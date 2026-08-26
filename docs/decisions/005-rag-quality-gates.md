# ADR 005: RAG Quality Gates and Regression Testing

**Status:** Accepted  
**Date:** 2026-08-26

## Context

RAG systems degrade silently when chunking, retrieval, or embedding configuration changes. KnowledgeOps needs deterministic evaluation, baseline comparison, and CI-friendly quality gates that do not require paid LLM APIs.

The `main_eval` dataset contains **60 questions** spanning HR, IT, security, finance, procurement, operations, and engineering topics — including questions that should refuse (out-of-scope).

## Decision

Implement evaluation in `app/evaluation/`:

1. **Metrics** (`metrics.py`) — MRR, Hit Rate@k, Precision@k, Recall@k, NDCG@k
2. **Runner** (`runner.py`) — executes retrieval against dataset, persists results to PostgreSQL
3. **Regression** (`regression.py`) — compares candidate run against `evals/datasets/baseline_metrics.json` with configurable tolerance
4. **Quality gates** (`config/retrieval.yaml`):

```yaml
quality_gates:
  hit_rate_at_5_min: 0.6
  mrr_min: 0.5
  regression_tolerance: 0.05
```

Baseline metrics (measured):

| Metric | Baseline | Gate |
|---|---|---|
| MRR | 0.625 | ≥ 0.5 ✓ |
| Hit Rate @ 5 | 0.633 | ≥ 0.6 ✓ |
| Precision @ 5 | 0.573 | — |
| Recall @ 5 | 0.633 | — |
| NDCG @ 5 | 0.702 | — |

## Alternatives Considered

| Alternative | Why not chosen |
|---|---|
| **LLM-as-judge (RAGAS only)** | Non-deterministic; requires API keys; unsuitable for CI gating |
| **Manual spot-checking** | Does not scale; no regression detection |
| **Single accuracy number** | Hides retrieval rank quality; MRR and NDCG capture ranking |
| **No gates (metrics informational only)** | Allows silent regressions during refactors |

## Consequences

**Positive**

- Baseline file enables `compare_metrics()` before merge
- `enforce_quality_gates()` raises `QualityGateError` for programmatic CI integration
- Per-query metrics stored for failure analysis

**Negative**

- Retrieval-only evaluation does not measure answer correctness from generation
- Dataset maintenance burden — 60 questions must stay aligned with `demo_knowledge` content
- Tolerance of 0.05 may be too loose or tight depending on dataset size

**Follow-up**

- Add generation-quality evaluation with mock provider for deterministic answer matching
- Expand `per_query` entries in baseline file for targeted regression on failure categories
