"""Vector database helpers for loading and persisting FAISS artifacts."""
from pathlib import Path
from typing import Optional

from src.llm.storage import RagStorage

from .config import get_rag_settings


def get_storage(path: Optional[Path] = None) -> RagStorage:
    cfg = get_rag_settings()
    return RagStorage(path or cfg.vector_db_dir)
