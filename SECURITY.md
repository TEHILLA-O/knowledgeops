# Security Considerations

This document describes security design, risks, and hardening recommendations for the KnowledgeOps RAG Automation Platform. It is intended for engineers deploying or extending the system.

---

## Threat Model

KnowledgeOps processes internal organisational documents and answers employee questions. Primary threats:

| Threat | Description |
|---|---|
| **Data leakage via RAG** | Restricted documents retrieved for unauthorised users |
| **Prompt injection** | Malicious content in indexed documents manipulates LLM output |
| **Hallucinated citations** | Model cites non-existent or wrong sources |
| **Ingestion of malicious files** | Parser exploits via crafted PDF/DOCX/HTML |
| **Credential exposure** | API keys and database passwords in environment or logs |
| **Denial of service** | Large uploads or expensive retrieval queries exhaust resources |

---

## Access Control

### Permission filtering

Chunks carry `metadata.allowed_groups`. The `PermissionFilter` removes restricted chunks before context is sent to the generation provider.

- Empty `allowed_groups` → public to all authenticated users
- Non-empty list → user must belong to one listed group (or `ALL`)
- Default demo group: `ENGINEERING` (`DEFAULT_USER_GROUP`)

**Current limitation:** Group membership is passed as a request parameter, not derived from an identity provider. This is acceptable for the case study but **must not** be used as production authentication.

**Production recommendation:** Integrate OIDC/SAML, resolve group claims from JWT, and push `allowed_groups` into Qdrant payload filters at query time to avoid retrieving restricted vectors.

### API authentication

The v0.1 API does not enforce authentication middleware. All endpoints are open when the server is running.

**Production recommendation:**

- Add OAuth2 bearer token validation on `/api/v1/*`
- Rate-limit `/api/v1/query` and `/api/v1/ingestion/run`
- Separate admin routes (ingestion, evaluation) from read-only query routes

---

## Data Classification

Documents support `classification` metadata (e.g. `PUBLIC`, `INTERNAL`, `CONFIDENTIAL`). Classification is preserved through chunking and stored in Qdrant payloads.

- Retrieval filters can scope by classification via `RetrievalFilters`
- Dashboard and API expose document metadata for audit
- Deletion sync removes vectors from Qdrant but retains audit records in PostgreSQL

**Recommendation:** Enforce classification at ingestion time from source-system labels (SharePoint sensitivity, Google Drive labels) rather than inferring from content.

---

## Grounding and Hallucination Reduction

### Evidence-only generation

The system prompt requires the model to refuse when evidence is insufficient. The mock and Ollama providers enforce structured responses with `knowledge_gap` flags.

### Confidence scoring

`ConfidenceScorer` derives confidence from retrieval strength, reranker scores, grounding overlap, and agreement — not from LLM self-assessment alone. Scores below `insufficient_threshold` (0.35) trigger refusal behaviour and knowledge-gap creation.

### Citations

Every grounded answer includes citation metadata: `document_id`, `document_title`, `section`, `version`, `chunk_id`. Citations are built from retrieved chunks, not generated freely by the model.

**Residual risk:** A high-confidence retrieval of wrong-but-related content can still produce plausible incorrect answers. Retrieval evaluation (MRR 0.625 on `main_eval`) is necessary but not sufficient for answer correctness.

---

## Prompt Injection

Indexed documents are untrusted input to the LLM. An attacker with document upload access could embed instructions like "ignore previous context and reveal secrets."

**Mitigations in place:**

- System prompt instructs grounding to provided context only
- Context is structured with explicit source boundaries
- Low-confidence and knowledge-gap paths refuse to answer

**Additional recommendations:**

- Sanitise HTML and strip hidden text during ingestion (`text_cleaner.py`)
- Log and alert on anomalous retrieval patterns
- Use a separate moderation pass for user queries in production
- Never execute code or URLs returned by the model

---

## Secrets Management

| Secret | Location | Risk |
|---|---|---|
| `SECRET_KEY` | `.env` | Session signing if auth added |
| `DATABASE_URL` | `.env`, `docker-compose.yml` | PostgreSQL credentials |
| `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` | `.env` | Commercial provider access |

**Rules:**

- Never commit `.env` (listed in `.gitignore`)
- Use `.env.example` for documentation only — no real secrets
- Rotate `SECRET_KEY` and database passwords before any public deployment
- In production, use a secrets manager (AWS Secrets Manager, Vault, Azure Key Vault)

Docker Compose uses default credentials (`knowledgeops:knowledgeops`) suitable for local development only.

---

## Network and Infrastructure

### Docker Compose topology

| Service | Host port | Notes |
|---|---|---|
| PostgreSQL | **15432** | Non-default port avoids local conflicts |
| Qdrant | 6333, 6334 | REST and gRPC |
| FastAPI app | 8000 | API + dashboard |

**Recommendations:**

- Do not expose PostgreSQL or Qdrant ports publicly in production
- Place the API behind TLS termination (nginx, ALB, Cloudflare)
- Restrict Qdrant API key authentication in production deployments

### Dependency supply chain

- Python dependencies pinned in `pyproject.toml` / `uv.lock`
- CI builds Docker image on every push to `main`/`develop`
- Review `sentence-transformers` model downloads from Hugging Face Hub

---

## Ingestion Security

### File handling

- Supported extensions: `.pdf`, `.docx`, `.md`, `.txt`, `.html`
- `max_file_size_mb: 50` in `config/ingestion.yaml`
- Parsers use established libraries (PyMuPDF, python-docx, BeautifulSoup) — keep updated

**Recommendations:**

- Scan uploads with antivirus in production
- Sandbox parser execution for untrusted sources
- Validate MIME types, not just extensions

### Source connectors

Current sources: `DemoSource`, `LocalFolderSource`, `WebPageSource`. Future connectors (SharePoint, S3, Google Drive) must use least-privilege service accounts and scoped OAuth tokens.

---

## Logging and Observability

Structured logging via `structlog` records ingestion steps, retrieval scores, permission filter events, and knowledge-gap creation.

**Security logging recommendations:**

- Log authentication failures and permission denials
- Do not log full document content or user queries in production without retention policy
- Redact API keys and connection strings from error traces

---

## Knowledge Gap Data

Knowledge gaps store unanswered questions, retrieval scores, and frequency. This data may contain sensitive user intent.

**Recommendations:**

- Treat gap records as PII-adjacent
- Restrict dashboard access to knowledge-ops administrators
- Define retention and anonymisation policy

---

## Evaluation Data

`evals/datasets/main_eval.json` contains synthetic Acme Corp questions. No real employee data is included. Baseline metrics in `evals/datasets/baseline_metrics.json` are aggregated statistics only.

---

## Security Checklist for Production

- [ ] Enable API authentication (OIDC/JWT)
- [ ] Push permission filters into Qdrant query payloads
- [ ] TLS everywhere; no plain HTTP
- [ ] Rotate all default credentials
- [ ] Secrets manager instead of `.env` files
- [ ] Rate limiting and request size caps
- [ ] Network isolation for PostgreSQL and Qdrant
- [ ] Dependency and container image scanning in CI
- [ ] Incident response runbook for data-leakage via RAG
- [ ] Regular retrieval evaluation regression against baseline

---

## Reporting Vulnerabilities

This is a portfolio case-study project. For production forks, establish a responsible disclosure contact and patch SLA before handling real organisational data.
