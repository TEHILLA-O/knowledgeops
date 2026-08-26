"""Document repository."""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError
from app.db.models import Document, DocumentVersion


class DocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_documents(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        source: str | None = None,
        document_type: str | None = None,
        department: str | None = None,
        status: str | None = None,
        search: str | None = None,
        include_deleted: bool = False,
    ) -> tuple[list[Document], int]:
        stmt = select(Document)
        if not include_deleted:
            stmt = stmt.where(Document.is_deleted.is_(False))
        if source:
            stmt = stmt.where(Document.source == source)
        if document_type:
            stmt = stmt.where(Document.document_type == document_type)
        if department:
            stmt = stmt.where(Document.department == department)
        if status:
            stmt = stmt.where(Document.status == status)
        if search:
            pattern = f"%{search}%"
            stmt = stmt.where(
                Document.title.ilike(pattern) | Document.filename.ilike(pattern)
            )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.session.execute(count_stmt)).scalar_one()

        offset = (page - 1) * page_size
        stmt = stmt.order_by(Document.updated_at.desc()).offset(offset).limit(page_size)
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def get_by_id(self, document_id: str) -> Document:
        stmt = (
            select(Document)
            .where(Document.id == document_id)
            .options(selectinload(Document.versions), selectinload(Document.chunks))
        )
        result = await self.session.execute(stmt)
        document = result.scalar_one_or_none()
        if document is None:
            raise NotFoundError(f"Document {document_id} not found")
        return document

    async def get_versions(self, document_id: str) -> list[DocumentVersion]:
        await self.get_by_id(document_id)
        stmt = (
            select(DocumentVersion)
            .where(DocumentVersion.document_id == document_id)
            .order_by(DocumentVersion.version.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, document: Document) -> Document:
        self.session.add(document)
        await self.session.flush()
        return document

    async def update(self, document: Document) -> Document:
        await self.session.flush()
        return document

    async def count_indexed(self) -> int:
        stmt = select(func.count()).select_from(Document).where(
            Document.is_deleted.is_(False),
            Document.status == "INDEXED",
        )
        return (await self.session.execute(stmt)).scalar_one()

    async def count_chunks(self) -> int:
        from app.db.models import Chunk

        stmt = select(func.count()).select_from(Chunk).where(Chunk.is_active.is_(True))
        return (await self.session.execute(stmt)).scalar_one()

    async def get_last_indexed_at(self) -> datetime | None:
        stmt = select(func.max(Document.last_indexed_at)).where(Document.is_deleted.is_(False))
        return (await self.session.execute(stmt)).scalar_one_or_none()
