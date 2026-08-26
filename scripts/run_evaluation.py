"""Run retrieval evaluation and optionally save results."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.api.deps import EvaluationSearchAdapter
from app.core.config import get_settings
from app.evaluation.datasets import ensure_default_dataset
from app.evaluation.runner import EvaluationRunner
from app.repositories.evaluation_repo import EvaluationRepository
from app.retrieval.service import RetrievalService


async def run_evaluation(
    *,
    dataset_name: str = "sample",
    top_k: int = 10,
    name: str | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    """Execute evaluation run and persist results."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from app.db.models import Base
    from app.retrieval.qdrant_client import QdrantService

    settings = get_settings()
    ensure_default_dataset(settings)

    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session = session_factory()
    try:
        qdrant = QdrantService(settings)
        retrieval = RetrievalService(qdrant=qdrant, settings=settings)
        adapter = EvaluationSearchAdapter(retrieval)
        repo = EvaluationRepository(session)
        runner = EvaluationRunner(repo, adapter, settings)

        run = await runner.run(dataset_name=dataset_name, name=name, top_k=top_k)
        await session.commit()

        result: dict[str, Any] = {
            "id": run.id,
            "name": run.name,
            "dataset_name": run.dataset_name,
            "status": run.status,
            "metrics": run.metrics or {},
            "config": run.config or {},
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        }

        if output_path is None:
            results_dir = settings.project_root / "evals" / "results"
            results_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
            output_path = results_dir / f"eval_{dataset_name}_{timestamp}.json"

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        result["output_path"] = str(output_path)
        return result
    finally:
        await session.close()
        await engine.dispose()


if __name__ == "__main__":
    import asyncio

    import typer

    def main(
        dataset: str = typer.Option("sample", "--dataset", "-d"),
        top_k: int = typer.Option(10, "--top-k", "-k"),
        output: Path | None = typer.Option(None, "--output", "-o"),
    ) -> None:
        result = asyncio.run(run_evaluation(dataset_name=dataset, top_k=top_k, output_path=output))
        print(json.dumps(result, indent=2))

    typer.run(main)
