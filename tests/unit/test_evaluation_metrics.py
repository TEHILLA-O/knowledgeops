"""Tests for evaluation metrics."""

from app.evaluation.metrics import (
    aggregate_metrics,
    compute_query_metrics,
    hit_rate_at_k,
    reciprocal_rank,
)


def test_hit_rate_at_k() -> None:
    relevant = {"doc-a"}
    retrieved = ["doc-b", "doc-a", "doc-c"]
    assert hit_rate_at_k(relevant, retrieved, 1) == 0.0
    assert hit_rate_at_k(relevant, retrieved, 2) == 1.0


def test_reciprocal_rank() -> None:
    relevant = {"doc-a"}
    retrieved = ["doc-b", "doc-c", "doc-a"]
    assert reciprocal_rank(relevant, retrieved) == 1 / 3


def test_compute_query_metrics() -> None:
    metrics = compute_query_metrics({"doc-a"}, ["doc-a", "doc-b"], [1, 3, 5])
    assert "mrr" in metrics
    assert metrics["hit_rate_at_1"] == 1.0
    assert metrics["precision_at_3"] > 0


def test_aggregate_metrics() -> None:
    per_query = [
        {"mrr": 1.0, "hit_rate_at_5": 1.0},
        {"mrr": 0.5, "hit_rate_at_5": 0.0},
    ]
    agg = aggregate_metrics(per_query)
    assert agg["mrr"] == 0.75
    assert agg["hit_rate_at_5"] == 0.5
