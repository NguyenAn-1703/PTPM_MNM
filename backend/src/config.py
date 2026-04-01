"""Centralized runtime configuration for RAG backend."""
from dataclasses import dataclass
from pathlib import Path
import os


BASE_DIR = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class RAGSettings:
    ollama_base_url: str
    llm_model: str
    embedding_model: str
    vector_db_dir: Path
    data_raw_dir: Path
    data_processed_dir: Path
    chunk_size: int
    chunk_overlap: int


def _read_django_setting(name: str):
    try:
        from django.conf import settings

        if settings.configured:
            return getattr(settings, name, None)
    except Exception:
        return None
    return None


def get_rag_settings() -> RAGSettings:
    ollama_base_url = (
        os.getenv("OLLAMA_BASE_URL")
        or _read_django_setting("OLLAMA_BASE_URL")
        or "http://localhost:11434"
    )
    llm_model = os.getenv("OLLAMA_LLM") or _read_django_setting("OLLAMA_LLM") or "qwen2.5:7b"
    embedding_model = (
        os.getenv("EMBEDDING_MODEL")
        or _read_django_setting("EMBEDDING_MODEL")
        or "nomic-embed-text"
    )

    vector_db_setting = _read_django_setting("VECTOR_DB_PATH")
    vector_db_dir = Path(vector_db_setting) if vector_db_setting else BASE_DIR / "vector_db"

    chunk_size = int(os.getenv("CHUNK_SIZE", "1000"))
    chunk_overlap = int(os.getenv("CHUNK_OVERLAP", "150"))

    return RAGSettings(
        ollama_base_url=str(ollama_base_url).rstrip("/"),
        llm_model=llm_model,
        embedding_model=embedding_model,
        vector_db_dir=vector_db_dir,
        data_raw_dir=BASE_DIR / "data" / "raw",
        data_processed_dir=BASE_DIR / "data" / "processed",
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
