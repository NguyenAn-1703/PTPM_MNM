"""Vector database helpers for loading and persisting FAISS artifacts."""
from pathlib import Path
from typing import Any, Optional

from src.rag.storage import RagStorage

from .config import get_rag_settings


def get_storage(path: Optional[Path] = None) -> RagStorage:
    cfg = get_rag_settings()
    return RagStorage(path or cfg.vector_db_dir)


def load_vector_db(embeddings: Any, path: Optional[Path] = None):
    return get_storage(path).load_vector_store(embeddings)


def save_vector_db(vector_store: Any, path: Optional[Path] = None) -> None:
    get_storage(path).save_vector_store(vector_store)
