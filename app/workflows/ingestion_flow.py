"""Prefect ingestion workflow matching the ingestion pipeline spec."""

from __future__ import annotations

from typing import Any

from prefect import flow, get_run_logger, task

from app.core.config import Settings, get_settings
from app.schemas.common import IngestionRunSummary


@task(name="discover-documents", retries=2, retry_delay_seconds=5)
async def discover_documents_task(source_name: str, settings: Settings | None = None) -> str:
    """Validate source configuration and return source name for downstream tasks."""
    settings = settings or get_settings()
    sources = settings.ingestion_config.get("sources", {})
    if source_name == "demo":
        if not sources.get("demo", {}).get("enabled", True):
            raise ValueError("Demo source is disabled in ingestion config")
    elif source_name not in sources and source_name != "local_folder":
        get_run_logger().warning(
            "Source '%s' not in config; using local_folder fallback", source_name
        )
    return source_name


@task(name="run-ingestion-pipeline", retries=1, retry_delay_seconds=10)
async def run_ingestion_pipeline_task(
    source_name: str,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Execute the full discover -> parse -> chunk -> embed -> index pipeline."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from app.api.deps import IngestionService
    from app.db.models import Base
    from app.retrieval.qdrant_client import QdrantService

    settings = settings or get_settings()
    logger = get_run_logger()
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session = session_factory()
    qdrant = QdrantService(settings)
    try:
        service = IngestionService(session, qdrant, settings)
        logger.info("Starting ingestion for source: %s", source_name)
        summary: IngestionRunSummary = await service.run(source=source_name)
        await session.commit()
        logger.info(
            "Ingestion complete: %s new, %s modified, %s unchanged, %s deleted",
            summary.documents_new,
            summary.documents_modified,
            summary.documents_unchanged,
            summary.documents_deleted,
        )
        return summary.model_dump()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
        await engine.dispose()


@task(name="record-ingestion-metrics")
async def record_ingestion_metrics_task(summary: dict[str, Any]) -> dict[str, Any]:
    """Attach workflow metadata to the ingestion summary."""
    logger = get_run_logger()
    metrics = {
        **summary,
        "workflow": "ingestion_flow",
        "health_ok": summary.get("health_status") in ("HEALTHY", None),
        "chunks_per_document": (
            summary.get("chunks_indexed", 0) / max(summary.get("documents_discovered", 1), 1)
        ),
    }
    logger.info("Ingestion metrics recorded: %s chunks indexed", metrics.get("chunks_indexed", 0))
    return metrics


@flow(name="knowledgeops-ingestion", log_prints=True)
async def ingestion_flow(source: str = "demo") -> dict[str, Any]:
    """
    Prefect flow orchestrating document ingestion.

    Steps:
    1. Discover documents from configured source
    2. Detect changes (new / modified / unchanged / deleted)
    3. Parse, clean, chunk, embed, and index
    4. Record run metrics and health status
    """
    settings = get_settings()
    validated_source = await discover_documents_task(source, settings)
    summary = await run_ingestion_pipeline_task(validated_source, settings)
    return await record_ingestion_metrics_task(summary)


async def run_ingestion_flow(source: str = "demo") -> dict[str, Any]:
    """Convenience entry point for programmatic or CLI invocation."""
    return await ingestion_flow(source=source)
