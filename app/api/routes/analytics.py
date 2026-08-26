"""Analytics routes."""

from fastapi import APIRouter, Depends

from app.api.deps import Repositories, get_repositories
from app.schemas.common import AnalyticsSummary

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary", response_model=AnalyticsSummary)
async def analytics_summary(
    repos: Repositories = Depends(get_repositories),
) -> AnalyticsSummary:
    docs = await repos.analytics.documents_indexed_count()
    chunks = await repos.analytics.chunks_indexed_count()
    queries_today = await repos.analytics.queries_today_count()
    breakdown = await repos.analytics.query_status_breakdown(days=1)
    total_today = sum(breakdown.values()) or 1
    answered = breakdown.get("ANSWERED", 0)
    insufficient = breakdown.get("INSUFFICIENT_EVIDENCE", 0)
    avg_latency = await repos.analytics.avg_retrieval_latency_ms(days=7)
    gaps = await repos.analytics.knowledge_gaps_count()
    latest_score = await repos.evaluations.get_latest_score()
    index_health = await repos.analytics.latest_ingestion_health()

    return AnalyticsSummary(
        documents_indexed=docs,
        chunks_indexed=chunks,
        queries_today=queries_today,
        answered_percentage=round(answered / total_today * 100, 2),
        insufficient_evidence_percentage=round(insufficient / total_today * 100, 2),
        average_retrieval_latency_ms=round(avg_latency, 2),
        knowledge_gaps_count=gaps,
        latest_evaluation_score=latest_score,
        index_health=index_health,
    )
