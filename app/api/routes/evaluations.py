"""Evaluation routes."""

import math
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.api.deps import Repositories, get_evaluation_runner, get_repositories
from app.db.models import EvaluationRun
from app.evaluation.runner import EvaluationRunner
from app.evaluation.datasets import ensure_default_dataset, list_datasets

router = APIRouter(prefix="/evaluations", tags=["evaluations"])


class EvaluationRunRequest(BaseModel):
    dataset_name: str = Field(default="sample", min_length=1)
    name: str | None = None
    top_k: int = Field(default=10, ge=1, le=50)
    index_version_id: str | None = None


class EvaluationRunResponse(BaseModel):
    id: str
    name: str
    dataset_name: str
    status: str
    metrics: dict[str, Any] = Field(default_factory=dict)
    config: dict[str, Any] = Field(default_factory=dict)
    started_at: str
    completed_at: str | None = None


class PaginatedEvaluations(BaseModel):
    items: list[EvaluationRunResponse]
    total: int
    page: int
    page_size: int
    pages: int


def _run_to_response(run: EvaluationRun) -> EvaluationRunResponse:
    return EvaluationRunResponse(
        id=run.id,
        name=run.name,
        dataset_name=run.dataset_name,
        status=run.status,
        metrics=run.metrics or {},
        config=run.config or {},
        started_at=run.started_at.isoformat(),
        completed_at=run.completed_at.isoformat() if run.completed_at else None,
    )


@router.post("/run", response_model=EvaluationRunResponse)
async def run_evaluation(
    body: EvaluationRunRequest,
    runner: EvaluationRunner = Depends(get_evaluation_runner),
) -> EvaluationRunResponse:
    ensure_default_dataset()
    run = await runner.run(
        dataset_name=body.dataset_name,
        name=body.name,
        top_k=body.top_k,
        index_version_id=body.index_version_id,
    )
    return _run_to_response(run)


@router.get("", response_model=PaginatedEvaluations)
@router.get("/", response_model=PaginatedEvaluations, include_in_schema=False)
async def list_evaluations(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: str | None = None,
    dataset_name: str | None = None,
    repos: Repositories = Depends(get_repositories),
) -> PaginatedEvaluations:
    items, total = await repos.evaluations.list_runs(
        page=page, page_size=page_size, status=status, dataset_name=dataset_name
    )
    pages = math.ceil(total / page_size) if total else 0
    return PaginatedEvaluations(
        items=[_run_to_response(r) for r in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/datasets", response_model=list[str])
async def get_available_datasets() -> list[str]:
    ensure_default_dataset()
    return list_datasets()
