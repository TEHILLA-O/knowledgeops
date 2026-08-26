"""Reranking for retrieved chunks."""

from abc import ABC, abstractmethod

from app.core.logging import get_logger
from app.providers.base import RerankingProvider as DocumentRerankerProvider
from app.schemas.common import RetrievedChunk

logger = get_logger(__name__)


class RerankingProvider(ABC):
    """Abstract chunk-level reranker for the retrieval pipeline."""

    @abstractmethod
    async def rerank_chunks(
        self,
        query: str,
        chunks: list[RetrievedChunk],
    ) -> list[RetrievedChunk]:
        """Rerank chunks and attach rerank_score."""


class LocalReranker(RerankingProvider):
    """Reranks chunks using a cross-encoder or score-fusion fallback."""

    def __init__(self, provider: DocumentRerankerProvider | None = None) -> None:
        self._provider = provider

    async def rerank_chunks(
        self,
        query: str,
        chunks: list[RetrievedChunk],
    ) -> list[RetrievedChunk]:
        if not chunks:
            return []

        if self._provider is not None:
            try:
                documents = [c.content for c in chunks]
                ranked = await self._provider.rerank(query, documents)
                reranked: list[RetrievedChunk] = []
                for idx, score in ranked:
                    chunk = chunks[idx].model_copy(deep=True)
                    chunk.rerank_score = score
                    reranked.append(chunk)
                logger.debug("cross_encoder_rerank_complete", count=len(reranked))
                return reranked
            except Exception as exc:
                logger.warning("cross_encoder_rerank_failed", error=str(exc))

        return self._fusion_fallback(chunks)

    @staticmethod
    def _fusion_fallback(chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
        """Fall back to existing fusion/dense/sparse scores when cross-encoder unavailable."""
        reranked: list[RetrievedChunk] = []
        for chunk in chunks:
            updated = chunk.model_copy(deep=True)
            score = (
                chunk.rerank_score
                or chunk.fusion_score
                or chunk.dense_score
                or chunk.sparse_score
                or 0.0
            )
            updated.rerank_score = float(score)
            reranked.append(updated)
        reranked.sort(key=lambda c: c.rerank_score or 0.0, reverse=True)
        logger.debug("fusion_fallback_rerank_complete", count=len(reranked))
        return reranked
