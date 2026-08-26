"""Application constants."""

from enum import StrEnum


class DocumentStatus(StrEnum):
    NEW = "NEW"
    UNCHANGED = "UNCHANGED"
    MODIFIED = "MODIFIED"
    DELETED = "DELETED"
    INDEXED = "INDEXED"
    FAILED = "FAILED"


class IngestionRunStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class IndexHealthStatus(StrEnum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    FAILED_QUALITY_GATE = "FAILED_QUALITY_GATE"


class QueryStatus(StrEnum):
    ANSWERED = "ANSWERED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    ERROR = "ERROR"


class ConfidenceLevel(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class KnowledgeGapStatus(StrEnum):
    UNRESOLVED = "UNRESOLVED"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"


class Visibility(StrEnum):
    PUBLIC_INTERNAL = "PUBLIC_INTERNAL"
    TEAM = "TEAM"
    RESTRICTED = "RESTRICTED"


class UserGroup(StrEnum):
    HR = "HR"
    FINANCE = "FINANCE"
    ENGINEERING = "ENGINEERING"
    SECURITY = "SECURITY"
    OPERATIONS = "OPERATIONS"
    PROCUREMENT = "PROCUREMENT"
    LEARNING = "LEARNING"
    ALL = "ALL"


DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
QDRANT_VECTOR_SIZE = 384  # all-MiniLM-L6-v2
