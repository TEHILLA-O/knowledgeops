"""Integration tests for the ingestion pipeline."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.discovery.local_folder import LocalFolderSource
from app.ingestion.pipeline import IngestionPipeline
from app.providers.mock_embedding import MockEmbeddingProvider
from tests.conftest import MockQdrantService


@pytest.mark.integration
@pytest.mark.asyncio
async def test_ingestion_pipeline_indexes_documents(
    db_session: AsyncSession,
    test_settings,
    mock_qdrant: MockQdrantService,
    mock_embedding: MockEmbeddingProvider,
) -> None:
    source = LocalFolderSource(
        folder_path=test_settings.demo_knowledge_path,
        source_name="demo",
        settings=test_settings,
    )
    pipeline = IngestionPipeline(
        db_session,
        mock_qdrant,  # type: ignore[arg-type]
        mock_embedding,
        settings=test_settings,
    )
    summary = await pipeline.run(source)
    await db_session.commit()

    assert summary.documents_discovered >= 2
    assert summary.documents_new >= 2
    assert summary.chunks_indexed > 0
    assert summary.status in ("COMPLETED", "PARTIAL")
    assert await mock_qdrant.count_points() > 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_ingestion_detects_unchanged_on_second_run(
    db_session: AsyncSession,
    test_settings,
    mock_qdrant: MockQdrantService,
    mock_embedding: MockEmbeddingProvider,
) -> None:
    source = LocalFolderSource(
        folder_path=test_settings.demo_knowledge_path,
        source_name="demo",
        settings=test_settings,
    )
    pipeline = IngestionPipeline(
        db_session,
        mock_qdrant,  # type: ignore[arg-type]
        mock_embedding,
        settings=test_settings,
    )
    await pipeline.run(source)
    await db_session.commit()
    summary2 = await pipeline.run(source)
    await db_session.commit()

    assert summary2.documents_unchanged >= 2
    assert summary2.documents_new == 0
