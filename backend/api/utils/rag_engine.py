"""Compatibility layer for the refactored RAG package."""
from typing import Optional

from .rag import RAGEngine


# Singleton instance
_rag_engine: Optional[RAGEngine] = None


def get_rag_engine() -> RAGEngine:
    global _rag_engine
    if _rag_engine is None:
        _rag_engine = RAGEngine()
    return _rag_engine
