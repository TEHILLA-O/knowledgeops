"""Knowledge gap repository."""

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.models import KnowledgeGap


class KnowledgeGapRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_gaps(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        cluster_id: str | None = None,
        min_frequency: int | None = None,
        search: str | None = None,
    ) -> tuple[list[KnowledgeGap], int]:
        stmt = select(KnowledgeGap)
        if status:
            stmt = stmt.where(KnowledgeGap.status == status)
        if cluster_id:
            stmt = stmt.where(KnowledgeGap.cluster_id == cluster_id)
        if min_frequency is not None:
            stmt = stmt.where(KnowledgeGap.frequency >= min_frequency)
        if search:
            pattern = f"%{search}%"
            stmt = stmt.where(KnowledgeGap.question.ilike(pattern))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.session.execute(count_stmt)).scalar_one()

        offset = (page - 1) * page_size
        stmt = stmt.order_by(KnowledgeGap.frequency.desc(), KnowledgeGap.last_seen_at.desc())
        stmt = stmt.offset(offset).limit(page_size)
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def get_by_id(self, gap_id: str) -> KnowledgeGap:
        stmt = select(KnowledgeGap).where(KnowledgeGap.id == gap_id)
        result = await self.session.execute(stmt)
        gap = result.scalar_one_or_none()
        if gap is None:
            raise NotFoundError(f"Knowledge gap {gap_id} not found")
        return gap

    async def find_by_normalized_question(self, normalized: str) -> KnowledgeGap | None:
        stmt = select(KnowledgeGap).where(KnowledgeGap.normalized_question == normalized)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_cluster_id(self, cluster_id: str) -> list[KnowledgeGap]:
        stmt = select(KnowledgeGap).where(KnowledgeGap.cluster_id == cluster_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_unresolved(self) -> list[KnowledgeGap]:
        stmt = select(KnowledgeGap).where(KnowledgeGap.status == "UNRESOLVED")
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, gap: KnowledgeGap) -> KnowledgeGap:
        self.session.add(gap)
        await self.session.flush()
        return gap

    async def update(self, gap: KnowledgeGap) -> KnowledgeGap:
        gap.last_seen_at = datetime.now(UTC)
        await self.session.flush()
        return gap

    async def count_unresolved(self) -> int:
        stmt = (
            select(func.count())
            .select_from(KnowledgeGap)
            .where(KnowledgeGap.status == "UNRESOLVED")
        )
        return (await self.session.execute(stmt)).scalar_one()
