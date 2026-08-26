"""Benchmark ingestion, embedding, retrieval, and query latency."""

from __future__ import annotations

import statistics
import time
from typing import Any

from app.core.config import get_settings
from app.schemas.common import QueryRequest


async def run_benchmark(*, iterations: int = 3) -> dict[str, Any]:
    """Run performance benchmarks across pipeline stages."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from app.api.deps import IngestionService, QueryOrchestrator, Repositories
    from app.db.models import Base
    from app.generation.service import QueryService as GenerationQueryService
    from app.knowledge_gaps.service import KnowledgeGapService
    from app.providers.factory import create_embedding_provider
    from app.retrieval.service import RetrievalService
    from scripts.setup_demo import setup_demo

    settings = get_settings()
    setup_demo(reset_index=True)

    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session = session_factory()
    from app.retrieval.qdrant_client import QdrantService

    qdrant = QdrantService(settings)
    embedding = create_embedding_provider(settings)
    await qdrant.ensure_collection(embedding.vector_size)

    results: dict[str, Any] = {"iterations": iterations}

    try:
        ingestion_times: list[float] = []
        for _ in range(iterations):
            start = time.perf_counter()
            service = IngestionService(session, qdrant, settings)
            await service.run(source="demo")
            await session.commit()
            ingestion_times.append(time.perf_counter() - start)
        results["ingestion_seconds"] = {
            "mean": round(statistics.mean(ingestion_times), 3),
            "min": round(min(ingestion_times), 3),
            "max": round(max(ingestion_times), 3),
        }

        embed_texts = [
            "Vacation policy for full-time employees",
            "VPN connection and password reset procedures",
            "Security incident reporting requirements",
        ]
        embed_times: list[float] = []
        for _ in range(iterations):
            start = time.perf_counter()
            await embedding.embed_batch(embed_texts)
            embed_times.append(time.perf_counter() - start)
        results["embedding_seconds"] = {
            "mean": round(statistics.mean(embed_times), 4),
            "texts_per_batch": len(embed_texts),
        }

        retrieval = RetrievalService(qdrant=qdrant, embedding_provider=embedding, settings=settings)
        retrieval_times: list[float] = []
        for _ in range(iterations):
            start = time.perf_counter()
            await retrieval.search("What is the vacation policy?", top_k=5)
            retrieval_times.append(time.perf_counter() - start)
        results["retrieval_seconds"] = {
            "mean": round(statistics.mean(retrieval_times), 4),
            "mean_ms": round(statistics.mean(retrieval_times) * 1000, 1),
        }

        repos = Repositories(session)
        generation = GenerationQueryService(retrieval_service=retrieval, settings=settings)
        gap_service = KnowledgeGapService(repos.knowledge_gaps, settings)
        orchestrator = QueryOrchestrator(repos, generation, retrieval, gap_service)

        query_times: list[float] = []
        for _ in range(iterations):
            start = time.perf_counter()
            await orchestrator.query(QueryRequest(query="How many vacation days do employees get?"))
            await session.commit()
            query_times.append(time.perf_counter() - start)
        results["query_seconds"] = {
            "mean": round(statistics.mean(query_times), 4),
            "mean_ms": round(statistics.mean(query_times) * 1000, 1),
        }
    finally:
        await session.close()
        await engine.dispose()

    return results


if __name__ == "__main__":
    import asyncio
    import json

    print(json.dumps(asyncio.run(run_benchmark()), indent=2))
