# ADR 006: Metadata-Based Permission Filtering

**Status:** Accepted  
**Date:** 2026-08-26

## Context

Internal knowledge bases contain documents restricted to specific departments or roles (HR compensation, executive policies, finance-only procedures). A RAG system that retrieves restricted content and feeds it to any user creates a data-leakage risk, regardless of what the LLM outputs.

The case-study demo verifies permission filtering: ENGINEERING users do not see FINANCE-restricted chunks; FINANCE users do.

## Decision

Implement **post-retrieval permission filtering** in `app/retrieval/permissions.py`:

- Chunks carry `metadata.allowed_groups` (list of group names, or empty for public)
- `PermissionFilter.filter_chunks()` removes chunks the requesting user's group cannot access
- `UserGroup.ALL` in `allowed_groups` grants universal access
- API and CLI accept `user_group` parameter (default: `ENGINEERING` from `DEFAULT_USER_GROUP`)
- Filtering occurs **after** hybrid retrieval and reranking, **before** context building and generation

```python
# Public chunk: allowed_groups = []  → visible to all
# Restricted:   allowed_groups = ["FINANCE"]  → FINANCE only
```

## Alternatives Considered

| Alternative | Why not chosen |
|---|---|
| **Qdrant payload filter at query time** | Valid for production; post-filter chosen for clarity and testability in v1 |
| **Separate collections per department** | Operational overhead; poor cross-department public document sharing |
| **LLM instruction to ignore restricted content** | Unreliable; security must not depend on model compliance |
| **Full OAuth2 / RBAC integration** | Out of scope for case study; group parameter simulates identity |

## Consequences

**Positive**

- Verified in demo step 19: restricted retrieval demonstration
- Filtered chunks are logged with `permission_filter_applied` for audit
- Eval dataset includes `requires_access_group` field for permission-aware test cases

**Negative**

- Post-filter wastes retrieval compute on chunks that will be discarded
- Group membership is a simple string, not a full identity provider integration
- Over-restrictive filtering can trigger false knowledge-gap records

**Follow-up**

- Push `allowed_groups` into Qdrant payload filters to avoid retrieving restricted content
- Integrate with corporate IdP (OIDC) and resolve group membership from JWT claims
- Add integration tests for every `requires_access_group` eval question
