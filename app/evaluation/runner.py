"""Evaluation runner against retrieval pipeline."""

from datetime import UTC, datetime
from typing import Any, Protocol

from app.core.config import Settings
from app.db.models import EvaluationResult, EvaluationRun, generate_uuid
from app.evaluation.datasets import load_dataset
from app.evaluation.metrics import aggregate_metrics, compute_query_metrics
from app.repositories.evaluation_repo import EvaluationRepository


class RetrievalPipeline(Protocol):
    async def search(
        self,
        query: str,
        *,
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]: ...


def _normalize_doc_key(value: str) -> str:
    return value.lower().replace("_", "-").replace(" ", "-").strip()


def _retrieved_doc_keys(result: dict[str, Any]) -> list[str]:
    """Build match keys from retrieved chunk metadata."""
    keys: list[str] = []
    metadata = result.get("metadata") or {}
    for field in ("filename", "document_stable_id", "source", "department"):
        value = metadata.get(field)
        if value:
            keys.append(_normalize_doc_key(str(value)))
    title = result.get("document_title")
    if title:
        keys.append(_normalize_doc_key(str(title)))
    doc_id = result.get("document_id")
    if doc_id:
        keys.append(_normalize_doc_key(str(doc_id)))
    return keys


def _is_relevant(expected: str, retrieved: dict[str, Any]) -> bool:
    needle = _normalize_doc_key(expected)
    return any(needle in key or key in needle for key in _retrieved_doc_keys(retrieved) if key)


def _retrieved_labels(results: list[dict[str, Any]]) -> list[str]:
    labels: list[str] = []
    for result in results:
        metadata = result.get("metadata") or {}
        label = str(metadata.get("filename") or result.get("document_title") or result.get("document_id") or "")
        labels.append(label)
    return labels


def _compute_fuzzy_metrics(
    expected_documents: list[str],
    retrieved: list[dict[str, Any]],
    k_values: list[int],
) -> dict[str, float]:
    """Compute retrieval metrics using substring document matching."""
    per_k_hits: dict[int, float] = {}
    per_k_precision: dict[int, float] = {}
    per_k_recall: dict[int, float] = {}
    per_k_ndcg: dict[int, float] = {}
    mrr = 0.0

    for rank, item in enumerate(retrieved, start=1):
        if any(_is_relevant(expected, item) for expected in expected_documents):
            if mrr == 0.0:
                mrr = 1.0 / rank
            break

    for k in k_values:
        top = retrieved[:k]
        hits = sum(
            1
            for item in top
            if any(_is_relevant(expected, item) for expected in expected_documents)
        )
        per_k_hits[k] = 1.0 if hits > 0 else 0.0
        per_k_precision[k] = hits / len(top) if top else 0.0
        per_k_recall[k] = min(1.0, hits / max(len(expected_documents), 1))
        dcg = 0.0
        for index, item in enumerate(top):
            if any(_is_relevant(expected, item) for expected in expected_documents):
                dcg += 1.0 / (index + 2)
        ideal = 1.0
        per_k_ndcg[k] = dcg / ideal if ideal else 0.0

    metrics: dict[str, float] = {"mrr": mrr}
    for k in k_values:
        metrics[f"hit_rate_at_{k}"] = per_k_hits[k]
        metrics[f"precision_at_{k}"] = per_k_precision[k]
        metrics[f"recall_at_{k}"] = per_k_recall[k]
        metrics[f"ndcg_at_{k}"] = per_k_ndcg[k]
    return metrics


class EvaluationRunner:
    def __init__(
        self,
        repo: EvaluationRepository,
        pipeline: RetrievalPipeline,
        settings: Settings,
    ) -> None:
        self.repo = repo
        self.pipeline = pipeline
        self.settings = settings

    async def run(
        self,
        *,
        dataset_name: str,
        name: str | None = None,
        top_k: int = 10,
        index_version_id: str | None = None,
    ) -> EvaluationRun:
        dataset = load_dataset(dataset_name, self.settings)
        run = EvaluationRun(
            id=generate_uuid(),
            name=name or f"eval-{dataset_name}-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
            dataset_name=dataset.name,
            index_version_id=index_version_id,
            status="RUNNING",
            config={"top_k": top_k, "k_values": dataset.k_values},
            metrics={},
        )
        await self.repo.create_run(run)

        per_query_metrics: list[dict[str, float]] = []
        results: list[EvaluationResult] = []

        for question in dataset.questions:
            retrieved = await self.pipeline.search(question.question, top_k=top_k)
            retrieved_docs = _retrieved_labels(retrieved)
            q_metrics = _compute_fuzzy_metrics(
                question.expected_documents,
                retrieved,
                dataset.k_values,
            )
            per_query_metrics.append(q_metrics)

            passed = q_metrics.get("hit_rate_at_5", q_metrics.get("hit_rate_at_3", 0.0)) >= 0.5
            results.append(
                EvaluationResult(
                    id=generate_uuid(),
                    evaluation_run_id=run.id,
                    question=question.question,
                    expected_document=(
                        question.expected_documents[0] if question.expected_documents else None
                    ),
                    retrieved_documents=retrieved_docs,
                    metrics=q_metrics,
                    passed=passed,
                )
            )

        run.metrics = aggregate_metrics(per_query_metrics)
        run.status = "COMPLETED"
        run.completed_at = datetime.now(UTC)
        await self.repo.add_results(results)
        await self.repo.update_run(run)
        return run
