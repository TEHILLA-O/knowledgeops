"""E2E test for document deletion synchronization."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Document
from app.ingestion.discovery.local_folder import LocalFolderSource
from app.ingestion.pipeline import IngestionPipeline
from app.providers.mock_embedding import MockEmbeddingProvider
from tests.conftest import MockQdrantService


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_deletion_removes_document_from_index(
    db_session: AsyncSession,
    test_settings,
    mock_qdrant: MockQdrantService,
    mock_embedding: MockEmbeddingProvider,
    tmp_path,
) -> None:
    demo_path = tmp_path / "deletion_demo"
    demo_path.mkdir(exist_ok=True)
    keep_doc = demo_path / "keep.md"
    delete_doc = demo_path / "remove.md"
    keep_doc.write_text("# Keep\n\nThis document stays.\n", encoding="utf-8")
    delete_doc.write_text("# Remove\n\nThis document will be deleted.\n", encoding="utf-8")

    source = LocalFolderSource(folder_path=demo_path, source_name="demo", settings=test_settings)
    pipeline = IngestionPipeline(
        db_session,
        mock_qdrant,  # type: ignore[arg-type]
        mock_embedding,
        settings=test_settings,
    )

    await pipeline.run(source)
    await db_session.commit()
    points_before_delete = await mock_qdrant.count_points()

    delete_doc.unlink()
    summary = await pipeline.run(source)
    await db_session.commit()

    assert summary.documents_deleted == 1
    assert await mock_qdrant.count_points() < points_before_delete

    result = await db_session.execute(select(Document).where(Document.is_deleted.is_(True)))
    deleted_docs = list(result.scalars().all())
    assert len(deleted_docs) == 1
