"""Prefect workflow definitions for KnowledgeOps automation."""

from app.workflows.ingestion_flow import ingestion_flow, run_ingestion_flow

__all__ = ["ingestion_flow", "run_ingestion_flow"]
