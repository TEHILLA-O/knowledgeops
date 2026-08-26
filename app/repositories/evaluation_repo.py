"""Evaluation run repository."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError
from app.db.models import EvaluationResult, EvaluationRun


class EvaluationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_runs(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        dataset_name: str | None = None,
    ) -> tuple[list[EvaluationRun], int]:
        stmt = select(EvaluationRun)
        if status:
            stmt = stmt.where(EvaluationRun.status == status)
        if dataset_name:
            stmt = stmt.where(EvaluationRun.dataset_name == dataset_name)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.session.execute(count_stmt)).scalar_one()

        offset = (page - 1) * page_size
        stmt = stmt.order_by(EvaluationRun.started_at.desc()).offset(offset).limit(page_size)
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def get_by_id(self, run_id: str) -> EvaluationRun:
        stmt = (
            select(EvaluationRun)
            .where(EvaluationRun.id == run_id)
            .options(selectinload(EvaluationRun.results))
        )
        result = await self.session.execute(stmt)
        run = result.scalar_one_or_none()
        if run is None:
            raise NotFoundError(f"Evaluation run {run_id} not found")
        return run

    async def create_run(self, run: EvaluationRun) -> EvaluationRun:
        self.session.add(run)
        await self.session.flush()
        return run

    async def update_run(self, run: EvaluationRun) -> EvaluationRun:
        await self.session.flush()
        return run

    async def add_results(self, results: list[EvaluationResult]) -> list[EvaluationResult]:
        self.session.add_all(results)
        await self.session.flush()
        return results

    async def get_latest_completed(self) -> EvaluationRun | None:
        stmt = (
            select(EvaluationRun)
            .where(EvaluationRun.status == "COMPLETED")
            .order_by(EvaluationRun.completed_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_latest_score(self) -> float | None:
        run = await self.get_latest_completed()
        if run is None or not run.metrics:
            return None
        metrics = run.metrics
        for key in ("hit_rate_at_5", "mrr", "ndcg_at_5"):
            if key in metrics:
                return float(metrics[key])
        return None
