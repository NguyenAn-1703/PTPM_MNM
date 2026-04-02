"""Optional vector backend adapter for Qdrant dual-write and shadow-read migration."""
from datetime import datetime
import logging
import uuid
from typing import Any, Dict, List, Optional


logger = logging.getLogger(__name__)


class QdrantVectorAdapter:
    def __init__(
        self,
        *,
        enabled: bool,
        url: str,
        api_key: str,
        collection_name: str,
        embeddings: Any,
        primary_backend: str,
        dual_write: bool,
        shadow_read: bool,
    ):
        self.enabled = bool(enabled)
        self.url = url
        self.api_key = api_key
        self.collection_name = collection_name
        self.embeddings = embeddings
        self.primary_backend = primary_backend
        self.dual_write = bool(dual_write)
        self.shadow_read = bool(shadow_read)

        self._client = None
        self._models = None
        self._initialized = False

    def _get_client(self):
        if not self.enabled:
            return None
        if self._client is not None:
            return self._client

        try:
            from qdrant_client import QdrantClient
            from qdrant_client import models
        except Exception as exc:
            logger.warning("Qdrant client unavailable: %s", exc)
            self.enabled = False
            return None

        try:
            self._client = QdrantClient(url=self.url, api_key=self.api_key or None, timeout=20)
            self._models = models
            return self._client
        except Exception as exc:
            logger.warning("Qdrant init failed: %s", exc)
            self.enabled = False
            return None

    def _ensure_collection(self, embedding_dim: int) -> bool:
        client = self._get_client()
        if client is None:
            return False
        if self._initialized:
            return True

        try:
            existing = client.collection_exists(collection_name=self.collection_name)
            if not existing:
                client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=self._models.VectorParams(size=embedding_dim, distance=self._models.Distance.COSINE),
                )
            self._initialized = True
            return True
        except Exception as exc:
            logger.warning("Failed to ensure Qdrant collection %s: %s", self.collection_name, exc)
            return False

    def _build_filter(self, metadata_filters: Optional[Dict[str, Any]]):
        if not metadata_filters or self._models is None:
            return None

        must_conditions = []

        filenames = [item for item in (metadata_filters.get("filenames") or []) if str(item).strip()]
        if filenames:
            must_conditions.append(
                self._models.FieldCondition(
                    key="metadata.filename",
                    match=self._models.MatchAny(any=filenames),
                )
            )

        file_types = [item for item in (metadata_filters.get("file_types") or []) if str(item).strip()]
        if file_types:
            must_conditions.append(
                self._models.FieldCondition(
                    key="metadata.file_type",
                    match=self._models.MatchAny(any=file_types),
                )
            )

        vector_roles = [item for item in (metadata_filters.get("vector_roles") or []) if str(item).strip()]
        if vector_roles:
            must_conditions.append(
                self._models.FieldCondition(
                    key="metadata.vector_role",
                    match=self._models.MatchAny(any=vector_roles),
                )
            )

        tags = [item for item in (metadata_filters.get("tags") or []) if str(item).strip()]
        if tags:
            must_conditions.append(
                self._models.FieldCondition(
                    key="metadata.tags",
                    match=self._models.MatchAny(any=tags),
                )
            )

        page_from = metadata_filters.get("page_from")
        page_to = metadata_filters.get("page_to")
        if page_from is not None or page_to is not None:
            must_conditions.append(
                self._models.FieldCondition(
                    key="metadata.page_number",
                    range=self._models.Range(gte=page_from, lte=page_to),
                )
            )

        uploaded_after = self._to_timestamp(metadata_filters.get("uploaded_after"))
        uploaded_before = self._to_timestamp(metadata_filters.get("uploaded_before"))
        if uploaded_after is not None or uploaded_before is not None:
            must_conditions.append(
                self._models.FieldCondition(
                    key="metadata.uploaded_at_ts",
                    range=self._models.Range(gte=uploaded_after, lte=uploaded_before),
                )
            )

        if not must_conditions:
            return None

        return self._models.Filter(must=must_conditions)

    @staticmethod
    def _to_timestamp(value: Any) -> Optional[float]:
        if value in (None, ""):
            return None
        if isinstance(value, (int, float)):
            return float(value)

        text = str(value).strip()
        if not text:
            return None

        try:
            return float(text)
        except (TypeError, ValueError):
            pass

        try:
            if text.endswith("Z"):
                text = text[:-1] + "+00:00"
            return datetime.fromisoformat(text).timestamp()
        except (TypeError, ValueError):
            return None

    def should_use_as_primary(self) -> bool:
        return self.enabled and self.primary_backend == "qdrant"

    def should_dual_write(self) -> bool:
        return self.enabled and self.dual_write

    def should_shadow_read(self) -> bool:
        return self.enabled and self.shadow_read

    def upsert_texts(self, texts: List[str], metadatas: List[Dict[str, Any]]) -> int:
        client = self._get_client()
        if client is None or not texts:
            return 0

        try:
            vectors = self.embeddings.embed_documents(texts)
            if not vectors:
                return 0

            if not self._ensure_collection(len(vectors[0])):
                return 0

            points = []
            for idx, vector in enumerate(vectors):
                metadata = metadatas[idx] if idx < len(metadatas) else {}
                points.append(
                    self._models.PointStruct(
                        id=str(uuid.uuid4()),
                        vector=vector,
                        payload={
                            "content": texts[idx],
                            "metadata": metadata or {},
                        },
                    )
                )

            client.upsert(collection_name=self.collection_name, points=points)
            return len(points)
        except Exception as exc:
            logger.warning("Qdrant upsert failed: %s", exc)
            return 0

    def search(self, query: str, top_k: int, metadata_filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        client = self._get_client()
        if client is None or not query.strip():
            return []

        try:
            query_vector = self.embeddings.embed_query(query)
            if not query_vector:
                return []
            if not self._ensure_collection(len(query_vector)):
                return []

            query_filter = self._build_filter(metadata_filters)
            results = client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                query_filter=query_filter,
                limit=max(1, top_k),
                with_payload=True,
            )

            search_results: List[Dict[str, Any]] = []
            for item in results:
                payload = item.payload or {}
                metadata = payload.get("metadata") or {}
                score = float(1.0 - float(item.score))
                search_results.append(
                    {
                        "content": str(payload.get("content", "")),
                        "metadata": metadata,
                        "score": score,
                    }
                )
            return search_results
        except Exception as exc:
            logger.warning("Qdrant search failed: %s", exc)
            return []

    def delete_by_filename(self, filename: str) -> int:
        client = self._get_client()
        if client is None or not filename:
            return 0

        try:
            query_filter = self._models.Filter(
                must=[
                    self._models.FieldCondition(
                        key="metadata.filename",
                        match=self._models.MatchValue(value=filename),
                    )
                ]
            )
            client.delete(collection_name=self.collection_name, points_selector=query_filter)
            return 1
        except Exception as exc:
            logger.warning("Qdrant delete by filename failed: %s", exc)
            return 0

    def clear(self) -> None:
        client = self._get_client()
        if client is None:
            return

        try:
            client.delete_collection(collection_name=self.collection_name)
            self._initialized = False
        except Exception as exc:
            logger.warning("Qdrant clear failed: %s", exc)

    def count(self) -> int:
        client = self._get_client()
        if client is None:
            return 0
        try:
            response = client.count(collection_name=self.collection_name, exact=False)
            return int(response.count)
        except Exception:
            return 0
