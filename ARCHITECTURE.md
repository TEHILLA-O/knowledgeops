# Architecture

Technical architecture reference for the KnowledgeOps RAG Automation Platform.

---

## System Context

KnowledgeOps sits between document sources and end users, automating ingestion, indexing, retrieval, and grounded answer generation.

```mermaid
flowchart TB
    subgraph Sources["Document Sources"]
        DEMO[demo_knowledge/]
        LOCAL[Local Folder]
        WEB[Web Pages]
    end

    subgraph Platform["KnowledgeOps Platform"]
        API[FastAPI API + Dashboard]
        ING[Ingestion Pipeline]
        RET[Hybrid Retrieval]
        GEN[Grounded Generation]
        EVAL[Evaluation Engine]
        GAP[Knowledge Gap Tracker]
    end

    subgraph Storage["Data Stores"]
        PG[(PostgreSQL :15432)]
        QD[(Qdrant :6333)]
    end

    subgraph Users["Consumers"]
        CLI[knowledgeops CLI]
        HTTP[HTTP Clients]
        DASH[Web Dashboard]
    end

    DEMO --> ING
    LOCAL --> ING
    WEB --> ING
    ING --> PG
    ING --> QD
    HTTP --> API
    CLI --> API
    DASH --> API
    API --> RET
    RET --> QD
    RET --> PG
    API --> GEN
    GEN --> RET
    API --> GAP
    GAP --> PG
    API --> EVAL
    EVAL --> RET
```

---

## Component Overview

| Layer | Modules | Responsibility |
|---|---|---|
| **API** | `app/api/routes/`, `app/dashboard/` | REST endpoints, HTML dashboard |
| **CLI** | `app/cli/main.py` | Typer commands for demo, ingest, query, evaluate |
| **Ingestion** | `app/ingestion/` | Discover, parse, clean, chunk, embed, index |
| **Retrieval** | `app/retrieval/` | Dense, sparse, hybrid fusion, rerank, permissions |
| **Generation** | `app/generation/` | Grounded answers, citations, confidence |
| **Evaluation** | `app/evaluation/` | Metrics, runner, regression, quality gates |
| **Workflows** | `app/workflows/` | Prefect ingestion flow with retries |
| **Persistence** | `app/db/`, `app/repositories/` | SQLAlchemy models and data access |

---

## Ingestion Workflow

```mermaid
flowchart LR
    A[Discover] --> B[Change Detection]
    B --> C{Status?}
    C -->|NEW/MODIFIED| D[Parse]
    C -->|UNCHANGED| Z[Skip]
    C -->|DELETED| Y[Remove from Qdrant]
    D --> E[Clean Text]
    E --> F[Extract Metadata]
    F --> G[Chunk]
    G --> H[Embed Batch]
    H --> I[Upsert Qdrant]
    I --> J[Persist PostgreSQL]
    Y --> J
    Z --> J
```

**Key classes:** `IngestionPipeline`, `DocumentChange`, `ParserRegistry`, `chunk_document`

**Measured behaviour:**

- First run: 40 documents → 662 chunks indexed
- Second run (unchanged): 40 unchanged, 0 chunks re-indexed
- Unchanged ingestion: 0.234 s mean (3 iterations)

---

## Database and Vector Store Interaction

```mermaid
erDiagram
    DOCUMENT ||--o{ DOCUMENT_VERSION : has
    DOCUMENT ||--o{ CHUNK : contains
    INGESTION_RUN ||--o{ INGESTION_STEP : tracks
    INGESTION_RUN ||--o{ INGESTION_ERROR : may_have
    EVALUATION_RUN ||--o{ EVALUATION_RESULT : produces
    KNOWLEDGE_GAP ||--o{ GAP_QUERY : clusters

    DOCUMENT {
        uuid id
        string source
        string title
        string status
        string content_hash
    }

    CHUNK {
        uuid id
        uuid document_id
        int version
        string content_hash
        string qdrant_point_id
    }
```

PostgreSQL is the **system of record** for documents, versions, chunks, ingestion audit, evaluation runs, and knowledge gaps.

Qdrant stores **vectors and retrieval payloads** keyed by deterministic point IDs derived from chunk IDs. On deletion, Qdrant points are removed; PostgreSQL retains audit metadata.

---

## Retrieval Flow

```mermaid
flowchart TD
    Q[User Query] --> E[Embed Query]
    E --> D[Dense Search - Qdrant]
    E --> S[Sparse Search - BM25]
    D --> F[Score Fusion - alpha=0.5]
    S --> F
    F --> R[Rerank - Cross-Encoder]
    R --> P[Permission Filter]
    P --> C[Context Builder]
    C --> OUT[Top-K Chunks]
```

