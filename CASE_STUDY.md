# KnowledgeOps RAG Automation Platform

## Executive Summary

KnowledgeOps is a self-maintaining retrieval-augmented generation (RAG) platform designed to automate the full lifecycle of an internal knowledge base — from document discovery and incremental indexing through hybrid retrieval, grounded answer generation, and systematic tracking of unanswered questions.

Unlike a basic "upload a PDF and chat" tutorial, KnowledgeOps demonstrates production-oriented engineering: content-hash change detection, document versioning, permission-aware retrieval, deterministic evaluation with regression baselines, and knowledge-gap automation that turns failed searches into actionable intelligence.

This case study documents the engineering approach, measured results, and tradeoffs. All metrics below are from actual runs against the included `demo_knowledge` corpus and `main_eval` evaluation dataset.

---

## Business Problem

Organisations accumulate knowledge across HR policies, IT runbooks, security manuals, finance procedures, and engineering guidelines. Employees ask repetitive questions; answers are buried in documents that change frequently.

Traditional approaches fail in predictable ways:

- **Static chatbots** go stale when documents update
- **Manual RAG pipelines** re-embed everything on every run, wasting compute
- **Ungoverned retrieval** leaks restricted content across departments
- **No feedback loop** — failed searches disappear instead of driving content improvements

KnowledgeOps addresses these gaps with an automated knowledge lifecycle.

---

## Engineering Objectives

1. Incremental ingestion with change detection (no unnecessary re-embedding)
2. Hybrid retrieval combining semantic and lexical search
3. Grounded generation with citations and transparent confidence
4. Knowledge-gap detection for unanswered questions
5. Deterministic evaluation with quality gates and regression baselines
6. Permission filtering before context reaches the LLM
7. Runnable locally via Docker without paid API keys

---

## Architecture

The platform follows a layered architecture:

- **Ingestion layer** — discover, parse, clean, chunk, embed, index
- **Storage layer** — PostgreSQL (metadata, versions, audit) + Qdrant (vectors)
- **Retrieval layer** — dense + BM25 hybrid, reranking, permission filter
- **Generation layer** — grounded answers, citations, confidence scoring
- **Intelligence layer** — knowledge gaps, evaluation, analytics

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed Mermaid diagrams.

---

## Automated Ingestion

Documents are discovered from configurable sources (`DemoSource`, `LocalFolderSource`, `WebPageSource`). Each document receives a stable identifier and content hash.

**Measured results:**

| Metric | Value |
|---|---|
| Documents discovered | 40 |
| Chunks indexed (first run) | 662 |
| Documents unchanged (second run) | 40 |
| Chunks re-indexed (second run) | 0 |
| Unchanged ingestion latency | 0.234 s mean |

The zero re-index on the second run validates that content-hash change detection works as designed.

---

## Document Change Detection

Every ingestion run classifies documents as NEW, UNCHANGED, MODIFIED, or DELETED:

- **UNCHANGED** — skip parsing, chunking, and embedding entirely
- **MODIFIED** — re-chunk and re-embed only affected content; increment version
- **DELETED** — remove Qdrant vectors; retain audit trail in PostgreSQL

The case-study demo modifies `hr/leave-policy.md` (sick leave 10 → 12 days), re-runs ingestion, and confirms only the changed document is re-processed.

---

## Chunking Strategy

Default strategy: **sentence-aware chunking** with heading preservation.

| Parameter | Value |
|---|---|
| Chunk size | 512 tokens |
| Overlap | 64 tokens |
| Min length | 100 characters |
| Max length | 1024 characters |

Alternative strategies (fixed token, section-aware) are available for evaluation experiments. Metadata (section, page, version) survives chunking and is attached to every Qdrant payload.

662 chunks from 40 documents averages ~16.5 chunks per document — appropriate for policy-length markdown files.

---

## Embedding Strategy

