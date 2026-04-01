"""Evaluation and benchmark helpers for chunking and retrieval modes."""
import time
from typing import Any, Dict, List, Optional

from .text import normalize_chunk_params, split_text


class RAGEvaluationMixin:
    def _build_temp_vector_store(self, source_docs: List[Dict[str, Any]], chunk_size: int, chunk_overlap: int):
        from langchain_community.vectorstores import FAISS

        texts: List[str] = []
        metadatas: List[Dict[str, Any]] = []

        for doc_idx, doc in enumerate(source_docs):
            source_text = str(doc.get("text", "")).strip()
            if not source_text:
                continue

            base_metadata = doc.get("metadata", {}) or {}
            chunks = split_text(source_text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
            for chunk_idx, chunk in enumerate(chunks):
                texts.append(chunk)
                metadatas.append(
                    {
                        "source_doc_index": doc_idx,
                        "chunk_index": chunk_idx,
                        "total_chunks": len(chunks),
                        "chunk_size": chunk_size,
                        "chunk_overlap": chunk_overlap,
                        **base_metadata,
                    }
                )

        if not texts:
            return None, 0

        temp_store = FAISS.from_texts(
            texts=texts,
            embedding=self.embeddings,
            metadatas=metadatas,
        )
        return temp_store, len(texts)

    def evaluate_chunk_strategy(
        self,
        evaluation_set: List[Dict[str, Any]],
        chunk_sizes: List[int],
        chunk_overlaps: List[int],
        top_k: int = 3,
    ) -> Dict[str, Any]:
        if not evaluation_set:
            raise ValueError("evaluation_set không được rỗng")

        source_docs = self.storage.load_source_documents()
        if not source_docs:
            raise ValueError("Không có source documents để đánh giá. Hãy upload tài liệu trước.")

        valid_cases: List[Dict[str, Any]] = []
        for idx, case in enumerate(evaluation_set):
            question = str(case.get("question", "")).strip()
            if not question:
                raise ValueError(f"evaluation_set[{idx}].question không hợp lệ")

            expected_keywords = case.get("expected_keywords") or []
            if not isinstance(expected_keywords, list):
                raise ValueError(f"evaluation_set[{idx}].expected_keywords phải là list")

            cleaned_keywords = [str(item).strip().lower() for item in expected_keywords if str(item).strip()]
            valid_cases.append(
                {
                    "question": question,
                    "expected_keywords": cleaned_keywords,
                }
            )

        reports: List[Dict[str, Any]] = []
        for size in chunk_sizes:
            for overlap in chunk_overlaps:
                normalized_size, normalized_overlap = normalize_chunk_params(
                    default_size=self.chunk_size,
                    default_overlap=self.chunk_overlap,
                    chunk_size=size,
                    chunk_overlap=overlap,
                )
                temp_store, generated_chunks = self._build_temp_vector_store(
                    source_docs=source_docs,
                    chunk_size=normalized_size,
                    chunk_overlap=normalized_overlap,
                )

                if temp_store is None:
                    continue

                hit_count = 0
                per_question: List[Dict[str, Any]] = []

                for case in valid_cases:
                    results = temp_store.similarity_search_with_score(case["question"], k=top_k)
                    contexts: List[Dict[str, Any]] = []
                    for doc, score in results:
                        contexts.append(
                            {
                                "content": doc.page_content,
                                "metadata": doc.metadata,
                                "score": float(score),
                            }
                        )

                    contexts = self._filter_relevant_contexts(contexts)
                    joined_context = "\\n".join([item["content"] for item in contexts]).lower()
                    expected_keywords = case["expected_keywords"]

                    if expected_keywords:
                        is_hit = all(keyword in joined_context for keyword in expected_keywords)
                    else:
                        is_hit = len(contexts) > 0

                    if is_hit:
                        hit_count += 1

                    per_question.append(
                        {
                            "question": case["question"],
                            "expected_keywords": expected_keywords,
                            "retrieved_contexts": len(contexts),
                            "hit": is_hit,
                        }
                    )

                total = len(valid_cases)
                accuracy = round(hit_count / total, 4) if total else 0.0

                reports.append(
                    {
                        "chunk_size": normalized_size,
                        "chunk_overlap": normalized_overlap,
                        "retrieval_accuracy": accuracy,
                        "hits": hit_count,
                        "total_questions": total,
                        "generated_chunks": generated_chunks,
                        "details": per_question,
                    }
                )

        sorted_reports = sorted(
            reports,
            key=lambda item: (item["retrieval_accuracy"], -item["generated_chunks"]),
            reverse=True,
        )

        return {
            "summary": {
                "source_documents": len(source_docs),
                "evaluated_configs": len(sorted_reports),
                "metric": "retrieval_accuracy",
            },
            "best_config": sorted_reports[0] if sorted_reports else None,
            "reports": sorted_reports,
        }

    def benchmark_retrieval_modes(
        self,
        evaluation_set: List[Dict[str, Any]],
        top_k: int = 3,
        retrieval_modes: Optional[List[str]] = None,
        metadata_filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if not evaluation_set:
            raise ValueError("evaluation_set không được rỗng")

        if self.vector_store is None:
            raise ValueError("Chưa có dữ liệu vector store để benchmark. Hãy upload tài liệu trước.")

        modes = retrieval_modes or ["vector", "hybrid", "hybrid_rerank"]
        valid_modes = {"vector", "hybrid", "hybrid_rerank"}

        sanitized_modes = []
        for mode in modes:
            normalized = str(mode or "").strip().lower()
            if normalized not in valid_modes:
                raise ValueError(f"retrieval_mode không hợp lệ: {mode}")
            if normalized not in sanitized_modes:
                sanitized_modes.append(normalized)

        cases: List[Dict[str, Any]] = []
        for idx, item in enumerate(evaluation_set):
            question = str(item.get("question", "")).strip()
            if not question:
                raise ValueError(f"evaluation_set[{idx}].question không hợp lệ")

            expected_keywords = item.get("expected_keywords") or []
            if not isinstance(expected_keywords, list):
                raise ValueError(f"evaluation_set[{idx}].expected_keywords phải là list")

            cleaned_keywords = [str(token).strip().lower() for token in expected_keywords if str(token).strip()]
            cases.append({"question": question, "expected_keywords": cleaned_keywords})

        reports: List[Dict[str, Any]] = []
        for mode in sanitized_modes:
            total_latency = 0.0
            hits = 0
            details: List[Dict[str, Any]] = []

            for case in cases:
                question = case["question"]
                expected = case["expected_keywords"]

                started = time.perf_counter()
                if mode == "vector":
                    contexts = self.search(question, top_k=max(top_k * 2, 6), metadata_filters=metadata_filters)
                    contexts = self._filter_relevant_contexts(contexts)
                    contexts = contexts[:top_k]
                    reranker_used = False
                elif mode == "hybrid":
                    contexts = self._hybrid_search(question, top_k=max(top_k * 2, 6), metadata_filters=metadata_filters)
                    contexts = contexts[:top_k]
                    reranker_used = False
                else:
                    candidates = self._hybrid_search(question, top_k=max(top_k * 2, 6), metadata_filters=metadata_filters)
                    rerank_info = self._rerank_contexts(question, candidates, top_k=top_k)
                    contexts = rerank_info["contexts"]
                    reranker_used = bool(rerank_info.get("used", False))

                latency_ms = (time.perf_counter() - started) * 1000
                total_latency += latency_ms

                joined = "\\n".join([item.get("content", "") for item in contexts]).lower()
                if expected:
                    is_hit = all(token in joined for token in expected)
                else:
                    is_hit = len(contexts) > 0
                if is_hit:
                    hits += 1

                details.append(
                    {
                        "question": question,
                        "expected_keywords": expected,
                        "hit": is_hit,
                        "latency_ms": round(latency_ms, 3),
                        "retrieved_contexts": len(contexts),
                        "reranker_used": reranker_used,
                    }
                )

            total = len(cases)
            reports.append(
                {
                    "mode": mode,
                    "retrieval_accuracy": round(hits / total, 4) if total else 0.0,
                    "hits": hits,
                    "total_questions": total,
                    "avg_latency_ms": round(total_latency / total, 3) if total else 0.0,
                    "details": details,
                }
            )

        reports.sort(key=lambda item: (item["retrieval_accuracy"], -item["avg_latency_ms"]), reverse=True)
        return {
            "summary": {
                "metric": "retrieval_accuracy",
                "question_count": len(cases),
                "evaluated_modes": len(reports),
                "top_k": top_k,
            },
            "best_mode": reports[0] if reports else None,
            "reports": reports,
        }
