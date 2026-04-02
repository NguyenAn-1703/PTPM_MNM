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
    chunking_strategy: str
    enable_multi_vector: bool
    enable_context_reorder: bool
    enable_context_compression: bool
    context_candidate_pool: int
    context_dedupe_jaccard_threshold: float
    context_compression_max_chars: int
    self_rag_confidence_threshold: float
    vector_backend: str
    enable_qdrant_dual_write: bool
    enable_qdrant_shadow_read: bool
    qdrant_url: str
    qdrant_api_key: str
    qdrant_collection: str
    persist_calibration_artifacts: bool
    enable_ragas_in_calibration: bool
    calibration_artifact_dir: Path


def _read_bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default

    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


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
    chunking_strategy = str(os.getenv("CHUNKING_STRATEGY", "recursive")).strip().lower()
    if chunking_strategy not in {"fixed", "recursive", "semantic"}:
        chunking_strategy = "recursive"

    enable_multi_vector = _read_bool_env("ENABLE_MULTI_VECTOR", True)
    enable_context_reorder = _read_bool_env("ENABLE_CONTEXT_REORDER", True)
    enable_context_compression = _read_bool_env("ENABLE_CONTEXT_COMPRESSION", True)

    context_candidate_pool = max(4, int(os.getenv("CONTEXT_CANDIDATE_POOL", "12")))
    context_dedupe_jaccard_threshold = float(os.getenv("CONTEXT_DEDUPE_JACCARD_THRESHOLD", "0.82"))
    context_dedupe_jaccard_threshold = min(0.99, max(0.2, context_dedupe_jaccard_threshold))

    context_compression_max_chars = max(180, int(os.getenv("CONTEXT_COMPRESSION_MAX_CHARS", "900")))
    self_rag_confidence_threshold = float(os.getenv("SELF_RAG_CONFIDENCE_THRESHOLD", "0.58"))
    self_rag_confidence_threshold = min(0.95, max(0.1, self_rag_confidence_threshold))

    vector_backend = str(os.getenv("VECTOR_BACKEND", "faiss")).strip().lower()
    if vector_backend not in {"faiss", "qdrant"}:
        vector_backend = "faiss"

    enable_qdrant_dual_write = _read_bool_env("ENABLE_QDRANT_DUAL_WRITE", False)
    enable_qdrant_shadow_read = _read_bool_env("ENABLE_QDRANT_SHADOW_READ", False)
    qdrant_url = str(os.getenv("QDRANT_URL", "http://localhost:6333")).strip().rstrip("/")
    qdrant_api_key = str(os.getenv("QDRANT_API_KEY", "")).strip()
    qdrant_collection = str(os.getenv("QDRANT_COLLECTION", "rag_chunks")).strip() or "rag_chunks"

    persist_calibration_artifacts = _read_bool_env("PERSIST_CALIBRATION_ARTIFACTS", True)
    enable_ragas_in_calibration = _read_bool_env("ENABLE_RAGAS_IN_CALIBRATION", False)
    calibration_artifact_dir = Path(
        os.getenv("CALIBRATION_ARTIFACT_DIR", str(BASE_DIR / "artifacts" / "self_rag"))
    )

    return RAGSettings(
        ollama_base_url=str(ollama_base_url).rstrip("/"),
        llm_model=llm_model,
        embedding_model=embedding_model,
        vector_db_dir=vector_db_dir,
        data_raw_dir=BASE_DIR / "data" / "raw",
        data_processed_dir=BASE_DIR / "data" / "processed",
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        chunking_strategy=chunking_strategy,
        enable_multi_vector=enable_multi_vector,
        enable_context_reorder=enable_context_reorder,
        enable_context_compression=enable_context_compression,
        context_candidate_pool=context_candidate_pool,
        context_dedupe_jaccard_threshold=context_dedupe_jaccard_threshold,
        context_compression_max_chars=context_compression_max_chars,
        self_rag_confidence_threshold=self_rag_confidence_threshold,
        vector_backend=vector_backend,
        enable_qdrant_dual_write=enable_qdrant_dual_write,
        enable_qdrant_shadow_read=enable_qdrant_shadow_read,
        qdrant_url=qdrant_url,
        qdrant_api_key=qdrant_api_key,
        qdrant_collection=qdrant_collection,
        persist_calibration_artifacts=persist_calibration_artifacts,
        enable_ragas_in_calibration=enable_ragas_in_calibration,
        calibration_artifact_dir=calibration_artifact_dir,
    )