- **Model:** `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions)
- **Provider:** Local `sentence-transformers` (no API cost)
- **Batch size:** 32 chunks per batch
- **Cache key:** chunk content hash — unchanged chunks skip re-embedding

Embedding batch benchmark: **0.027 s** mean for a 3-text batch (3 iterations).

---

## Hybrid Retrieval

Pure vector search misses exact policy numbers and acronyms. Pure keyword search misses paraphrases. KnowledgeOps fuses both:

1. Dense cosine search in Qdrant (top 20)
2. BM25 sparse search in-process (top 20)
3. Min-max score normalisation with `alpha = 0.5`
4. Cross-encoder reranking (top 8 → context top 5)

Hybrid retrieval latency: **1099 ms** mean. This is the primary latency contributor and reflects CPU-bound local inference.

---

## Reranking

A local cross-encoder reranker re-scores fused candidates. Both retrieval and rerank scores are stored on each `RetrievedChunk` for debug visibility. Reranking improves precision at the cost of latency — an expected tradeoff documented in the benchmark results.

---

## Context Construction

The context builder (`app/retrieval/context_builder.py`) does not blindly pass all retrieved chunks to the LLM:

- Removes duplicate chunks
- Respects `max_context_tokens` (4000)
- Prioritises reranker scores
- Enforces source diversity
- Preserves citation metadata

---

## Grounded Generation

The system prompt enforces a core rule: if evidence does not support an answer, the model must refuse. The default mock provider returns structured responses with `knowledge_gap` flags for insufficient evidence.

Generation providers are abstracted — swap to Ollama or commercial APIs via environment configuration.

---

## Citation System

Every grounded answer includes citations with:

- Document ID and title
- Section and page (when available)
- Document version
- Chunk ID

Citations are constructed from retrieved chunks, not freely generated by the model.

---

## Confidence Model

Confidence is derived from measurable signals, not LLM self-assessment:

| Signal | Weight |
|---|---|
| Retrieval strength | 35% |
| Reranker score | 35% |
| Grounding overlap | 20% |
| Agreement | 10% |

Levels: HIGH (≥ 0.75), MEDIUM (≥ 0.50), LOW, INSUFFICIENT_EVIDENCE (< 0.35).

When confidence is insufficient, the system refuses and creates a knowledge-gap record.

---

## Hallucination Reduction

Multiple layers reduce hallucination risk:

1. **Retrieval-first** — answers must be supported by retrieved chunks
2. **Grounding check** — token overlap between answer and evidence
3. **Confidence gating** — refuse below threshold
4. **Citation enforcement** — sources traceable to indexed content
5. **Knowledge-gap path** — explicit "insufficient evidence" instead of guessing

---

## Knowledge Gap Detection

When retrieval confidence is low, no useful chunks are found, or the generator reports insufficient evidence, KnowledgeOps creates a knowledge-gap record containing:

- The question text
- Timestamp and frequency count
- Best retrieval score achieved
- Status (UNRESOLVED by default)

The demo asks "What is the company's policy on Mars colonization subsidies?" — the system correctly refuses and records a gap. This transforms failed searches into content-creation priorities.

---

## RAG Evaluation

Evaluation uses the `main_eval` dataset with **60 questions** across HR, IT, security, finance, procurement, operations, and engineering.

| Metric | Value |
|---|---|
| MRR | 0.625 |
| Hit Rate @ 5 | 0.633 |
| Precision @ 5 | 0.573 |
| Recall @ 5 | 0.633 |
| NDCG @ 5 | 0.702 |

Both configured quality gates pass: Hit Rate @ 5 ≥ 0.6 and MRR ≥ 0.5.

---

## Regression Testing

Baseline metrics are stored in `evals/datasets/baseline_metrics.json`. The regression module (`app/evaluation/regression.py`) compares new evaluation runs against the baseline with a tolerance of 0.05. This enables CI integration to catch retrieval regressions before merge.

---

## Access Control

Permission filtering uses `metadata.allowed_groups` on chunks. The `PermissionFilter` removes restricted content before it reaches the generation provider.

Demo verification: ENGINEERING users see public chunks only; FINANCE users additionally see finance-restricted content. Production deployments should integrate with an identity provider and push filters to Qdrant query time.

---

## Observability

Structured logging via `structlog` covers:

- Ingestion step timing and document status transitions
- Retrieval scores (dense, sparse, fusion, rerank)
- Permission filter events
- Knowledge-gap creation
- Query latency

The dashboard at `/dashboard` provides document browsing, version history, and retrieval debug views.

---

## Failure Recovery

- **Ingestion errors** are recorded per-document in `IngestionError` without aborting the full run
- **Prefect tasks** retry discovery (2×) and pipeline execution (1×)
- **Qdrant collection** is auto-created on startup if missing
- **PostgreSQL** health check gates application startup in Docker Compose

---

## Testing Strategy

| Layer | Focus |
|---|---|
| Unit | Parsers, chunking, metrics, permissions, confidence |
| Integration | Ingestion pipeline, retrieval, evaluation runner |
| E2E | API endpoints, full query flow |

**Results:** 49 tests passed, 72% code coverage.

---

## Performance

Benchmark (3 iterations):

| Stage | Mean |
|---|---|
| Ingestion (unchanged) | 0.234 s |
| Embedding batch | 0.027 s |
| Hybrid retrieval | 1099 ms |
| Full query | 1599 ms |

Retrieval dominates query latency. GPU acceleration or provider-based embedding/reranking would be the first production optimisation.

---

## Engineering Tradeoffs

| Decision | Benefit | Cost |
|---|---|---|
| Qdrant + PostgreSQL | Clean separation of vector and relational data | Dual-store consistency |
| In-process BM25 | No extra search infrastructure | Does not scale to millions of chunks |
| Local embeddings | Zero API cost, offline capable | CPU latency |
| Mock generation default | Deterministic CI, no API keys | Not representative of real LLM behaviour |
| Post-retrieval permissions | Simple, testable | Wastes retrieval compute on filtered chunks |
| Content-hash skip | 0 re-embeds on unchanged run | Full hash on every discovery pass |

See [docs/decisions/](docs/decisions/) for full ADRs.

---

## Results

| Category | Result |
|---|---|
| Incremental ingestion | 40 unchanged, 0 re-indexed on second run |
| Retrieval quality | MRR 0.625, Hit@5 0.633, NDCG@5 0.702 |
| Quality gates | Passed |
| Demo scenarios | Version change, deletion sync, knowledge gaps, permissions — all verified |
| Test suite | 49 passed, 72% coverage |

---

## Limitations

- No real authentication — group permissions are simulated
- Mock generation provider by default
- CPU-bound retrieval latency (~1.1 s)
- 40-document demo corpus — not tested at enterprise scale
- Retrieval evaluation only — does not measure generation answer correctness with real LLMs

---

## Production Roadmap

1. OIDC authentication with group claims
2. Qdrant payload filters for permissions at query time
3. Commercial LLM provider integration (OpenAI / Anthropic)
4. GPU inference for embeddings and reranking
5. Source connectors: SharePoint, Google Drive, S3
6. OpenTelemetry distributed tracing
7. Horizontal ingestion workers via Prefect agent pool
8. Generation-quality evaluation with LLM-as-judge (offline batch)

---

## Skills Demonstrated

Python · RAG · Hybrid search · Embeddings · Vector databases · Document ETL · Change detection · Versioning · FastAPI · PostgreSQL · Qdrant · Evaluation metrics · Regression testing · Docker · CI/CD · Prefect · Permission-aware retrieval · Knowledge gap automation · Structured logging · CLI design
