"""Controller layer for chat and chat-stream orchestration."""
from typing import Any, Dict, Iterable, List, Optional

from src.services import chat_service


class ChatFlowController:
    """Coordinate chat execution between API adapters and chat service."""

    @staticmethod
    def parse_history(history_raw) -> List[Dict[str, str]]:
        if history_raw in (None, ""):
            return []

        if not isinstance(history_raw, list):
            raise ValueError("history phải là danh sách")

        parsed: List[Dict[str, str]] = []
        for idx, item in enumerate(history_raw):
            if not isinstance(item, dict):
                raise ValueError(f"history[{idx}] không hợp lệ")

            role = str(item.get("role", "")).strip().lower()
            content = str(item.get("content", "")).strip()

            if role not in {"user", "assistant"}:
                raise ValueError(f"history[{idx}].role phải là user hoặc assistant")
            if not content:
                raise ValueError(f"history[{idx}].content không được để trống")

            parsed.append({"role": role, "content": content})

        return parsed

    @staticmethod
    def default_top_k() -> int:
        return chat_service.get_default_top_k()

    @staticmethod
    def run_chat(
        *,
        question: str,
        history: Optional[List[Dict[str, str]]] = None,
        top_k: Optional[int] = None,
        session_id: Optional[str] = None,
        retrieval_mode: str = "hybrid",
        metadata_filters: Optional[Dict[str, Any]] = None,
        use_reranker: bool = True,
        use_self_rag: bool = True,
        trace_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        return chat_service.run_chat(
            question=question,
            history=history,
            top_k=top_k,
            session_id=session_id,
            retrieval_mode=retrieval_mode,
            metadata_filters=metadata_filters,
            use_reranker=use_reranker,
            use_self_rag=use_self_rag,
            trace_id=trace_id,
        )

    @staticmethod
    def run_chat_stream(
        *,
        question: str,
        history: Optional[List[Dict[str, str]]] = None,
        top_k: Optional[int] = None,
        session_id: Optional[str] = None,
        retrieval_mode: str = "hybrid",
        metadata_filters: Optional[Dict[str, Any]] = None,
        use_reranker: bool = True,
        use_self_rag: bool = True,
        trace_id: Optional[str] = None,
    ) -> Iterable[Dict[str, Any]]:
        return chat_service.run_chat_stream(
            question=question,
            history=history,
            top_k=top_k,
            session_id=session_id,
            retrieval_mode=retrieval_mode,
            metadata_filters=metadata_filters,
            use_reranker=use_reranker,
            use_self_rag=use_self_rag,
            trace_id=trace_id,
        )

    @staticmethod
    def clear_session_memory(session_id: str) -> bool:
        return chat_service.clear_session_memory(session_id)
