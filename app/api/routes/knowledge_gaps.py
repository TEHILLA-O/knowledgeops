"""Knowledge gap routes."""

import math
from typing import Any

from fastapi import APIRouter, Depends, Query

from app.api.deps import Repositories, get_repositories
from app.db.models import KnowledgeGap
from app.schemas.common import KnowledgeGapSummary, PaginatedResponse

router = APIRouter(prefix="/knowledge-gaps", tags=["knowledge-gaps"])


class KnowledgeGapDetail(KnowledgeGapSummary):
    normalized_question: str | None = None
    cluster_id: str | None = None
    metadata: dict[str, Any] = {}
    first_seen_at: str | None = None


def _gap_to_summary(gap: KnowledgeGap) -> KnowledgeGapSummary:
    return KnowledgeGapSummary(
        id=gap.id,
        question=gap.question,
        frequency=gap.frequency,
        best_retrieval_score=gap.best_retrieval_score,
        suggested_topic=gap.suggested_topic,
        status=gap.status,
        last_seen_at=gap.last_seen_at,
    )


@router.get("", response_model=PaginatedResponse)
@router.get("/", response_model=PaginatedResponse, include_in_schema=False)
async def list_knowledge_gaps(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: str | None = None,
    cluster_id: str | None = None,
    min_frequency: int | None = None,
    search: str | None = None,
    repos: Repositories = Depends(get_repositories),
) -> PaginatedResponse:
    items, total = await repos.knowledge_gaps.list_gaps(
        page=page,
        page_size=page_size,
        status=status,
        cluster_id=cluster_id,
        min_frequency=min_frequency,
        search=search,
    )
    pages = math.ceil(total / page_size) if total else 0
    return PaginatedResponse(
        items=[_gap_to_summary(g) for g in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/{gap_id}", response_model=KnowledgeGapDetail)
async def get_knowledge_gap(
    gap_id: str,
    repos: Repositories = Depends(get_repositories),
) -> KnowledgeGapDetail:
    gap = await repos.knowledge_gaps.get_by_id(gap_id)
    return KnowledgeGapDetail(
        **_gap_to_summary(gap).model_dump(),
        normalized_question=gap.normalized_question,
        cluster_id=gap.cluster_id,
        metadata=gap.metadata_json or {},
        first_seen_at=gap.first_seen_at.isoformat() if gap.first_seen_at else None,
    )
