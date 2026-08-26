"""API route modules."""

from app.api.routes import (
    analytics,
    documents,
    evaluations,
    health,
    ingestion,
    knowledge_gaps,
    query,
)

__all__ = [
    "analytics",
    "documents",
    "evaluations",
    "health",
    "ingestion",
    "knowledge_gaps",
    "query",
]
