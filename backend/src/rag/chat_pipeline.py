"""Chat orchestration pipeline for conversational RAG."""
import logging
from typing import Any, Dict, List, Optional

from .prompts import build_chat_answer_prompt, build_chat_retry_prompt
from .text import build_citations, format_history


logger = logging.getLogger(__name__)


class RAGChatPipelineMixin:
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
    ) -> Dict[str, Any]:
        if self.vector_store is None:
            return {
                "answer": "Chưa có tài liệu nào được upload. Vui lòng upload tài liệu trước khi đặt câu hỏi.",
                "contexts": [],
                "has_context": False,
                "confidence_score": 0.0,
                "confidence_label": "low",
            }

        resolved_session_id = self.memory.normalize_session_id(session_id)
        client_history = self.memory.sanitize_history(history or [])
        memory_history = self.memory.get_session_history(resolved_session_id)
        effective_history = client_history if client_history else memory_history

        if client_history:
            self.memory.set_session_history(resolved_session_id, client_history)

        standalone_question = self._condense_question(effective_history, question)
        rewritten = standalone_question.strip().lower() != question.strip().lower()
        retrieval_mode = (retrieval_mode or "hybrid").strip().lower()
        if retrieval_mode not in {"vector", "hybrid"}:
            retrieval_mode = "hybrid"

        logger.info("Query: %s", question)

        if retrieval_mode == "vector":
            contexts = self.search(standalone_question, top_k=max(top_k * 2, 6), metadata_filters=metadata_filters)
            contexts = self._filter_relevant_contexts(contexts)
        else:
            contexts = self._hybrid_search(standalone_question, top_k=max(top_k * 2, 6), metadata_filters=metadata_filters)

        rerank_info = {"contexts": contexts[:top_k], "used": False, "model": None}
        if use_reranker:
            rerank_info = self._rerank_contexts(standalone_question, contexts, top_k=top_k)
            contexts = rerank_info["contexts"]
        else:
            contexts = contexts[:top_k]

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
            }

        context_text = "\n\n---\n\n".join([ctx["content"] for ctx in contexts])
        history_text = format_history(
            effective_history,
            history_max_messages=self.history_max_messages,
            history_max_chars=self.history_max_chars,
        )
        prompt = build_chat_answer_prompt(self.system_prompt, history_text, context_text, question)

        try:
            answer = self._invoke_llm(prompt)
        except Exception as exc:
            answer = f"Lỗi khi gọi LLM: {str(exc)}"

        self_eval = self._self_evaluate_answer(question=question, answer=answer, contexts=contexts)
        self_rag_applied = False

        if use_self_rag and (not self_eval.get("supported") or float(self_eval.get("confidence", 0.0)) < 0.45):
            self_rag_applied = True
            rewritten_query = self._rewrite_query_for_retrieval(question, effective_history)
            if retrieval_mode == "vector":
                second_contexts = self.search(rewritten_query, top_k=max(top_k * 2, 6), metadata_filters=metadata_filters)
                second_contexts = self._filter_relevant_contexts(second_contexts)
            else:
                second_contexts = self._hybrid_search(rewritten_query, top_k=max(top_k * 2, 6), metadata_filters=metadata_filters)

            if use_reranker:
                second_rerank = self._rerank_contexts(rewritten_query, second_contexts, top_k=top_k)
                second_contexts = second_rerank["contexts"]

            if second_contexts:
                second_context_text = "\n\n---\n\n".join([ctx["content"] for ctx in second_contexts])
                second_prompt = build_chat_retry_prompt(self.system_prompt, history_text, second_context_text, question)
                try:
                    second_answer = self._invoke_llm(second_prompt)
                    second_eval = self._self_evaluate_answer(question=question, answer=second_answer, contexts=second_contexts)
                    if float(second_eval.get("confidence", 0.0)) >= float(self_eval.get("confidence", 0.0)):
                        answer = second_answer
                        contexts = second_contexts
                        self_eval = second_eval
                except Exception:
                    pass

        confidence_score = min(
            1.0,
            max(
                0.0,
                0.6 * float(self_eval.get("confidence", 0.0))
                + (0.4 if contexts else 0.0)
                - (0.15 if not contexts else 0.0),
            ),
        )
        confidence_label = self._confidence_label(confidence_score)

        self.memory.append_session_messages(
            resolved_session_id,
            [
                {"role": "user", "content": question},
                {"role": "assistant", "content": answer},
            ],
        )

        return {
            "answer": answer,
            "contexts": build_citations(contexts, answer),
            "has_context": True,
            "session_id": resolved_session_id,
            "standalone_question": standalone_question,
            "rewritten": rewritten,
            "retrieval_mode": retrieval_mode,
            "applied_filters": metadata_filters or {},
            "reranker": {"used": bool(rerank_info.get("used", False)), "model": rerank_info.get("model")},
            "self_rag_applied": self_rag_applied,
            "confidence_score": round(confidence_score, 4),
            "confidence_label": confidence_label,
            "self_check": self_eval,
        }
