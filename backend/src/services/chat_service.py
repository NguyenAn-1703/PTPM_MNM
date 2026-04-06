"""Application service for chat-related orchestration over RAG runtime."""
from typing import Any, Dict, Iterable, List, Optional

from src.llm.runtime import get_rag_engine


def get_default_top_k() -> int:
    rag_engine = get_rag_engine()
    return int(getattr(rag_engine, "default_top_k", 5))


def run_chat(
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
    rag_engine = get_rag_engine()
    return rag_engine.chat(
        question=question,
        history=history or [],
        top_k=top_k,
        session_id=session_id,
        retrieval_mode=retrieval_mode,
        metadata_filters=metadata_filters,
        use_reranker=use_reranker,
        use_self_rag=use_self_rag,
        trace_id=trace_id,
    )


def run_chat_stream(
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
    rag_engine = get_rag_engine()
    return rag_engine.chat_stream(
        question=question,
        history=history or [],
        top_k=top_k,
        session_id=session_id,
        retrieval_mode=retrieval_mode,
        metadata_filters=metadata_filters,
        use_reranker=use_reranker,
        use_self_rag=use_self_rag,
        trace_id=trace_id,
    )


def clear_session_memory(session_id: str) -> bool:
    rag_engine = get_rag_engine()
    return rag_engine.clear_session_memory(session_id)
