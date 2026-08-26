"""Retrieval orchestration service."""

import time
from typing import Any

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.providers.base import EmbeddingProvider
from app.providers.base import RerankingProvider as DocumentRerankerProvider
from app.providers.factory import create_embedding_provider, create_reranking_provider
from app.retrieval.context_builder import ContextBuilder
from app.retrieval.dense import DenseRetriever
from app.retrieval.hybrid import HybridRetriever
from app.retrieval.permissions import PermissionFilter
from app.retrieval.qdrant_client import QdrantService
from app.retrieval.reranker import LocalReranker
from app.retrieval.sparse import SparseRetriever
from app.schemas.common import RetrievalFilters, RetrievedChunk

logger = get_logger(__name__)


class RetrievalService:
    """Orchestrates hybrid search, permission filtering, reranking, and context building."""

    def __init__(
        self,
        qdrant: QdrantService | None = None,
        embedding_provider: EmbeddingProvider | None = None,
        reranker_provider: DocumentRerankerProvider | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.qdrant = qdrant or QdrantService(self.settings)
        self.embedding_provider = embedding_provider or create_embedding_provider(self.settings)
        self._retrieval_cfg = self.settings.retrieval_config.get("retrieval", {})

        dense = DenseRetriever(self.qdrant, self.embedding_provider)
        sparse = SparseRetriever(self.qdrant)
        alpha = float(self._retrieval_cfg.get("hybrid_alpha", 0.5))
        self.hybrid = HybridRetriever(dense, sparse, alpha=alpha)
        self.dense = dense
        self.sparse = sparse

        reranker_provider = reranker_provider if reranker_provider is not None else create_reranking_provider(
            self.settings
        )
        self.reranker = LocalReranker(provider=reranker_provider)
        self.permissions = PermissionFilter()
        self.context_builder = ContextBuilder(
            max_context_tokens=int(self._retrieval_cfg.get("max_context_tokens", 4000)),
            context_top_k=int(self._retrieval_cfg.get("context_top_k", 5)),
            source_diversity=bool(self._retrieval_cfg.get("source_diversity", True)),
        )

    async def search(
        self,
        query: str,
        filters: RetrievalFilters | None = None,
        user_group: str | None = None,
        top_k: int | None = None,
    ) -> tuple[list[RetrievedChunk], dict[str, Any]]:
        """Run full retrieval pipeline and return chunks with debug metadata."""
        start = time.perf_counter()
        user_group = user_group or (filters.user_group if filters else None) or self.settings.default_user_group

        dense_top_k = int(self._retrieval_cfg.get("dense_top_k", 20))
        sparse_top_k = int(self._retrieval_cfg.get("sparse_top_k", 20))
        fusion_top_k = int(self._retrieval_cfg.get("fusion_top_k", 30))
        rerank_top_k = top_k or int(self._retrieval_cfg.get("rerank_top_k", 8))
        enable_hybrid = bool(self._retrieval_cfg.get("enable_hybrid", True))

        if enable_hybrid:
            candidates = await self.hybrid.search(
                query,
                dense_top_k=dense_top_k,
                sparse_top_k=sparse_top_k,
                fusion_top_k=fusion_top_k,
                filters=filters,
            )
        else:
            candidates = await self.dense.search(query, top_k=dense_top_k, filters=filters)

        pre_filter_count = len(candidates)
        candidates = self.permissions.filter_chunks(candidates, user_group)

        if bool(self._retrieval_cfg.get("enable_reranking", True)):
            reranked = await self.reranker.rerank_chunks(query, candidates)
            min_score = float(self._retrieval_cfg.get("min_rerank_score", 0.1))
            results = [c for c in reranked if (c.rerank_score or 0.0) >= min_score][:rerank_top_k]
        else:
            results = candidates[:rerank_top_k]

        latency_ms = int((time.perf_counter() - start) * 1000)
        debug = {
            "pre_filter_count": pre_filter_count,
            "post_filter_count": len(candidates),
            "result_count": len(results),
            "hybrid_enabled": enable_hybrid,
            "latency_ms": latency_ms,
        }
        return results, debug

    async def build_context(
        self,
        query: str,
        filters: RetrievalFilters | None = None,
        user_group: str | None = None,
    ) -> tuple[str, list[RetrievedChunk], dict[str, Any]]:
        """Retrieve, filter, rerank, and assemble generation context."""
        chunks, debug = await self.search(query, filters=filters, user_group=user_group)
        context_text, selected = self.context_builder.build(chunks)
        debug["context_chunks"] = len(selected)
        debug["context_tokens"] = len(context_text.split())
        return context_text, selected, debug
