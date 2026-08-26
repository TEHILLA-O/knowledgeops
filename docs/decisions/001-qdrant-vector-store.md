# ADR 001: Qdrant as Vector Store

**Status:** Accepted  
**Date:** 2026-08-26

## Context

KnowledgeOps requires a vector database to store dense embeddings for semantic retrieval, support metadata filtering, and scale independently from the relational metadata store. The platform must run locally via Docker for development and case-study demonstrations without paid cloud dependencies.

PostgreSQL holds document metadata, version history, ingestion audit trails, and knowledge-gap records. Vector search must support:

- Dense cosine similarity over 384-dimensional embeddings (`all-MiniLM-L6-v2`)
- Payload-based metadata filters (department, classification, `allowed_groups`)
- Deterministic point IDs tied to chunk identifiers for idempotent upserts and deletions
- Clean startup in `docker compose` alongside PostgreSQL

## Decision

Use **Qdrant** (`qdrant/qdrant:v1.12.5`) as the dedicated vector store. Collection `knowledgeops_chunks` is created automatically at application startup via `QdrantService.ensure_collection()`.

Chunk vectors and retrieval payloads live in Qdrant. PostgreSQL remains the system of record for documents, versions, chunks, and ingestion runs.

## Alternatives Considered

| Alternative | Why not chosen |
|---|---|
| **pgvector (PostgreSQL extension)** | Couples vector and relational workloads; harder to tune ANN independently; adds extension management to PostgreSQL image |
| **Pinecone / Weaviate Cloud** | Introduces external dependency and API keys; unsuitable for offline portfolio demo |
| **Chroma (embedded)** | Simpler for tutorials but weaker production metadata filtering and multi-process concurrency story |
| **Elasticsearch hybrid** | Heavier operational footprint; BM25 already handled in-process via `rank-bm25` |

## Consequences

**Positive**

- Clear separation of concerns: PostgreSQL for transactional metadata, Qdrant for ANN search
- Native payload filtering supports permission and department scoping at retrieval time
- Docker Compose provides a one-command local stack (`postgres` on host port **15432**, `qdrant` on **6333**)
- `qdrant-client` integrates cleanly with async FastAPI services

**Negative**

- Two data stores must stay consistent during ingestion (chunk upsert/delete in Qdrant + PostgreSQL)
- Backup and disaster-recovery procedures must cover both systems
- Sparse vectors are computed in-process (BM25) rather than stored in Qdrant sparse indexes

**Follow-up**

- Monitor collection size and consider quantization if chunk count exceeds demo scale
- Evaluate Qdrant sparse vectors if lexical recall becomes a bottleneck at production scale