**Configuration** (`config/retrieval.yaml`):

| Parameter | Value |
|---|---|
| `dense_top_k` | 20 |
| `sparse_top_k` | 20 |
| `fusion_top_k` | 30 |
| `rerank_top_k` | 8 |
| `context_top_k` | 5 |
| `hybrid_alpha` | 0.5 |

**Measured latency:** hybrid retrieval mean **1099 ms** (3 iterations).

---

## Query Lifecycle

```mermaid
sequenceDiagram
    participant U as User / CLI
    participant API as FastAPI
    participant OR as QueryOrchestrator
    participant RET as RetrievalService
    participant GEN as GenerationService
    participant GAP as KnowledgeGapService
    participant DB as PostgreSQL

    U->>API: POST /api/v1/query
    API->>OR: QueryRequest
    OR->>RET: search(query, filters, user_group)
    RET->>RET: hybrid + rerank + permissions
    RET-->>OR: RetrievedChunks
    OR->>GEN: generate(context, query)
    GEN-->>OR: answer + citations + confidence
    alt insufficient evidence
        OR->>GAP: record_gap(query, scores)
        GAP->>DB: persist
    end
    OR->>DB: log query analytics
    OR-->>API: QueryResponse
    API-->>U: answer + citations + confidence
```

**Measured full query latency:** **1599 ms** mean (3 iterations).

---

## Evaluation Pipeline

```mermaid
flowchart LR
    DS[main_eval.json<br/>60 questions] --> RUN[EvaluationRunner]
    RUN --> RET[RetrievalService]
    RET --> MET[compute_query_metrics]
    MET --> AGG[aggregate_metrics]
    AGG --> PG[(PostgreSQL)]
    AGG --> BL[baseline_metrics.json]
    BL --> REG[Regression Compare]
    AGG --> GATE[Quality Gates]
```

**Baseline metrics (top_k=5):**

| Metric | Value |
|---|---|
| MRR | 0.625 |
| Hit Rate @ 5 | 0.633 |
| Precision @ 5 | 0.573 |
| Recall @ 5 | 0.633 |
| NDCG @ 5 | 0.702 |

Quality gates: `hit_rate_at_5_min: 0.6`, `mrr_min: 0.5` — both passed.

---

## Permission Filtering

```mermaid
flowchart TD
    R[Retrieved Chunks] --> F{allowed_groups empty?}
    F -->|Yes| KEEP[Keep - public]
    F -->|No| G{User group in allowed_groups?}
    G -->|Yes| KEEP
    G -->|No| DROP[Remove chunk]
    KEEP --> C[Context Builder]
    DROP --> LOG[Log permission_filter_applied]
```

Filtering occurs after reranking and before context construction. Verified in case-study demo step 19.

---

## Prefect Workflow

`app/workflows/ingestion_flow.py` wraps the ingestion pipeline as a Prefect flow:

1. `discover-documents` task (retries: 2)
2. `run-ingestion-pipeline` task (retries: 1)
3. Returns `IngestionRunSummary`

Prefect server is not required for local operation — the flow can be invoked directly. A dedicated Prefect container was intentionally omitted from Docker Compose.

---

## Deployment Topology

```mermaid
flowchart TB
    subgraph DockerCompose["docker compose up"]
        APP[app :8000]
        PG[(postgres :15432)]
        QD[(qdrant :6333)]
    end

    APP --> PG
    APP --> QD
    VOL[demo_knowledge volume] --> APP
    CFG[config/ read-only] --> APP
```

---

## Configuration

| File | Purpose |
|---|---|
| `.env` | Secrets, provider selection, connection URLs |
| `config/ingestion.yaml` | Chunking, sources, batch size |
| `config/retrieval.yaml` | Hybrid, rerank, confidence, quality gates |

Default local PostgreSQL URL: `postgresql+asyncpg://knowledgeops:knowledgeops@localhost:15432/knowledgeops`

---

## Extension Points

| Area | Interface | Future connectors |
|---|---|---|
| Document sources | `DocumentSource` ABC | Google Drive, SharePoint, S3, Notion, Confluence |
| Parsers | `ParserRegistry` | Additional MIME types |
| Embeddings | `EmbeddingProvider` | OpenAI, Cohere |
| Generation | `GenerationProvider` | OpenAI, Anthropic |
| Reranking | `RerankingProvider` | Cohere Rerank |

See [docs/decisions/](decisions/) for architecture decision records.
