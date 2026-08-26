# ADR 004: Content-Hash Document Versioning

**Status:** Accepted  
**Date:** 2026-08-26

## Context

Enterprise knowledge bases change continuously. Re-embedding unchanged documents wastes compute and introduces retrieval drift. The platform must detect NEW, UNCHANGED, MODIFIED, and DELETED documents, maintain version history, and re-index only what changed.

Measured ingestion behaviour:

| Run | Documents | Chunks indexed |
|---|---|---|
| First run | 40 discovered | 662 indexed |
| Second run (unchanged) | 40 unchanged | 0 re-indexed |

Second-run ingestion benchmark (unchanged docs): **0.234 s** mean over 3 iterations.

## Decision

Implement change detection in `app/ingestion/change_detection.py` and versioning in PostgreSQL:

- **Stable document ID** derived from source + path
- **Content hash** (`content_hash`) computed after parsing and cleaning
- **Checksum** of raw file bytes for discovery-level change hints
- **DocumentVersion** records: version number, hash, timestamps, status, `previous_version_id`
- **Ingestion pipeline** skips embedding for UNCHANGED documents; re-chunks and re-embeds MODIFIED; removes Qdrant points and marks DELETED

Version history is exposed via `GET /api/v1/documents/{document_id}/versions`.

## Alternatives Considered

| Alternative | Why not chosen |
|---|---|
| **Re-index everything on every run** | Wastes compute; measured 0 chunks re-indexed on second run proves incremental approach |
| **File modification time only** | Unreliable across copies, git checkouts, and container volume mounts |
| **Git-based versioning** | Not all sources are git-tracked (web, future SharePoint/S3) |
| **Immutable document IDs per version** | Complicates citation stability; version chain preferred for audit trail |

## Consequences

**Positive**

- Demonstrated in case-study demo: policy edit triggers re-index of changed document only
- Deletion sync removes stale chunks from Qdrant while retaining audit metadata in PostgreSQL
- Embedding cache keyed on chunk hash avoids redundant model inference

**Negative**

- Hash recomputation requires full parse+clean on every discovery pass (cheap at 40 documents, scales with corpus)
- Moving/renaming files appears as DELETE + NEW unless source identifiers are normalised
- Version explosion requires retention policy in production

**Follow-up**

- Add configurable version retention (keep last N versions)
- Support embedding-model-change re-index flag independent of content-hash changes
