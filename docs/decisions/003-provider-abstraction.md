# ADR 003: Provider Abstraction for Embeddings and Generation

**Status:** Accepted  
**Date:** 2026-08-26

## Context

KnowledgeOps must run end-to-end without paid API keys for CI, local development, and portfolio demonstrations. Production deployments will swap in commercial LLM and embedding providers. Hard-coding provider SDK calls throughout ingestion and generation would make testing brittle and provider migration costly.

## Decision

Introduce provider abstractions in `app/providers/`:

| Interface | Implementations | Default |
|---|---|---|
| `EmbeddingProvider` | `LocalEmbeddingProvider`, `MockEmbeddingProvider` | `local` (`all-MiniLM-L6-v2`) |
| `GenerationProvider` | `MockGenerationProvider`, `OllamaGenerationProvider` | `mock` |
| `RerankingProvider` | `LocalRerankerProvider`, none | `local` |

`app/providers/factory.py` resolves providers from environment variables (`EMBEDDING_PROVIDER`, `GENERATION_PROVIDER`, `RERANKING_PROVIDER`). CI sets `EMBEDDING_PROVIDER=mock` and `GENERATION_PROVIDER=mock` to avoid model downloads.

## Alternatives Considered

| Alternative | Why not chosen |
|---|---|
| **Direct OpenAI SDK calls** | Locks tests and CI to external APIs and secrets |
| **LangChain provider wrappers** | Extra dependency layer; project needs fine-grained control over grounding and citations |
| **Single monolithic AI client** | Prevents independent scaling of embedding vs generation workloads |

## Consequences

**Positive**

- Zero-cost CI/CD pipeline — no API keys required
- Embedding batch benchmark: **0.027 s** mean for 3-text batch (local provider)
- Swapping providers is an environment change, not a code change
- Mock generation enforces grounding rules deterministically in tests

**Negative**

- Mock generation does not reflect real LLM behaviour (latency, phrasing, edge-case hallucinations)
- Each new provider requires a concrete implementation and test fixtures
- Local embedding model adds ~80 MB model download on first run

**Follow-up**

- Add OpenAI / Anthropic generation providers behind the same interface
- Track `embedding_model` version in chunk metadata to support controlled re-indexing on model change
