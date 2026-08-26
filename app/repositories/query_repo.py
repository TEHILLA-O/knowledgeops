"""Query record repository."""

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError
from app.db.models import Answer, Citation, QueryRecord, QueryRetrieval


class QueryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_queries(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        since: datetime | None = None,
    ) -> tuple[list[QueryRecord], int]:
        stmt = select(QueryRecord).options(
            selectinload(QueryRecord.answer).selectinload(Answer.citations),
            selectinload(QueryRecord.retrievals),
        )
        if status:
            stmt = stmt.where(QueryRecord.status == status)
        if since:
            stmt = stmt.where(QueryRecord.created_at >= since)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.session.execute(count_stmt)).scalar_one()

        offset = (page - 1) * page_size
        stmt = stmt.order_by(QueryRecord.created_at.desc()).offset(offset).limit(page_size)
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def get_by_id(self, query_id: str) -> QueryRecord:
        stmt = (
            select(QueryRecord)
            .where(QueryRecord.id == query_id)
            .options(
                selectinload(QueryRecord.answer).selectinload(Answer.citations),
                selectinload(QueryRecord.retrievals),
            )
        )
        result = await self.session.execute(stmt)
        record = result.scalar_one_or_none()
        if record is None:
            raise NotFoundError(f"Query {query_id} not found")
        return record

    async def create_query(self, record: QueryRecord) -> QueryRecord:
        self.session.add(record)
        await self.session.flush()
        return record

    async def add_retrievals(self, retrievals: list[QueryRetrieval]) -> list[QueryRetrieval]:
        self.session.add_all(retrievals)
        await self.session.flush()
        return retrievals

    async def save_answer(
        self,
        answer: Answer,
        citations: list[Citation] | None = None,
    ) -> Answer:
        self.session.add(answer)
        if citations:
            self.session.add_all(citations)
        await self.session.flush()
        return answer

    async def count_queries_since(self, since: datetime) -> int:
        stmt = select(func.count()).select_from(QueryRecord).where(QueryRecord.created_at >= since)
        return (await self.session.execute(stmt)).scalar_one()

    async def count_by_status_since(self, status: str, since: datetime) -> int:
        stmt = (
            select(func.count())
            .select_from(QueryRecord)
            .where(QueryRecord.status == status, QueryRecord.created_at >= since)
        )
        return (await self.session.execute(stmt)).scalar_one()

    async def avg_retrieval_latency_since(self, since: datetime) -> float:
        stmt = select(func.avg(QueryRecord.retrieval_latency_ms)).where(
            QueryRecord.created_at >= since,
            QueryRecord.retrieval_latency_ms.is_not(None),
        )
        result = (await self.session.execute(stmt)).scalar_one_or_none()
        return float(result or 0.0)

    @staticmethod
    def start_of_today() -> datetime:
        now = datetime.now(UTC)
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
