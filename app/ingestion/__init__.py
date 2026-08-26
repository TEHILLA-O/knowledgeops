"""Ingestion package for KnowledgeOps RAG platform."""

from app.ingestion.change_detection import DocumentChange, detect_changes, reconcile_content_hash
from app.ingestion.pipeline import IngestionPipeline

__all__ = [
    "DocumentChange",
    "IngestionPipeline",
    "detect_changes",
    "reconcile_content_hash",
]
