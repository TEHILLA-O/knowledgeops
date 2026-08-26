"""Evaluation module."""

from app.evaluation.datasets import EvalDataset, EvalQuestion, list_datasets, load_dataset
from app.evaluation.metrics import (
    aggregate_metrics,
    compute_query_metrics,
    dcg_at_k,
    hit_rate_at_k,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)
from app.evaluation.regression import RegressionReport, compare_metrics, enforce_quality_gates
from app.evaluation.runner import EvaluationRunner

__all__ = [
    "EvalDataset",
    "EvalQuestion",
    "EvaluationRunner",
    "RegressionReport",
    "aggregate_metrics",
    "compare_metrics",
    "compute_query_metrics",
    "dcg_at_k",
    "enforce_quality_gates",
    "hit_rate_at_k",
    "list_datasets",
    "load_dataset",
    "ndcg_at_k",
    "precision_at_k",
    "recall_at_k",
    "reciprocal_rank",
]
