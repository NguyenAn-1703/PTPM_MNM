"""Retrieval and reranking utilities for RAG engine."""
import logging
import math
import re
from typing import Any, Dict, List, Optional

from django.conf import settings


logger = logging.getLogger(__name__)


class RAGRetrievalMixin:
    @staticmethod
    def _tokenize(text: str) -> List[str]:
        return [token for token in re.findall(r"[A-Za-z0-9À-ỹ]{2,}", (text or "").lower()) if token]

    @staticmethod
    def _context_key(ctx: Dict[str, Any]) -> str:
        metadata = ctx.get("metadata", {}) or {}
        return "::".join(
            [
                str(metadata.get("filename", "")),
                str(metadata.get("chunk_index", "")),
                str(metadata.get("char_start", "")),
                str(metadata.get("char_end", "")),
                str(ctx.get("content", ""))[:120],
            ]
        )

    def _matches_metadata_filters(self, metadata: Dict[str, Any], filters: Optional[Dict[str, Any]]) -> bool:
        if not filters:
            return True

        metadata = metadata or {}
        filenames = filters.get("filenames")
        file_types = filters.get("file_types")

        if filenames and metadata.get("filename") not in set(filenames):
            return False
        if file_types and metadata.get("file_type") not in set(file_types):
            return False

        return True

    def _get_reranker(self):
        if self._cross_encoder is not None:
            return self._cross_encoder

        cross_encoder_enabled = bool(getattr(settings, "ENABLE_CROSS_ENCODER", False))
        if not cross_encoder_enabled:
            self._cross_encoder = False
            return None

        try:
            from sentence_transformers import CrossEncoder

            self._cross_encoder = CrossEncoder(self.cross_encoder_model)
            return self._cross_encoder
        except Exception as exc:
            logger.warning("Cross-encoder unavailable: %s", exc)
            self._cross_encoder = False
            return None

    def _filter_relevant_contexts(self, contexts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        filtered = []
        for ctx in contexts:
            try:
                score = float(ctx.get("score", 0.0))
            except (TypeError, ValueError):
                continue

            if score <= self.max_retrieval_distance:
                filtered.append(ctx)

        return filtered

    def _collect_all_chunks(self, metadata_filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        if self.vector_store is None:
            return []

        try:
            docs = list(self.vector_store.docstore._dict.values())
        except Exception:
            return []

        chunks: List[Dict[str, Any]] = []
        for doc in docs:
            metadata = doc.metadata or {}
            if not self._matches_metadata_filters(metadata, metadata_filters):
                continue

            chunks.append(
                {
                    "content": doc.page_content,
                    "metadata": metadata,
                    "score": 0.0,
                }
            )

        return chunks

    def _keyword_search(self, query: str, top_k: int, metadata_filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        chunks = self._collect_all_chunks(metadata_filters)
        if not chunks:
            return []

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        chunk_tokens = [self._tokenize(item["content"]) for item in chunks]
        total_docs = len(chunk_tokens)
        df: Dict[str, int] = {}
        for tokens in chunk_tokens:
            for token in set(tokens):
                df[token] = df.get(token, 0) + 1

        scored: List[Dict[str, Any]] = []
        for idx, tokens in enumerate(chunk_tokens):
            if not tokens:
                continue

            tf: Dict[str, int] = {}
            for token in tokens:
                tf[token] = tf.get(token, 0) + 1

            score = 0.0
            for token in query_tokens:
                freq = tf.get(token, 0)
                if freq == 0:
                    continue
                idf = math.log((1 + total_docs) / (1 + df.get(token, 0))) + 1.0
                score += freq * idf

            if score <= 0:
                continue

            scored.append(
                {
                    **chunks[idx],
                    "score": float(1.0 / (1.0 + score)),
                    "keyword_score": float(score),
                }
            )

        scored.sort(key=lambda item: item.get("keyword_score", 0.0), reverse=True)
        return scored[:top_k]

    def _rerank_contexts(self, query: str, contexts: List[Dict[str, Any]], top_k: int) -> Dict[str, Any]:
        if not contexts:
            return {"contexts": [], "used": False, "model": None}

        reranker = self._get_reranker()
        if reranker:
            try:
                pairs = [[query, item["content"]] for item in contexts]
                scores = reranker.predict(pairs)
                enriched = []
                for idx, item in enumerate(contexts):
                    enriched.append({**item, "rerank_score": float(scores[idx])})
                enriched.sort(key=lambda item: item.get("rerank_score", -1.0), reverse=True)
                return {"contexts": enriched[:top_k], "used": True, "model": self.cross_encoder_model}
            except Exception as exc:
                logger.warning("Cross-encoder rerank failed, fallback lexical rerank: %s", exc)

        query_terms = set(self._tokenize(query))
        fallback = []
        for item in contexts:
            terms = set(self._tokenize(item["content"]))
            overlap = len(query_terms.intersection(terms))
            fallback.append({**item, "rerank_score": float(overlap)})

        fallback.sort(key=lambda item: item.get("rerank_score", 0.0), reverse=True)
        return {"contexts": fallback[:top_k], "used": False, "model": "lexical-overlap"}

    def _hybrid_search(self, query: str, top_k: int = 3, metadata_filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        vector_candidates = self.search(query, top_k=max(top_k * 3, 8), metadata_filters=metadata_filters)
        vector_candidates = self._filter_relevant_contexts(vector_candidates)
        keyword_candidates = self._keyword_search(query, top_k=max(top_k * 3, 8), metadata_filters=metadata_filters)

        fused: Dict[str, Dict[str, Any]] = {}
        rrf_k = 60

        for rank, item in enumerate(vector_candidates, start=1):
            key = self._context_key(item)
            current = fused.get(key, {**item, "hybrid_score": 0.0})
            current["hybrid_score"] += 1.0 / (rrf_k + rank)
            current["vector_rank"] = rank
            fused[key] = current

        for rank, item in enumerate(keyword_candidates, start=1):
            key = self._context_key(item)
            current = fused.get(key, {**item, "hybrid_score": 0.0})
            current["hybrid_score"] += 1.0 / (rrf_k + rank)
            current["keyword_rank"] = rank
            fused[key] = current

        merged = list(fused.values())
        merged.sort(key=lambda item: item.get("hybrid_score", 0.0), reverse=True)
        return merged[:top_k]

    def search(self, query: str, top_k: int = 3, metadata_filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        if self.vector_store is None:
            return []

        results = self.vector_store.similarity_search_with_score(query, k=top_k)

        search_results = []
        for doc, score in results:
            metadata = doc.metadata or {}
            if not self._matches_metadata_filters(metadata, metadata_filters):
                continue

            search_results.append(
                {
                    "content": doc.page_content,
                    "metadata": metadata,
                    "score": float(score),
                }
            )

        return search_results
