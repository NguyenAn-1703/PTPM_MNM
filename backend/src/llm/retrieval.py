"""Retrieval and reranking utilities for RAG engine."""
from datetime import datetime
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

    @staticmethod
    def _to_timestamp(value: Any) -> Optional[float]:
        if value in (None, ""):
            return None

        if isinstance(value, (int, float)):
            return float(value)

        text = str(value).strip()
        if not text:
            return None

        try:
            return float(text)
        except (TypeError, ValueError):
            pass

        try:
            if text.endswith("Z"):
                text = text[:-1] + "+00:00"
            return datetime.fromisoformat(text).timestamp()
        except (TypeError, ValueError):
            return None

    def _matches_metadata_filters(self, metadata: Dict[str, Any], filters: Optional[Dict[str, Any]]) -> bool:
        if not filters:
            return True

        metadata = metadata or {}
        filenames = set(filters.get("filenames") or [])
        file_types = set(filters.get("file_types") or [])
        vector_roles = set(filters.get("vector_roles") or [])
        tags = set(filters.get("tags") or [])
        page_from = filters.get("page_from")
        page_to = filters.get("page_to")

        if filenames and str(metadata.get("filename", "")) not in filenames:
            return False
        if file_types and str(metadata.get("file_type", "")) not in file_types:
            return False

        role = str(metadata.get("vector_role") or "content")
        if vector_roles and role not in vector_roles:
            return False

        if page_from is not None or page_to is not None:
            page_number_raw = metadata.get("page_number")
            if page_number_raw in (None, ""):
                return False
            try:
                page_number = int(page_number_raw)
            except (TypeError, ValueError):
                return False
            if page_from is not None and page_number < int(page_from):
                return False
            if page_to is not None and page_number > int(page_to):
                return False

        if tags:
            metadata_tags = metadata.get("tags") or []
            if isinstance(metadata_tags, str):
                metadata_tags = [item.strip() for item in metadata_tags.split(",") if item.strip()]
            metadata_tags_set = {str(item) for item in metadata_tags}
            if not tags.intersection(metadata_tags_set):
                return False

        uploaded_after = self._to_timestamp(filters.get("uploaded_after"))
        uploaded_before = self._to_timestamp(filters.get("uploaded_before"))
        if uploaded_after is not None or uploaded_before is not None:
            uploaded_at_ts = self._to_timestamp(metadata.get("uploaded_at_ts"))
            if uploaded_at_ts is None:
                uploaded_at_ts = self._to_timestamp(metadata.get("uploaded_at"))

            if uploaded_at_ts is None:
                return False
            if uploaded_after is not None and uploaded_at_ts < uploaded_after:
                return False
            if uploaded_before is not None and uploaded_at_ts > uploaded_before:
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

    def _resolve_parent_contexts(self, contexts: List[Dict[str, Any]], metadata_filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        if self.vector_store is None:
            return contexts

        try:
            docs = list(self.vector_store.docstore._dict.values())
        except Exception:
            return contexts

        parent_map: Dict[str, Dict[str, Any]] = {}
        for doc in docs:
            metadata = doc.metadata or {}
            if str(metadata.get("vector_role") or "content") != "content":
                continue
            if not self._matches_metadata_filters(metadata, metadata_filters):
                continue

            parent_id = str(metadata.get("parent_chunk_id") or "").strip()
            if not parent_id:
                continue
            parent_map[parent_id] = {"content": doc.page_content, "metadata": metadata}

        resolved: List[Dict[str, Any]] = []
        seen_parent_ids = set()

        for item in contexts:
            metadata = item.get("metadata", {}) or {}
            parent_id = str(metadata.get("parent_chunk_id") or "").strip()
            if parent_id:
                if parent_id in seen_parent_ids:
                    continue
                seen_parent_ids.add(parent_id)
                if str(metadata.get("vector_role") or "content") != "content" and parent_id in parent_map:
                    parent_item = parent_map[parent_id]
                    resolved.append(
                        {
                            **item,
                            "content": parent_item["content"],
                            "metadata": parent_item["metadata"],
                        }
                    )
                    continue

            resolved.append(item)

        return resolved

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

    def _compress_contexts(self, query: str, contexts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not contexts or not bool(getattr(self, "enable_context_compression", True)):
            return contexts

        max_chars = int(getattr(self, "context_compression_max_chars", 900))
        dedupe_threshold = float(getattr(self, "context_dedupe_jaccard_threshold", 0.82))
        query_terms = set(self._tokenize(query))

        def jaccard(tokens_a: set, tokens_b: set) -> float:
            if not tokens_a or not tokens_b:
                return 0.0
            return len(tokens_a.intersection(tokens_b)) / max(1, len(tokens_a.union(tokens_b)))

        compressed: List[Dict[str, Any]] = []
        seen_token_sets: List[set] = []

        for item in contexts:
            content = str(item.get("content", "")).strip()
            if not content:
                continue

            tokens = set(self._tokenize(content))
            if any(jaccard(tokens, prev_tokens) >= dedupe_threshold for prev_tokens in seen_token_sets):
                continue

            seen_token_sets.append(tokens)
            if len(content) <= max_chars:
                compressed_text = content
            else:
                sentences = [segment.strip() for segment in re.split(r"(?<=[\.\!\?])\s+|\n+", content) if segment.strip()]
                if not sentences:
                    compressed_text = content[:max_chars]
                else:
                    scored_sentences: List[Dict[str, Any]] = []
                    for idx, sentence in enumerate(sentences):
                        sent_tokens = set(self._tokenize(sentence))
                        overlap = len(query_terms.intersection(sent_tokens))
                        scored_sentences.append({"text": sentence, "score": overlap, "index": idx})

                    scored_sentences.sort(key=lambda row: (row["score"], -row["index"]), reverse=True)
                    selected: List[str] = []
                    current_len = 0
                    for row in scored_sentences:
                        sentence = row["text"]
                        additional = len(sentence) + (1 if selected else 0)
                        if current_len + additional > max_chars:
                            continue
                        selected.append(sentence)
                        current_len += additional
                        if current_len >= int(max_chars * 0.85):
                            break

                    if not selected:
                        compressed_text = content[:max_chars]
                    else:
                        compressed_text = " ".join(selected)

            compressed.append({**item, "compressed_content": compressed_text})

        return compressed

    def _reorder_contexts(self, contexts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not contexts or len(contexts) <= 2 or not bool(getattr(self, "enable_context_reorder", True)):
            return contexts

        front: List[Dict[str, Any]] = []
        back: List[Dict[str, Any]] = []
        for idx, item in enumerate(contexts):
            if idx % 2 == 0:
                front.append(item)
            else:
                back.insert(0, item)

        return front + back

    def _multi_vector_search(self, query: str, top_k: int = 3, metadata_filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        if not bool(getattr(self, "enable_multi_vector", False)):
            return self.search(query, top_k=top_k, metadata_filters=metadata_filters)

        candidate_pool = max(top_k * 3, int(getattr(self, "context_candidate_pool", 12)))
        role_weights = {
            "content": 1.0,
            "summary": 0.85,
            "hypo_question": 0.7,
        }
        fused: Dict[str, Dict[str, Any]] = {}
        rrf_k = 60

        for role, weight in role_weights.items():
            role_filters = {**(metadata_filters or {}), "vector_roles": [role]}
            role_candidates = self.search(query, top_k=candidate_pool, metadata_filters=role_filters)
            role_candidates = self._filter_relevant_contexts(role_candidates)

            for rank, item in enumerate(role_candidates, start=1):
                key = self._context_key(item)
                current = fused.get(key, {**item, "multi_vector_score": 0.0})
                current["multi_vector_score"] += weight * (1.0 / (rrf_k + rank))
                current[f"{role}_rank"] = rank
                fused[key] = current

        merged = list(fused.values())
        merged.sort(key=lambda item: item.get("multi_vector_score", 0.0), reverse=True)

        resolved = self._resolve_parent_contexts(merged, metadata_filters=metadata_filters)
        return resolved[:candidate_pool]

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
        vector_candidates = self._multi_vector_search(query, top_k=max(top_k * 3, 8), metadata_filters=metadata_filters)
        vector_candidates = self._filter_relevant_contexts(vector_candidates)
        keyword_filters = {**(metadata_filters or {})}
        keyword_filters.setdefault("vector_roles", ["content"])
        keyword_candidates = self._keyword_search(query, top_k=max(top_k * 3, 8), metadata_filters=keyword_filters)

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
        merged = self._resolve_parent_contexts(merged, metadata_filters=metadata_filters)
        return merged[:top_k]

    def search(self, query: str, top_k: int = 3, metadata_filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        adapter = getattr(self, "vector_adapter", None)
        if adapter is not None and adapter.should_use_as_primary():
            return adapter.search(query, top_k=max(1, top_k), metadata_filters=metadata_filters)

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

        if adapter is not None and adapter.should_shadow_read():
            shadow_results = adapter.search(query, top_k=max(1, top_k), metadata_filters=metadata_filters)
            logger.info(
                "Shadow-read compare primary=%s shadow=%s query=%s",
                len(search_results),
                len(shadow_results),
                query[:120],
            )

        return search_results
