"""Dense vector retrieval via Qdrant."""

from typing import Any

from app.core.logging import get_logger
from app.providers.base import EmbeddingProvider
from app.retrieval.qdrant_client import QdrantService
from app.schemas.common import RetrievalFilters, RetrievedChunk

logger = get_logger(__name__)


def _payload_to_chunk(payload: dict[str, Any], dense_score: float | None = None) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=str(payload.get("chunk_id", "")),
        document_id=str(payload.get("document_id", "")),
        document_title=str(payload.get("document_title", "")),
        document_version=int(payload.get("document_version", 1)),
        content=str(payload.get("content", "")),
        dense_score=dense_score,
        section=payload.get("section"),
        page_number=payload.get("page_number"),
        source_url=payload.get("source_url"),
        metadata={
            k: v
            for k, v in payload.items()
            if k
            not in {
                "chunk_id",
                "document_id",
                "document_title",
                "document_version",
                "content",
                "section",
                "page_number",
                "source_url",
            }
        },
    )


def filters_to_qdrant_dict(filters: RetrievalFilters | None) -> dict[str, Any]:
    """Convert RetrievalFilters to Qdrant filter payload (excludes user_group)."""
    if not filters:
        return {}
    result: dict[str, Any] = {}
    for field in ("source", "document_type", "department", "classification", "version"):
        value = getattr(filters, field, None)
        if value is not None:
            result[field] = value
    if filters.tag:
        result["tags"] = filters.tag
    return result


class DenseRetriever:
    """Retrieves chunks using dense vector similarity search."""

    def __init__(
        self,
        qdrant: QdrantService,
        embedding_provider: EmbeddingProvider,
    ) -> None:
        self.qdrant = qdrant
        self.embedding_provider = embedding_provider

    async def search(
        self,
        query: str,
        top_k: int = 20,
        filters: RetrievalFilters | None = None,
    ) -> list[RetrievedChunk]:
        vector = await self.embedding_provider.embed_text(query)
        qdrant_filters = filters_to_qdrant_dict(filters)

        results = await self.qdrant.search_dense(
            vector=vector,
            limit=top_k,
            filters=qdrant_filters or None,
        )

        chunks: list[RetrievedChunk] = []
        for point in results:
            if not point.payload:
                continue
            payload = dict(point.payload)
            chunks.append(_payload_to_chunk(payload, dense_score=float(point.score)))

        logger.debug("dense_retrieval_complete", query_len=len(query), results=len(chunks))
        return chunks
