"""Shared Pydantic schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.core.constants import ConfidenceLevel, QueryStatus


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class PaginatedResponse(BaseModel):
    items: list[Any]
    total: int
    page: int
    page_size: int
    pages: int


class ErrorResponse(BaseModel):
    error: str
    code: str
    detail: str | None = None


class HealthResponse(BaseModel):
    status: str
    app: str
    version: str = "0.1.0"


class ReadinessResponse(BaseModel):
    status: str
    postgres: str
    qdrant: str


class DocumentReference(BaseModel):
    stable_id: str
    filename: str
    source: str
    source_url: str | None = None
    checksum: str
    modified_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RawDocument(BaseModel):
    reference: DocumentReference
    content: bytes
    content_type: str


class ParsedDocument(BaseModel):
    text: str
    title: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    sections: list[dict[str, Any]] = Field(default_factory=list)


class DocumentChunk(BaseModel):
    chunk_id: str
    document_id: str
    document_stable_id: str
    document_title: str
    document_version: int
    chunk_index: int
    content: str
    content_hash: str
    section: str | None = None
    page_number: int | None = None
    token_count: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class RetrievedChunk(BaseModel):
    chunk_id: str
    document_id: str
    document_title: str
    document_version: int
    content: str
    dense_score: float | None = None
    sparse_score: float | None = None
    fusion_score: float | None = None
    rerank_score: float | None = None
    section: str | None = None
    page_number: int | None = None
    source_url: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RetrievalFilters(BaseModel):
    source: str | None = None
    document_type: str | None = None
    department: str | None = None
    tag: str | None = None
    classification: str | None = None
    version: int | None = None
    user_group: str | None = None


class Message(BaseModel):
    role: str
    content: str


class GenerationResult(BaseModel):
    answer: str
    confidence_score: float
    confidence_level: ConfidenceLevel
    knowledge_gap: bool
    input_tokens: int = 0
    output_tokens: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class CitationInfo(BaseModel):
    document_id: str
    document_title: str
    version: int
    page: int | None = None
    section: str | None = None
    chunk_id: str
    source_url: str | None = None
    citation_text: str | None = None


class ConfidenceInfo(BaseModel):
    level: ConfidenceLevel
    score: float
    signals: dict[str, float] = Field(default_factory=dict)


class QueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    filters: RetrievalFilters | None = None
    user_group: str | None = None
    include_debug: bool = False


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    filters: RetrievalFilters | None = None
    user_group: str | None = None
    top_k: int = Field(default=10, ge=1, le=50)


class QueryResponse(BaseModel):
    query: str
    answer: str | None = None
    status: QueryStatus
    confidence: ConfidenceInfo | None = None
    citations: list[CitationInfo] = Field(default_factory=list)
    retrieval: dict[str, Any] = Field(default_factory=dict)
    latency_ms: int = 0
    debug: dict[str, Any] | None = None


class SearchResponse(BaseModel):
    query: str
    results: list[RetrievedChunk]
    latency_ms: int = 0


class DocumentSummary(BaseModel):
    id: str
    stable_id: str
    title: str
    filename: str
    document_type: str
    source: str
    current_version: int
    status: str
    department: str | None = None
    chunk_count: int
    is_deleted: bool
    last_indexed_at: datetime | None = None


class DocumentVersionInfo(BaseModel):
    id: str
    version: int
    content_hash: str
    status: str
    discovered_at: datetime
    indexed_at: datetime | None = None


class IngestionRunSummary(BaseModel):
    id: str
    status: str
    source: str
    documents_discovered: int
    documents_new: int
    documents_modified: int
    documents_unchanged: int
    documents_deleted: int
    chunks_indexed: int
    health_status: str | None = None
    started_at: datetime
    completed_at: datetime | None = None


class KnowledgeGapSummary(BaseModel):
    id: str
    question: str
    frequency: int
    best_retrieval_score: float | None
    suggested_topic: str | None
    status: str
    last_seen_at: datetime


class AnalyticsSummary(BaseModel):
    documents_indexed: int
    chunks_indexed: int
    queries_today: int
    answered_percentage: float
    insufficient_evidence_percentage: float
    average_retrieval_latency_ms: float
    knowledge_gaps_count: int
    latest_evaluation_score: float | None = None
    index_health: str | None = None
