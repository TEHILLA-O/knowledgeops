"""Application exceptions."""


class KnowledgeOpsError(Exception):
    """Base exception for KnowledgeOps platform."""

    def __init__(self, message: str, code: str = "INTERNAL_ERROR") -> None:
        self.message = message
        self.code = code
        super().__init__(message)


class ConfigurationError(KnowledgeOpsError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="CONFIGURATION_ERROR")


class DocumentProcessingError(KnowledgeOpsError):
    def __init__(self, message: str, document_id: str | None = None) -> None:
        self.document_id = document_id
        super().__init__(message, code="DOCUMENT_PROCESSING_ERROR")


class ProviderError(KnowledgeOpsError):
    def __init__(self, message: str, provider: str | None = None) -> None:
        self.provider = provider
        super().__init__(message, code="PROVIDER_ERROR")


class RetrievalError(KnowledgeOpsError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="RETRIEVAL_ERROR")


class NotFoundError(KnowledgeOpsError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="NOT_FOUND")


class ValidationError(KnowledgeOpsError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="VALIDATION_ERROR")


class QualityGateError(KnowledgeOpsError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="QUALITY_GATE_ERROR")
