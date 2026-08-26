# ADR 002: Hybrid Dense + Sparse Retrieval

**Status:** Accepted  
**Date:** 2026-08-26

## Context

Enterprise knowledge bases contain both semantically similar content ("vacation carry-forward rules") and exact-match identifiers (policy numbers, acronyms, product codes, dates). Pure dense retrieval misses lexical signals; pure keyword search misses paraphrases.

Measured baseline on `main_eval` (60 questions) with hybrid retrieval enabled:

| Metric | Value |
|---|---|
| MRR | 0.625 |
| Hit Rate @ 5 | 0.633 |
| Precision @ 5 | 0.573 |
| Recall @ 5 | 0.633 |
| NDCG @ 5 | 0.702 |

## Decision

Implement **hybrid retrieval** in `app/retrieval/hybrid.py`:

1. **Dense retrieval** — Qdrant cosine search over `sentence-transformers/all-MiniLM-L6-v2` embeddings (`dense_top_k: 20`)
2. **Sparse retrieval** — in-process BM25 over indexed chunk text (`sparse_top_k: 20`)
3. **Score fusion** — min-max normalisation of dense and sparse scores, blended with configurable `hybrid_alpha` (default **0.5**)
4. **Reranking** — cross-encoder reranker on fused candidates (`rerank_top_k: 8`, `context_top_k: 5`)

Configuration lives in `config/retrieval.yaml` and is hot-readable via `Settings.retrieval_config`.

## Alternatives Considered

| Alternative | Why not chosen |
|---|---|
| **Dense-only** | Underperforms on policy numbers and exact terminology present in eval set |
| **Elasticsearch BM25 + vectors** | Additional infrastructure; BM25 in Python sufficient at demo scale |
| **Reciprocal Rank Fusion (RRF)** | Valid alternative; min-max weighted fusion chosen for interpretable `alpha` tuning |
| **Qdrant sparse vectors** | Deferred; in-process BM25 avoids dual-index maintenance in v1 |

## Consequences

**Positive**

- Handles both semantic and lexical query patterns in a single pipeline
- `hybrid_alpha` provides an explicit tuning knob for evaluation experiments
- Retrieval debug output exposes dense, sparse, fusion, and rerank scores for observability

**Negative**

- Hybrid retrieval mean latency measured at **1099 ms** (3-iteration benchmark) — dominated by embedding + reranking on CPU
- BM25 index rebuilt from Qdrant payloads; not optimised for very large corpora
- Fusion normalisation can compress score dynamic range when candidate sets are small

**Follow-up**

- Experiment with RRF and learned fusion weights on `main_eval`
- Profile reranker latency; consider GPU or provider-based reranking for production
