"""Indexing and ingestion helpers for document chunks."""
import logging
from typing import Any, Dict, List, Optional

from .text import normalize_chunk_params, split_text_with_offsets


logger = logging.getLogger(__name__)


class RAGIndexingMixin:
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

        chunks: List[str] = []
        metadatas: List[Dict[str, Any]] = []

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
                )

                for seg_chunk in segment_chunks:
                    chunks.append(seg_chunk["content"])
                    metadatas.append(
                        {
                            "chunk_size": normalized_chunk_size,
                            "chunk_overlap": normalized_chunk_overlap,
                            "page_number": segment_page,
                            "char_start": seg_chunk["char_start"],
                            "char_end": seg_chunk["char_end"],
                            **(metadata or {}),
                        }
                    )
        else:
            fallback_chunks = split_text_with_offsets(
                text,
                chunk_size=normalized_chunk_size,
                chunk_overlap=normalized_chunk_overlap,
                base_offset=0,
            )

            for fallback_chunk in fallback_chunks:
                chunks.append(fallback_chunk["content"])
                metadatas.append(
                    {
                        "chunk_size": normalized_chunk_size,
                        "chunk_overlap": normalized_chunk_overlap,
                        "char_start": fallback_chunk["char_start"],
                        "char_end": fallback_chunk["char_end"],
                        **(metadata or {}),
                    }
                )

        logger.info("Processing %s chunks", len(chunks))

        if not chunks:
            raise ValueError("Không thể chia text thành chunks")

        for i in range(len(chunks)):
            metadatas[i] = {
                **metadatas[i],
                "chunk_index": i,
                "total_chunks": len(chunks),
            }

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

        self.storage.save_vector_store(self.vector_store)
        self.storage.persist_source_document(
            text=text,
            metadata={
                "chunk_size": normalized_chunk_size,
                "chunk_overlap": normalized_chunk_overlap,
                **(metadata or {}),
            },
        )

        return len(chunks)
