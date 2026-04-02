"""Indexing and ingestion helpers for document chunks."""
import hashlib
import logging
import re
import uuid
from typing import Any, Dict, List, Optional

from .text import normalize_chunk_params, split_text_with_offsets


logger = logging.getLogger(__name__)


class RAGIndexingMixin:
    @staticmethod
    def _estimate_token_count(text: str) -> int:
        return len(re.findall(r"[A-Za-z0-9À-ỹ]+", text or ""))

    @staticmethod
    def _build_auxiliary_texts(content: str) -> List[Dict[str, str]]:
        normalized = (content or "").strip()
        if not normalized:
            return []

        summary = normalized if len(normalized) <= 260 else normalized[:260].rsplit(" ", 1)[0].strip()
        keyword_candidates = re.findall(r"[A-Za-z0-9À-ỹ]{5,}", normalized.lower())
        unique_keywords: List[str] = []
        for token in keyword_candidates:
            if token not in unique_keywords:
                unique_keywords.append(token)
            if len(unique_keywords) >= 8:
                break

        hypothetic_query = ""
        if unique_keywords:
            hypothetic_query = f"Thông tin liên quan đến: {', '.join(unique_keywords)}"

        views: List[Dict[str, str]] = []
        if summary and summary != normalized:
            views.append({"vector_role": "summary", "content": summary})
        if hypothetic_query:
            views.append({"vector_role": "hypo_question", "content": hypothetic_query})
        return views

    def add_documents(
        self,
        text: str,
        metadata: Dict[str, Any] = None,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        source_segments: Optional[List[Dict[str, Any]]] = None,
    ) -> int:
        if not text.strip():
            raise ValueError("Text rỗng, không thể thêm vào vector store")

        normalized_chunk_size, normalized_chunk_overlap = normalize_chunk_params(
            default_size=self.chunk_size,
            default_overlap=self.chunk_overlap,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        chunking_strategy = getattr(self, "chunking_strategy", "fixed")
        enable_multi_vector = bool(getattr(self, "enable_multi_vector", False))
        source_doc_id = str((metadata or {}).get("source_doc_id") or uuid.uuid4().hex)

        chunks: List[str] = []
        metadatas: List[Dict[str, Any]] = []
        parent_units: List[Dict[str, Any]] = []

        if source_segments:
            for segment in source_segments:
                segment_text = str(segment.get("text", "")).strip()
                if not segment_text:
                    continue

                segment_start = int(segment.get("char_start", 0))
                segment_page = segment.get("page_number")

                segment_chunks = split_text_with_offsets(
                    segment_text,
                    chunk_size=normalized_chunk_size,
                    chunk_overlap=normalized_chunk_overlap,
                    base_offset=segment_start,
                    strategy=chunking_strategy,
                )

                for seg_chunk in segment_chunks:
                    parent_units.append(
                        {
                            "content": seg_chunk["content"],
                            "metadata": {
                                "chunk_size": normalized_chunk_size,
                                "chunk_overlap": normalized_chunk_overlap,
                                "chunking_strategy": chunking_strategy,
                                "page_number": segment_page,
                                "char_start": seg_chunk["char_start"],
                                "char_end": seg_chunk["char_end"],
                                **(metadata or {}),
                            },
                        }
                    )
        else:
            fallback_chunks = split_text_with_offsets(
                text,
                chunk_size=normalized_chunk_size,
                chunk_overlap=normalized_chunk_overlap,
                base_offset=0,
                strategy=chunking_strategy,
            )

            for fallback_chunk in fallback_chunks:
                parent_units.append(
                    {
                        "content": fallback_chunk["content"],
                        "metadata": {
                            "chunk_size": normalized_chunk_size,
                            "chunk_overlap": normalized_chunk_overlap,
                            "chunking_strategy": chunking_strategy,
                            "char_start": fallback_chunk["char_start"],
                            "char_end": fallback_chunk["char_end"],
                            **(metadata or {}),
                        },
                    }
                )

        logger.info("Processing %s parent chunks", len(parent_units))

        if not parent_units:
            raise ValueError("Không thể chia text thành chunks")

        total_parents = len(parent_units)
        for i, unit in enumerate(parent_units):
            base_metadata = unit["metadata"]
            content = unit["content"]
            chunk_hash = hashlib.sha1(content.encode("utf-8")).hexdigest()[:16]
            parent_chunk_id = f"{source_doc_id}:{base_metadata.get('char_start', 0)}:{base_metadata.get('char_end', 0)}"

            primary_metadata = {
                **base_metadata,
                "source_doc_id": source_doc_id,
                "chunk_index": i,
                "total_chunks": total_parents,
                "parent_chunk_id": parent_chunk_id,
                "vector_role": "content",
                "token_count": self._estimate_token_count(content),
                "chunk_hash": chunk_hash,
                "is_auxiliary": False,
            }

            chunks.append(content)
            metadatas.append(primary_metadata)

            if not enable_multi_vector:
                continue

            for aux in self._build_auxiliary_texts(content):
                aux_content = aux["content"]
                aux_metadata = {
                    **primary_metadata,
                    "vector_role": aux["vector_role"],
                    "token_count": self._estimate_token_count(aux_content),
                    "is_auxiliary": True,
                }
                chunks.append(aux_content)
                metadatas.append(aux_metadata)

        if self.vector_store is None:
            from langchain_community.vectorstores import FAISS

            self.vector_store = FAISS.from_texts(
                texts=chunks,
                embedding=self.embeddings,
                metadatas=metadatas,
            )
        else:
            self.vector_store.add_texts(
                texts=chunks,
                metadatas=metadatas,
            )

        if hasattr(self, "vector_adapter") and self.vector_adapter.should_dual_write():
            qdrant_upserted = self.vector_adapter.upsert_texts(chunks, metadatas)
            logger.info("Qdrant dual-write upserted=%s", qdrant_upserted)

        self.storage.save_vector_store(self.vector_store)
        self.storage.persist_source_document(
            text=text,
            metadata={
                "chunk_size": normalized_chunk_size,
                "chunk_overlap": normalized_chunk_overlap,
                "chunking_strategy": chunking_strategy,
                "source_doc_id": source_doc_id,
                "multi_vector": enable_multi_vector,
                **(metadata or {}),
            },
        )

        return len(chunks)
