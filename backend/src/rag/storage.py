"""Persistent storage helpers for vector store and source registry."""
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional


logger = logging.getLogger(__name__)


class RagStorage:
    """File-system persistence layer for FAISS index and source docs."""

    def __init__(self, vector_store_path: Path):
        self.vector_store_path = vector_store_path
        self.source_registry_path = self.vector_store_path / "source_documents.json"

    def load_vector_store(self, embeddings: Any) -> Optional[Any]:
        """Load vector store from disk if exists."""
        try:
            index_path = self.vector_store_path / "index.faiss"
            if index_path.exists():
                from langchain_community.vectorstores import FAISS

                return FAISS.load_local(
                    str(self.vector_store_path),
                    embeddings,
                    allow_dangerous_deserialization=True,
                )
        except Exception as exc:
            logger.warning("Could not load vector store: %s", exc)
        return None

    def save_vector_store(self, vector_store: Any) -> None:
        """Save vector store to disk."""
        if not vector_store:
            return
        self.vector_store_path.mkdir(parents=True, exist_ok=True)
        vector_store.save_local(str(self.vector_store_path))

    def load_source_documents(self) -> List[Dict[str, Any]]:
        """Load extracted source documents for chunk strategy evaluation."""
        if not self.source_registry_path.exists():
            return []

        try:
            with self.source_registry_path.open("r", encoding="utf-8") as fp:
                data = json.load(fp)
                if isinstance(data, list):
                    return data
        except Exception as exc:
            logger.warning("Could not load source registry: %s", exc)

        return []

    def save_source_documents(self, docs: List[Dict[str, Any]]) -> None:
        self.vector_store_path.mkdir(parents=True, exist_ok=True)
        with self.source_registry_path.open("w", encoding="utf-8") as fp:
            json.dump(docs, fp, ensure_ascii=False, indent=2)

    def persist_source_document(self, text: str, metadata: Optional[Dict[str, Any]]) -> None:
        """Persist original extracted text so we can re-index with different chunk settings."""
        docs = self.load_source_documents()
        docs.append(
            {
                "text": text,
                "metadata": metadata or {},
            }
        )
        self.save_source_documents(docs)

    def remove_source_documents_by_filename(self, filename: str) -> int:
        docs = self.load_source_documents()
        if not docs:
            return 0

        remaining_docs = [
            item
            for item in docs
            if str((item.get("metadata") or {}).get("filename", "")).strip() != filename
        ]
        removed_count = len(docs) - len(remaining_docs)

        if removed_count > 0:
            self.save_source_documents(remaining_docs)

        return removed_count

    def clear_vector_store(self) -> None:
        if self.vector_store_path.exists():
            import shutil

            shutil.rmtree(self.vector_store_path)
