"""Ingestion run repository."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError
from app.db.models import IngestionError, IngestionRun, IngestionStep


class IngestionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_runs(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        source: str | None = None,
    ) -> tuple[list[IngestionRun], int]:
        stmt = select(IngestionRun)
        if status:
            stmt = stmt.where(IngestionRun.status == status)
        if source:
            stmt = stmt.where(IngestionRun.source == source)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.session.execute(count_stmt)).scalar_one()

        offset = (page - 1) * page_size
        stmt = stmt.order_by(IngestionRun.started_at.desc()).offset(offset).limit(page_size)
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def get_by_id(self, run_id: str) -> IngestionRun:
        stmt = (
            select(IngestionRun)
            .where(IngestionRun.id == run_id)
            .options(selectinload(IngestionRun.steps), selectinload(IngestionRun.errors))
        )
        result = await self.session.execute(stmt)
        run = result.scalar_one_or_none()
        if run is None:
            raise NotFoundError(f"Ingestion run {run_id} not found")
        return run

    async def create_run(self, run: IngestionRun) -> IngestionRun:
        self.session.add(run)
        await self.session.flush()
        return run

    async def update_run(self, run: IngestionRun) -> IngestionRun:
        await self.session.flush()
        return run

    async def add_step(self, step: IngestionStep) -> IngestionStep:
        self.session.add(step)
        await self.session.flush()
        return step

    async def add_error(self, error: IngestionError) -> IngestionError:
        self.session.add(error)
        await self.session.flush()
        return error

    async def get_latest_run(self) -> IngestionRun | None:
        stmt = select(IngestionRun).order_by(IngestionRun.started_at.desc()).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
