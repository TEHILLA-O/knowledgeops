"""Hybrid dense + sparse retrieval with score fusion."""

from app.core.logging import get_logger
from app.retrieval.dense import DenseRetriever
from app.retrieval.sparse import SparseRetriever
from app.schemas.common import RetrievalFilters, RetrievedChunk

logger = get_logger(__name__)


def _normalize_score_map(chunks: list[RetrievedChunk], score_attr: str) -> dict[str, float]:
    scores = [getattr(c, score_attr) or 0.0 for c in chunks]
    if not scores:
        return {}
    max_score = max(scores)
    min_score = min(scores)
    if max_score == min_score:
        norm = 1.0 if max_score > 0 else 0.0
        return {c.chunk_id: norm for c in chunks}
    span = max_score - min_score
    return {
        c.chunk_id: ((getattr(c, score_attr) or 0.0) - min_score) / span for c in chunks
    }


class HybridRetriever:
    """Fuses dense and sparse retrieval results with configurable alpha."""

    def __init__(
        self,
        dense: DenseRetriever,
        sparse: SparseRetriever,
        alpha: float = 0.5,
    ) -> None:
        self.dense = dense
        self.sparse = sparse
        self.alpha = alpha

    async def search(
        self,
        query: str,
        dense_top_k: int = 20,
        sparse_top_k: int = 20,
        fusion_top_k: int = 30,
        filters: RetrievalFilters | None = None,
        alpha: float | None = None,
    ) -> list[RetrievedChunk]:
        blend = alpha if alpha is not None else self.alpha

        dense_results = await self.dense.search(query, top_k=dense_top_k, filters=filters)
        sparse_results = await self.sparse.search(query, top_k=sparse_top_k, filters=filters)

        dense_norm = _normalize_score_map(dense_results, "dense_score")
        sparse_norm = _normalize_score_map(sparse_results, "sparse_score")

        merged: dict[str, RetrievedChunk] = {}
        for chunk in dense_results + sparse_results:
            if chunk.chunk_id not in merged:
                merged[chunk.chunk_id] = chunk.model_copy(deep=True)
            else:
                existing = merged[chunk.chunk_id]
                if chunk.dense_score is not None:
                    existing.dense_score = chunk.dense_score
                if chunk.sparse_score is not None:
                    existing.sparse_score = chunk.sparse_score

        fused: list[RetrievedChunk] = []
        for chunk_id, chunk in merged.items():
            d_score = dense_norm.get(chunk_id, 0.0)
            s_score = sparse_norm.get(chunk_id, 0.0)
            fusion = blend * d_score + (1.0 - blend) * s_score
            chunk.fusion_score = fusion
            fused.append(chunk)

        fused.sort(key=lambda c: c.fusion_score or 0.0, reverse=True)
        result = fused[:fusion_top_k]
        logger.debug(
            "hybrid_retrieval_complete",
            dense=len(dense_results),
            sparse=len(sparse_results),
            fused=len(result),
            alpha=blend,
        )
        return result
