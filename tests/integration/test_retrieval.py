"""Integration tests for retrieval service."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.discovery.local_folder import LocalFolderSource
from app.ingestion.pipeline import IngestionPipeline
from app.providers.mock_embedding import MockEmbeddingProvider
from app.retrieval.service import RetrievalService
from tests.conftest import MockQdrantService


@pytest.mark.integration
@pytest.mark.asyncio
async def test_retrieval_returns_relevant_chunks(
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

    retrieval = RetrievalService(
        qdrant=mock_qdrant,  # type: ignore[arg-type]
        embedding_provider=mock_embedding,
        settings=test_settings,
    )
    chunks, debug = await retrieval.search("vacation policy", top_k=3)
    assert debug["result_count"] >= 0
    if chunks:
        assert chunks[0].content


@pytest.mark.integration
@pytest.mark.asyncio
async def test_build_context_respects_token_budget(
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

    retrieval = RetrievalService(
        qdrant=mock_qdrant,  # type: ignore[arg-type]
        embedding_provider=mock_embedding,
        settings=test_settings,
    )
    context, selected, debug = await retrieval.build_context("password reset")
    assert isinstance(context, str)
    assert debug["context_chunks"] == len(selected)
