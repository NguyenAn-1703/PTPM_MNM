"""RAG package exports.

This module intentionally avoids eager imports to prevent circular import chains
between src.database <-> src.rag.* during Django startup.
"""

__all__ = ["RAGEngine", "get_rag_engine"]


def __getattr__(name: str):
	if name == "RAGEngine":
		from .engine import RAGEngine

		return RAGEngine
	if name == "get_rag_engine":
		from .runtime import get_rag_engine

		return get_rag_engine
	raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
