"""Chat orchestration pipeline for conversational RAG."""
import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from .prompts import build_chat_answer_prompt
from .text import build_citations, format_history


logger = logging.getLogger(__name__)


class RAGChatPipelineMixin:
    @staticmethod
    def _normalize_retrieval_mode(retrieval_mode: str) -> str:
        normalized = (retrieval_mode or "hybrid").strip().lower()
        if normalized not in {"vector", "hybrid", "hybrid_multivector"}:
            return "hybrid"
        if normalized == "hybrid_multivector":
            return "hybrid"
        return normalized

    def _retrieve_contexts(
        self,
        query: str,
        top_k: int,
        retrieval_mode: str,
        metadata_filters: Optional[Dict[str, Any]],
        use_reranker: bool,
    ) -> Dict[str, Any]:
        candidate_top_k = max(top_k * 2, int(getattr(self, "context_candidate_pool", 12)))

        retrieve_started = time.perf_counter()
        if retrieval_mode == "vector":
            contexts = self._multi_vector_search(query, top_k=candidate_top_k, metadata_filters=metadata_filters)
            contexts = self._filter_relevant_contexts(contexts)
        else:
            contexts = self._hybrid_search(query, top_k=candidate_top_k, metadata_filters=metadata_filters)
        retrieve_ms = (time.perf_counter() - retrieve_started) * 1000

        rerank_info = {"contexts": contexts[:top_k], "used": False, "model": None}
        rerank_started = time.perf_counter()
        if use_reranker:
            rerank_info = self._rerank_contexts(query, contexts, top_k=top_k)
            contexts = rerank_info["contexts"]
        else:
            contexts = contexts[:top_k]
        rerank_ms = (time.perf_counter() - rerank_started) * 1000

        contexts = self._compress_contexts(query, contexts)
        contexts = self._reorder_contexts(contexts)

        return {
            "contexts": contexts,
            "rerank_info": rerank_info,
            "retrieve_ms": round(retrieve_ms, 3),
            "rerank_ms": round(rerank_ms, 3),
        }

    def _assess_answer(self, question: str, answer: str, contexts: List[Dict[str, Any]], use_self_rag: bool) -> Dict[str, Any]:
        self_eval = self._self_evaluate_answer(question=question, answer=answer, contexts=contexts)
        threshold = float(getattr(self, "self_rag_confidence_threshold", 0.58))
        self_rag_applied = bool(
            use_self_rag and (not self_eval.get("supported") or float(self_eval.get("confidence", 0.0)) < threshold)
        )
        confidence_score = min(
            1.0,
            max(
                0.0,
                0.6 * float(self_eval.get("confidence", 0.0))
                + (0.4 if contexts else 0.0)
                - (0.15 if not contexts else 0.0),
            ),
        )

        return {
            "self_check": self_eval,
            "self_rag_applied": self_rag_applied,
            "confidence_score": confidence_score,
            "confidence_label": self._confidence_label(confidence_score),
        }

    def chat(
        self,
        question: str,
        history: Optional[List[Dict[str, str]]] = None,
        top_k: int = 3,
        session_id: Optional[str] = None,
        retrieval_mode: str = "hybrid",
        metadata_filters: Optional[Dict[str, Any]] = None,
        use_reranker: bool = True,
        use_self_rag: bool = True,
        trace_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        request_trace_id = str(trace_id or uuid.uuid4().hex)
        total_started = time.perf_counter()

        if self.vector_store is None:
            return {
                "answer": "Chưa có tài liệu nào được upload. Vui lòng upload tài liệu trước khi đặt câu hỏi.",
                "contexts": [],
                "has_context": False,
                "confidence_score": 0.0,
                "confidence_label": "low",
                "trace_id": request_trace_id,
            }

        resolved_session_id = self.memory.normalize_session_id(session_id)
        client_history = self.memory.sanitize_history(history or [])
        memory_history = self.memory.get_session_history(resolved_session_id)
        effective_history = client_history if client_history else memory_history

        if client_history:
            self.memory.set_session_history(resolved_session_id, client_history)

        standalone_question = self._condense_question(effective_history, question)
        rewritten = standalone_question.strip().lower() != question.strip().lower()
        retrieval_mode = self._normalize_retrieval_mode(retrieval_mode)

        logger.info("trace=%s query=%s mode=%s", request_trace_id, question, retrieval_mode)

        retrieval_result = self._retrieve_contexts(
            query=standalone_question,
            top_k=top_k,
            retrieval_mode=retrieval_mode,
            metadata_filters=metadata_filters,
            use_reranker=use_reranker,
        )
        contexts = retrieval_result["contexts"]
        rerank_info = retrieval_result["rerank_info"]

        if not contexts:
            self.memory.append_session_messages(
                resolved_session_id,
                [
                    {"role": "user", "content": question},
                    {"role": "assistant", "content": "Không tìm thấy thông tin liên quan trong tài liệu đã upload."},
                ],
            )
            return {
                "answer": "Không tìm thấy thông tin liên quan trong tài liệu đã upload.",
                "contexts": [],
                "has_context": False,
                "session_id": resolved_session_id,
                "standalone_question": standalone_question,
                "rewritten": rewritten,
                "retrieval_mode": retrieval_mode,
                "applied_filters": metadata_filters or {},
                "reranker": {"used": False, "model": rerank_info.get("model")},
                "self_rag_applied": False,
                "confidence_score": 0.0,
                "confidence_label": "low",
                "trace_id": request_trace_id,
                "timings_ms": {
                    "retrieve": retrieval_result["retrieve_ms"],
                    "rerank": retrieval_result["rerank_ms"],
                    "total": round((time.perf_counter() - total_started) * 1000, 3),
                },
            }

        context_text = "\n\n---\n\n".join([ctx.get("compressed_content") or ctx["content"] for ctx in contexts])
        history_text = format_history(
            effective_history,
            history_max_messages=self.history_max_messages,
            history_max_chars=self.history_max_chars,
        )
        prompt = build_chat_answer_prompt(self.system_prompt, history_text, context_text, question)

        generation_started = time.perf_counter()
        try:
            answer = self._invoke_llm(prompt)
        except Exception as exc:
            answer = f"Lỗi khi gọi LLM: {str(exc)}"
        generation_ms = (time.perf_counter() - generation_started) * 1000

        eval_started = time.perf_counter()
        assessment = self._assess_answer(
            question=question,
            answer=answer,
            contexts=contexts,
            use_self_rag=use_self_rag,
        )
        eval_ms = (time.perf_counter() - eval_started) * 1000

        self.memory.append_session_messages(
            resolved_session_id,
            [
                {"role": "user", "content": question},
                {"role": "assistant", "content": answer},
            ],
        )

        total_ms = (time.perf_counter() - total_started) * 1000
        result = {
            "answer": answer,
            "contexts": build_citations(contexts, answer),
            "has_context": True,
            "session_id": resolved_session_id,
            "standalone_question": standalone_question,
            "rewritten": rewritten,
            "retrieval_mode": retrieval_mode,
            "applied_filters": metadata_filters or {},
            "reranker": {"used": bool(rerank_info.get("used", False)), "model": rerank_info.get("model")},
            "self_rag_applied": bool(assessment["self_rag_applied"]),
            "confidence_score": round(float(assessment["confidence_score"]), 4),
            "confidence_label": assessment["confidence_label"],
            "self_check": assessment["self_check"],
            "trace_id": request_trace_id,
            "timings_ms": {
                "retrieve": retrieval_result["retrieve_ms"],
                "rerank": retrieval_result["rerank_ms"],
                "generation": round(generation_ms, 3),
                "evaluation": round(eval_ms, 3),
                "total": round(total_ms, 3),
            },
        }
        logger.info(
            "trace=%s done total_ms=%.2f retrieve_ms=%.2f rerank_ms=%.2f gen_ms=%.2f eval_ms=%.2f contexts=%s",
            request_trace_id,
            total_ms,
            retrieval_result["retrieve_ms"],
            retrieval_result["rerank_ms"],
            generation_ms,
            eval_ms,
            len(contexts),
        )
        return result

    def chat_stream(
        self,
        question: str,
        history: Optional[List[Dict[str, str]]] = None,
        top_k: int = 3,
        session_id: Optional[str] = None,
        retrieval_mode: str = "hybrid",
        metadata_filters: Optional[Dict[str, Any]] = None,
        use_reranker: bool = True,
        use_self_rag: bool = True,
        trace_id: Optional[str] = None,
    ):
        request_trace_id = str(trace_id or uuid.uuid4().hex)

        if self.vector_store is None:
            yield {
                "event": "error",
                "data": {
                    "error": "Chưa có tài liệu nào được upload. Vui lòng upload tài liệu trước khi đặt câu hỏi.",
                    "trace_id": request_trace_id,
                },
            }
            return

        resolved_session_id = self.memory.normalize_session_id(session_id)
        client_history = self.memory.sanitize_history(history or [])
        memory_history = self.memory.get_session_history(resolved_session_id)
        effective_history = client_history if client_history else memory_history

        if client_history:
            self.memory.set_session_history(resolved_session_id, client_history)

        standalone_question = self._condense_question(effective_history, question)
        rewritten = standalone_question.strip().lower() != question.strip().lower()
        retrieval_mode = self._normalize_retrieval_mode(retrieval_mode)

        retrieval_result = self._retrieve_contexts(
            query=standalone_question,
            top_k=top_k,
            retrieval_mode=retrieval_mode,
            metadata_filters=metadata_filters,
            use_reranker=use_reranker,
        )
        contexts = retrieval_result["contexts"]

        yield {
            "event": "meta",
            "data": {
                "trace_id": request_trace_id,
                "session_id": resolved_session_id,
                "standalone_question": standalone_question,
                "rewritten": rewritten,
                "retrieval_mode": retrieval_mode,
                "reranker": {
                    "used": bool(retrieval_result["rerank_info"].get("used", False)),
                    "model": retrieval_result["rerank_info"].get("model"),
                },
                "timings_ms": {
                    "retrieve": retrieval_result["retrieve_ms"],
                    "rerank": retrieval_result["rerank_ms"],
                },
            },
        }

        if not contexts:
            answer = "Không tìm thấy thông tin liên quan trong tài liệu đã upload."
            self.memory.append_session_messages(
                resolved_session_id,
                [
                    {"role": "user", "content": question},
                    {"role": "assistant", "content": answer},
                ],
            )
            yield {
                "event": "done",
                "data": {
                    "answer": answer,
                    "contexts": [],
                    "has_context": False,
                    "trace_id": request_trace_id,
                },
            }
            return

        history_text = format_history(
            effective_history,
            history_max_messages=self.history_max_messages,
            history_max_chars=self.history_max_chars,
        )
        context_text = "\n\n---\n\n".join([ctx.get("compressed_content") or ctx["content"] for ctx in contexts])
        prompt = build_chat_answer_prompt(self.system_prompt, history_text, context_text, question)

        answer_parts: List[str] = []
        try:
            for token in self._stream_llm(prompt):
                answer_parts.append(token)
                yield {"event": "token", "data": {"token": token}}
        except Exception as exc:
            yield {
                "event": "error",
                "data": {"error": f"Lỗi khi stream LLM: {str(exc)}", "trace_id": request_trace_id},
            }
            return

        answer = "".join(answer_parts).strip()
        assessment = self._assess_answer(
            question=question,
            answer=answer,
            contexts=contexts,
            use_self_rag=use_self_rag,
        )

        self.memory.append_session_messages(
            resolved_session_id,
            [
                {"role": "user", "content": question},
                {"role": "assistant", "content": answer},
            ],
        )

        yield {
            "event": "done",
            "data": {
                "answer": answer,
                "contexts": build_citations(contexts, answer),
                "has_context": True,
                "session_id": resolved_session_id,
                "standalone_question": standalone_question,
                "rewritten": rewritten,
                "retrieval_mode": retrieval_mode,
                "applied_filters": metadata_filters or {},
                "self_rag_applied": bool(assessment["self_rag_applied"]),
                "confidence_score": round(float(assessment["confidence_score"]), 4),
                "confidence_label": assessment["confidence_label"],
                "self_check": assessment["self_check"],
                "trace_id": request_trace_id,
            },
        }
