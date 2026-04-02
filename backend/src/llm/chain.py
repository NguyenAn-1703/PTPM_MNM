"""High-level RAG chain helper built on current engine implementation."""
from typing import Any, Dict, List, Optional


def create_rag_chain(engine: Any):
    def run(
        question: str,
        *,
        session_id: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None,
        retrieval_mode: str = "hybrid",
        metadata_filters: Optional[Dict[str, Any]] = None,
        use_reranker: bool = True,
        use_self_rag: bool = True,
    ) -> Dict[str, Any]:
        return engine.chat(
            question=question,
            session_id=session_id,
            history=history,
            retrieval_mode=retrieval_mode,
            metadata_filters=metadata_filters,
            use_reranker=use_reranker,
            use_self_rag=use_self_rag,
        )

    return run
