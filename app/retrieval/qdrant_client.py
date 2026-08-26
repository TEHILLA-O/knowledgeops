"""Qdrant vector store client."""

import hashlib
import uuid
from typing import Any

from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qmodels
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import Settings, get_settings
from app.core.constants import QDRANT_VECTOR_SIZE
from app.core.exceptions import RetrievalError
from app.core.logging import get_logger

logger = get_logger(__name__)


class QdrantService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.client = AsyncQdrantClient(url=self.settings.qdrant_url, check_compatibility=False)
        self.collection = self.settings.qdrant_collection

    @staticmethod
    def point_id_from_chunk(chunk_id: str) -> str:
        digest = hashlib.sha256(chunk_id.encode()).hexdigest()
        return str(uuid.UUID(digest[:32]))

    async def ensure_collection(self, vector_size: int = QDRANT_VECTOR_SIZE) -> None:
        exists = await self.client.collection_exists(self.collection)
        if exists:
            return
        await self.client.create_collection(
            collection_name=self.collection,
            vectors_config=qmodels.VectorParams(size=vector_size, distance=qmodels.Distance.COSINE),
        )
        logger.info("qdrant_collection_created", collection=self.collection)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    async def upsert_vectors(
        self,
        points: list[dict[str, Any]],
    ) -> None:
        if not points:
            return
        qdrant_points = [
            qmodels.PointStruct(
                id=p["point_id"],
                vector=p["vector"],
                payload=p["payload"],
            )
            for p in points
        ]
        await self.client.upsert(collection_name=self.collection, points=qdrant_points)

    async def delete_by_document_id(self, document_id: str) -> None:
        await self.client.delete(
            collection_name=self.collection,
            points_selector=qmodels.FilterSelector(
                filter=qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(
                            key="document_id",
                            match=qmodels.MatchValue(value=document_id),
                        )
                    ]
                )
            ),
        )

    async def delete_by_point_ids(self, point_ids: list[str]) -> None:
        if not point_ids:
            return
        await self.client.delete(
            collection_name=self.collection,
            points_selector=qmodels.PointIdsList(points=point_ids),
        )

    async def search_dense(
        self,
        vector: list[float],
        limit: int = 20,
        filters: dict[str, Any] | None = None,
    ) -> list[Any]:
        qfilter = self._build_filter(filters) if filters else None
        try:
            response = await self.client.query_points(
                collection_name=self.collection,
                query=vector,
                limit=limit,
                query_filter=qfilter,
                with_payload=True,
            )
            return list(response.points)
        except Exception as exc:
            raise RetrievalError(f"Dense search failed: {exc}") from exc

    async def scroll_all_payloads(self) -> list[dict[str, Any]]:
        payloads: list[dict[str, Any]] = []
        offset = None
        while True:
            records, offset = await self.client.scroll(
                collection_name=self.collection,
                limit=256,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            for record in records:
                if record.payload:
                    payloads.append(dict(record.payload))
            if offset is None:
                break
        return payloads

    async def count_points(self) -> int:
        info = await self.client.get_collection(self.collection)
        return info.points_count or 0

    async def health_check(self) -> bool:
        try:
            await self.client.get_collections()
            return True
        except Exception:
            return False

    def _build_filter(self, filters: dict[str, Any]) -> qmodels.Filter:
        must: list[qmodels.Condition] = []
        for key, value in filters.items():
            if value is None:
                continue
            if key == "allowed_groups":
                must.append(
                    qmodels.FieldCondition(
                        key="allowed_groups",
                        match=qmodels.MatchAny(any=value if isinstance(value, list) else [value]),
                    )
                )
            else:
                must.append(
                    qmodels.FieldCondition(
                        key=key,
                        match=qmodels.MatchValue(value=value),
                    )
                )
        return qmodels.Filter(must=must)
