"""Runtime singleton for RAG engine."""
import threading
from typing import Optional

from .engine import RAGEngine


_rag_engine: Optional[RAGEngine] = None
_engine_lock = threading.Lock()


def get_rag_engine(reset: bool = False) -> RAGEngine:
    global _rag_engine
    with _engine_lock:
        if reset:
            _rag_engine = None
        if _rag_engine is None:
            _rag_engine = RAGEngine()
    return _rag_engine
