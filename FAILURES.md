# Failure modes, fixes, and results

Honest engineering notes for this project. Nothing here is invented for polish.

## What can go wrong

- **Restricted chunks retrieved for the wrong user.** Impact: data leakage via RAG. Mitigation: `allowed_groups` permission filter before generation; production needs real IdP claims (documented limitation: group is a request parameter today).
- **Stale or duplicated embeddings.** Re-indexing everything wastes compute; missing change detection serves old answers. Mitigation: content-hash change detection (NEW/UNCHANGED/MODIFIED/DELETED) and document versioning.
- **Hallucinated citations / low-evidence answers.** Impact: confident wrong guidance. Mitigation: grounded generation, refuse + knowledge-gap records on low confidence, deterministic eval suite.
- **Parser or query DoS.** Crafted uploads or expensive retrieval. Mitigation: format parsers behind a registry; production checklist calls for rate limits and size caps (`SECURITY.md`, `BUILD_REPORT.md`).

## What went wrong

**No recorded production incident in this repo yet.** Visible engineering gaps and measured leftovers:

1. Default generation provider is mock, so demo answers do not exercise real LLM latency or failure modes (`BUILD_REPORT.md` known limitations).
2. CI still reports 2 Ruff issues and 16 mypy errors (non-blocking for demo).
3. API authentication middleware is not enforced in v0.1; open endpoints when the server runs (`SECURITY.md`).

## How it was resolved

1. Mock provider is intentional for offline demos; Ollama/real providers are pluggable (`ARCHITECTURE.md`, ADRs on provider abstraction).
2. Lint/type debt is tracked in `BUILD_REPORT.md` as cleanup before production hardening; tests remain green.
3. Permission filtering and classification metadata are implemented for the case study; production OIDC/SAML is listed as required follow-up, not claimed done.

## Results

From `BUILD_REPORT.md` / README badges (measured in-repo):

- **49 tests passed**, **0 failed**, coverage about **72%**.
- Evaluation: `main_eval` **MRR 0.625**, **NDCG@5 0.702** (60-question benchmark).
- Incremental ingest demo claim: unchanged docs skipped (40 unchanged, 0 re-indexed) in the comparison table.
- Successful local demo: Docker Compose (app, Postgres, Qdrant), CLI query with citations, dashboard, knowledge-gap creation on refuse.
