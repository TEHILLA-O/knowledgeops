"""Ingestion routes."""

import math
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.api.deps import IngestionService, Repositories, get_ingestion_service, get_repositories
from app.db.models import IngestionRun
from app.schemas.common import IngestionRunSummary, PaginatedResponse

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


class IngestionRunRequest(BaseModel):
    source: str = Field(default="demo", min_length=1, max_length=128)


class IngestionRunDetail(IngestionRunSummary):
    documents_failed: int = 0
    chunks_indexed: int = 0
    chunks_removed: int = 0
    steps: list[dict[str, Any]] = Field(default_factory=list)
    errors: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


def _run_to_summary(run: IngestionRun) -> IngestionRunSummary:
    return IngestionRunSummary(
        id=run.id,
        status=run.status,
        source=run.source,
        documents_discovered=run.documents_discovered,
        documents_new=run.documents_new,
        documents_modified=run.documents_modified,
        documents_unchanged=run.documents_unchanged,
        documents_deleted=run.documents_deleted,
        chunks_indexed=run.chunks_indexed,
        health_status=run.health_status,
        started_at=run.started_at,
        completed_at=run.completed_at,
    )


@router.post("/run", response_model=IngestionRunSummary)
async def trigger_ingestion(
    body: IngestionRunRequest,
    service: IngestionService = Depends(get_ingestion_service),
) -> IngestionRunSummary:
    return await service.run(source=body.source)


@router.get("/runs", response_model=PaginatedResponse)
async def list_ingestion_runs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: str | None = None,
    source: str | None = None,
    repos: Repositories = Depends(get_repositories),
) -> PaginatedResponse:
    items, total = await repos.ingestion.list_runs(
        page=page, page_size=page_size, status=status, source=source
    )
    pages = math.ceil(total / page_size) if total else 0
    return PaginatedResponse(
        items=[_run_to_summary(r) for r in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/runs/{run_id}", response_model=IngestionRunDetail)
async def get_ingestion_run(
    run_id: str,
    repos: Repositories = Depends(get_repositories),
) -> IngestionRunDetail:
    run = await repos.ingestion.get_by_id(run_id)
    return IngestionRunDetail(
        **_run_to_summary(run).model_dump(),
        documents_failed=run.documents_failed,
        chunks_indexed=run.chunks_indexed,
        chunks_removed=run.chunks_removed,
        steps=[
            {
                "id": s.id,
                "step_name": s.step_name,
                "status": s.status,
                "duration_ms": s.duration_ms,
                "details": s.details,
                "created_at": s.created_at.isoformat(),
            }
            for s in run.steps
        ],
        errors=[
            {
                "id": e.id,
                "document_id": e.document_id,
                "error_type": e.error_type,
                "message": e.message,
                "created_at": e.created_at.isoformat(),
            }
            for e in run.errors
        ],
        metadata=run.metadata_json or {},
    )
