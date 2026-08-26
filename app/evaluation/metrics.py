"""Deterministic retrieval evaluation metrics."""

import math
from collections.abc import Sequence


def hit_rate_at_k(relevant: set[str], retrieved: Sequence[str], k: int) -> float:
    """Fraction of queries with at least one relevant doc in top-k."""
    if not retrieved:
        return 0.0
    top_k = retrieved[:k]
    return 1.0 if any(doc in relevant for doc in top_k) else 0.0


def reciprocal_rank(relevant: set[str], retrieved: Sequence[str]) -> float:
    """Reciprocal rank of first relevant document."""
    for rank, doc in enumerate(retrieved, start=1):
        if doc in relevant:
            return 1.0 / rank
    return 0.0


def precision_at_k(relevant: set[str], retrieved: Sequence[str], k: int) -> float:
    """Precision at k."""
    if k <= 0:
        return 0.0
    top_k = retrieved[:k]
    if not top_k:
        return 0.0
    hits = sum(1 for doc in top_k if doc in relevant)
    return hits / len(top_k)


def recall_at_k(relevant: set[str], retrieved: Sequence[str], k: int) -> float:
    """Recall at k."""
    if not relevant:
        return 0.0
    top_k = retrieved[:k]
    hits = sum(1 for doc in top_k if doc in relevant)
    return hits / len(relevant)


def dcg_at_k(relevant: set[str], retrieved: Sequence[str], k: int) -> float:
    """Discounted cumulative gain at k."""
    dcg = 0.0
    for i, doc in enumerate(retrieved[:k]):
        if doc in relevant:
            dcg += 1.0 / math.log2(i + 2)
    return dcg


def ndcg_at_k(relevant: set[str], retrieved: Sequence[str], k: int) -> float:
    """Normalized DCG at k."""
    ideal = dcg_at_k(relevant, list(relevant), min(k, len(relevant)))
    if ideal == 0.0:
        return 0.0
    return dcg_at_k(relevant, retrieved, k) / ideal


def compute_query_metrics(
    relevant: set[str],
    retrieved: Sequence[str],
    k_values: Sequence[int] | None = None,
) -> dict[str, float]:
    """Compute all metrics for a single query."""
    k_values = k_values or [1, 3, 5, 10]
    metrics: dict[str, float] = {"mrr": reciprocal_rank(relevant, retrieved)}
    for k in k_values:
        metrics[f"hit_rate_at_{k}"] = hit_rate_at_k(relevant, retrieved, k)
        metrics[f"precision_at_{k}"] = precision_at_k(relevant, retrieved, k)
        metrics[f"recall_at_{k}"] = recall_at_k(relevant, retrieved, k)
        metrics[f"ndcg_at_{k}"] = ndcg_at_k(relevant, retrieved, k)
    return metrics


def aggregate_metrics(per_query: list[dict[str, float]]) -> dict[str, float]:
    """Average metrics across queries."""
    if not per_query:
        return {}
    keys = per_query[0].keys()
    return {key: sum(q[key] for q in per_query) / len(per_query) for key in keys}
