"""RAG engine orchestration layer."""
import logging
from typing import Any, Dict, List, Optional

from src.config import get_rag_settings
from src.database import get_storage
from src.model_factory import get_embeddings, get_llm_client
from .chat_pipeline import RAGChatPipelineMixin
from .evaluation import RAGEvaluationMixin
from .indexing import RAGIndexingMixin
from .memory import SessionMemoryStore
from .retrieval import RAGRetrievalMixin
from .self_rag import RAGSelfRAGMixin
from .vector_adapter import QdrantVectorAdapter


logger = logging.getLogger(__name__)


class RAGEngine(RAGChatPipelineMixin, RAGRetrievalMixin, RAGSelfRAGMixin, RAGIndexingMixin, RAGEvaluationMixin):
    """Core RAG orchestration: indexing, retrieval, and answer generation."""

    def __init__(self):
        cfg = get_rag_settings()
        self.vector_store_path = cfg.vector_db_dir
        self.ollama_base_url = cfg.ollama_base_url
        self.llm_model = cfg.llm_model
        self.embedding_model = cfg.embedding_model
        self.request_timeout = 120
        self.max_retrieval_distance = 1.2
        try:
            from django.conf import settings

            self.cross_encoder_model = getattr(settings, "CROSS_ENCODER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
        except Exception:
            self.cross_encoder_model = "cross-encoder/ms-marco-MiniLM-L-6-v2"
        self._cross_encoder = None

        self.embeddings = get_embeddings()
        self._llm_client = get_llm_client()

        self.chunk_size = cfg.chunk_size
        self.chunk_overlap = cfg.chunk_overlap
        self.chunking_strategy = cfg.chunking_strategy
        self.enable_multi_vector = cfg.enable_multi_vector
        self.enable_context_reorder = cfg.enable_context_reorder
        self.enable_context_compression = cfg.enable_context_compression
        self.context_candidate_pool = cfg.context_candidate_pool
        self.context_dedupe_jaccard_threshold = cfg.context_dedupe_jaccard_threshold
        self.context_compression_max_chars = cfg.context_compression_max_chars
        self.self_rag_confidence_threshold = cfg.self_rag_confidence_threshold
        self.vector_backend = cfg.vector_backend
        self.enable_qdrant_dual_write = cfg.enable_qdrant_dual_write
        self.enable_qdrant_shadow_read = cfg.enable_qdrant_shadow_read

        self.storage = get_storage(self.vector_store_path)
        self.vector_store: Optional[Any] = self.storage.load_vector_store(self.embeddings)
        self._vector_revision = 0
        self._invalidate_retrieval_cache()
        qdrant_enabled = (
            self.vector_backend == "qdrant"
            or self.enable_qdrant_dual_write
            or self.enable_qdrant_shadow_read
        )
        self.vector_adapter = QdrantVectorAdapter(
            enabled=qdrant_enabled,
            url=cfg.qdrant_url,
            api_key=cfg.qdrant_api_key,
            collection_name=cfg.qdrant_collection,
            embeddings=self.embeddings,
            primary_backend=self.vector_backend,
            dual_write=self.enable_qdrant_dual_write,
            shadow_read=self.enable_qdrant_shadow_read,
        )
        self.persist_calibration_artifacts = cfg.persist_calibration_artifacts
        self.enable_ragas_in_calibration = cfg.enable_ragas_in_calibration
        self.calibration_artifact_dir = cfg.calibration_artifact_dir

        self.system_prompt = (
            "Bạn là trợ lý AI trả lời dựa trên ngữ cảnh được cung cấp."
            "Tuyệt đối không được tự ý thêm thông tin ngoài ngữ cảnh."
            "Hãy trả lời chính xác dựa trên thông tin đã cho."
            "Nếu không có đủ thông tin trong ngữ cảnh, phải trả lời đúng câu: "
            "'Không tìm thấy thông tin liên quan trong tài liệu đã upload.'."
        )
        self.history_max_messages = 7
        self.history_max_chars = 2000

        self.memory = SessionMemoryStore(
            history_max_messages=self.history_max_messages,
            max_memory_sessions=200,
            session_ttl_seconds=6 * 60 * 60,
        )

    @property
    def session_ttl_seconds(self) -> int:
        return self.memory.session_ttl_seconds

    def clear_session_memory(self, session_id: str) -> bool:
        return self.memory.clear_session_memory(session_id)

    def _invoke_llm(self, prompt: str) -> str:
        return self._llm_client.generate(prompt=prompt, temperature=0.2)

    def _stream_llm(self, prompt: str):
        return self._llm_client.generate_stream(prompt=prompt, temperature=0.2)

    def clear_vector_store(self):
        self.vector_store = None
        self.storage.clear_vector_store()
        self.vector_adapter.clear()
        self._vector_revision += 1
        self._invalidate_retrieval_cache()

    def delete_documents_by_filename(self, filename: str) -> Dict[str, Any]:
        cleaned_filename = str(filename).strip()
        if not cleaned_filename:
            raise ValueError("filename không được để trống")

        removed_source_documents = self.storage.remove_source_documents_by_filename(cleaned_filename)
        removed_qdrant_points = self.vector_adapter.delete_by_filename(cleaned_filename)

        if self.vector_store is None:
            self._vector_revision += 1
            self._invalidate_retrieval_cache()
            return {
                "removed_chunks": 0,
                "removed_source_documents": removed_source_documents,
                "removed_qdrant_points": removed_qdrant_points,
                "document_count": self.vector_adapter.count() if self.vector_backend == "qdrant" else 0,
                "uploaded_files": [],
            }

        target_doc_ids: List[str] = []
        for doc_id, doc in self.vector_store.docstore._dict.items():
            doc_filename = str(doc.metadata.get("filename", "")).strip()
            if doc_filename == cleaned_filename:
                target_doc_ids.append(doc_id)

        if target_doc_ids:
            self.vector_store.delete(ids=target_doc_ids)

        try:
            remaining_documents = int(self.vector_store.index.ntotal)
        except Exception:
            remaining_documents = 0

        if remaining_documents == 0:
            self.vector_store = None
            self.storage.clear_vector_store()
            self._vector_revision += 1
            self._invalidate_retrieval_cache()
            return {
                "removed_chunks": len(target_doc_ids),
                "removed_source_documents": removed_source_documents,
                "removed_qdrant_points": removed_qdrant_points,
                "document_count": 0,
                "uploaded_files": [],
            }

        self.storage.save_vector_store(self.vector_store)
        self._vector_revision += 1
        self._invalidate_retrieval_cache()

        filenames = set()
        for doc in self.vector_store.docstore._dict.values():
            doc_filename = doc.metadata.get("filename")
            if doc_filename:
                filenames.add(str(doc_filename))

        return {
            "removed_chunks": len(target_doc_ids),
            "removed_source_documents": removed_source_documents,
            "removed_qdrant_points": removed_qdrant_points,
            "document_count": remaining_documents,
            "uploaded_files": sorted(filenames),
        }

    def get_stats(self) -> Dict[str, Any]:
        source_documents = self.storage.load_source_documents()
        qdrant_count = self.vector_adapter.count() if self.vector_adapter.enabled else 0
        has_documents = bool(self.vector_store is not None)
        if self.vector_backend == "qdrant":
            has_documents = qdrant_count > 0

        stats = {
            "llm_model": self.llm_model,
            "embedding_model": self.embedding_model,
            "vector_db": "Qdrant" if self.vector_backend == "qdrant" else "FAISS",
            "vector_backend": self.vector_backend,
            "ollama_url": self.ollama_base_url,
            "supported_retrieval_modes": ["vector", "hybrid", "hybrid_multivector"],
            "cross_encoder_model": self.cross_encoder_model,
            "history_max_messages": self.history_max_messages,
            "memory_session_ttl_seconds": self.session_ttl_seconds,
            "default_chunk_size": self.chunk_size,
            "default_chunk_overlap": self.chunk_overlap,
            "chunking_strategy": self.chunking_strategy,
            "multi_vector_enabled": self.enable_multi_vector,
            "context_reorder_enabled": self.enable_context_reorder,
            "context_compression_enabled": self.enable_context_compression,
            "self_rag_confidence_threshold": self.self_rag_confidence_threshold,
            "qdrant_dual_write_enabled": self.enable_qdrant_dual_write,
            "qdrant_shadow_read_enabled": self.enable_qdrant_shadow_read,
            "qdrant_point_count": qdrant_count,
            "has_documents": has_documents,
            "document_count": qdrant_count if self.vector_backend == "qdrant" else 0,
            "uploaded_files": [],
            "source_document_count": len(source_documents),
            "active_memory_sessions": self.memory.active_sessions(),
            "retrieval_cache": self._retrieval_cache_stats(),
        }

        if self.vector_store:
            try:
                if self.vector_backend != "qdrant":
                    stats["document_count"] = self.vector_store.index.ntotal
            except Exception:
                pass

            try:
                filenames = set()
                for doc in self.vector_store.docstore._dict.values():
                    filename = doc.metadata.get("filename")
                    if filename:
                        filenames.add(filename)
                stats["uploaded_files"] = sorted(filenames)
            except Exception:
                pass

        return stats
