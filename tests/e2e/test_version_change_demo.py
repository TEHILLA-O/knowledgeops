"""E2E test for document version change detection and re-indexing."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.discovery.local_folder import LocalFolderSource
from app.ingestion.pipeline import IngestionPipeline
from app.providers.mock_embedding import MockEmbeddingProvider
from tests.conftest import MockQdrantService


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_version_change_reindexes_only_modified_document(
    db_session: AsyncSession,
    test_settings,
    mock_qdrant: MockQdrantService,
    mock_embedding: MockEmbeddingProvider,
    tmp_path,
) -> None:
    demo_path = tmp_path / "version_demo"
    demo_path.mkdir(exist_ok=True)
    doc_a = demo_path / "policy-a.md"
    doc_b = demo_path / "policy-b.md"
    doc_a.write_text("# Policy A\n\nOriginal content for policy A.\n", encoding="utf-8")
    doc_b.write_text("# Policy B\n\nStable content for policy B.\n", encoding="utf-8")

    test_settings.demo_knowledge_path = str(demo_path)
    source = LocalFolderSource(folder_path=demo_path, source_name="demo", settings=test_settings)
    pipeline = IngestionPipeline(
        db_session,
        mock_qdrant,  # type: ignore[arg-type]
        mock_embedding,
        settings=test_settings,
    )

    summary1 = await pipeline.run(source)
    await db_session.commit()
    initial_points = await mock_qdrant.count_points()

    doc_a.write_text(
        "# Policy A\n\nUpdated content for policy A with new vacation rules.\n",
        encoding="utf-8",
    )
    summary2 = await pipeline.run(source)
    await db_session.commit()

    assert summary1.documents_new == 2
    assert summary2.documents_modified == 1
    assert summary2.documents_unchanged == 1
    assert await mock_qdrant.count_points() >= initial_points
