"""Data access repositories."""

from app.repositories.analytics_repo import AnalyticsRepository
from app.repositories.document_repo import DocumentRepository
from app.repositories.evaluation_repo import EvaluationRepository
from app.repositories.ingestion_repo import IngestionRepository
from app.repositories.knowledge_gap_repo import KnowledgeGapRepository
from app.repositories.query_repo import QueryRepository

__all__ = [
    "AnalyticsRepository",
    "DocumentRepository",
    "EvaluationRepository",
    "IngestionRepository",
    "KnowledgeGapRepository",
    "QueryRepository",
]
