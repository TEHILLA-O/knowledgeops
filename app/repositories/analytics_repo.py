"""Analytics aggregation repository."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Chunk, Document, IngestionRun, KnowledgeGap, QueryRecord
from app.schemas.common import AnalyticsSummary


class AnalyticsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def documents_indexed_count(self) -> int:
        stmt = select(func.count()).select_from(Document).where(
            Document.is_deleted.is_(False),
            Document.status == "INDEXED",
        )
        return (await self.session.execute(stmt)).scalar_one()

    async def chunks_indexed_count(self) -> int:
        stmt = select(func.count()).select_from(Chunk).where(Chunk.is_active.is_(True))
        return (await self.session.execute(stmt)).scalar_one()

    async def queries_today_count(self) -> int:
        today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        stmt = select(func.count()).select_from(QueryRecord).where(QueryRecord.created_at >= today)
        return (await self.session.execute(stmt)).scalar_one()

    async def query_status_breakdown(self, days: int = 7) -> dict[str, int]:
        since = datetime.now(UTC) - timedelta(days=days)
        stmt = (
            select(QueryRecord.status, func.count())
            .where(QueryRecord.created_at >= since)
            .group_by(QueryRecord.status)
        )
        result = await self.session.execute(stmt)
        return {row[0]: row[1] for row in result.all()}

    async def avg_retrieval_latency_ms(self, days: int = 7) -> float:
        since = datetime.now(UTC) - timedelta(days=days)
        stmt = select(func.avg(QueryRecord.retrieval_latency_ms)).where(
            QueryRecord.created_at >= since,
            QueryRecord.retrieval_latency_ms.is_not(None),
        )
        result = (await self.session.execute(stmt)).scalar_one_or_none()
        return float(result or 0.0)

    async def knowledge_gaps_count(self) -> int:
        stmt = (
            select(func.count())
            .select_from(KnowledgeGap)
            .where(KnowledgeGap.status == "UNRESOLVED")
        )
        return (await self.session.execute(stmt)).scalar_one()

    async def latest_ingestion_health(self) -> str | None:
        stmt = (
            select(IngestionRun.health_status)
            .order_by(IngestionRun.started_at.desc())
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_summary(self) -> AnalyticsSummary:
        breakdown = await self.query_status_breakdown(days=1)
        total_today = sum(breakdown.values()) or 1
        answered = breakdown.get("ANSWERED", 0)
        insufficient = breakdown.get("INSUFFICIENT_EVIDENCE", 0)
        return AnalyticsSummary(
            documents_indexed=await self.documents_indexed_count(),
            chunks_indexed=await self.chunks_indexed_count(),
            queries_today=await self.queries_today_count(),
            answered_percentage=round(answered / total_today * 100, 2),
            insufficient_evidence_percentage=round(insufficient / total_today * 100, 2),
            average_retrieval_latency_ms=round(await self.avg_retrieval_latency_ms(days=7), 2),
            knowledge_gaps_count=await self.knowledge_gaps_count(),
            latest_evaluation_score=None,
            index_health=await self.latest_ingestion_health(),
        )

    async def query_volume_by_day(self, days: int = 14) -> list[dict[str, object]]:
        since = datetime.now(UTC) - timedelta(days=days)
        day_expr = func.date_trunc("day", QueryRecord.created_at)
        stmt = (
            select(day_expr.label("day"), func.count().label("count"))
            .where(QueryRecord.created_at >= since)
            .group_by(day_expr)
            .order_by(day_expr)
        )
        result = await self.session.execute(stmt)
        return [{"day": row.day, "count": row.count} for row in result.all()]
