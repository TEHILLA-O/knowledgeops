"""Document discovery source abstractions."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.schemas.common import DocumentReference, RawDocument


class DocumentSource(ABC):
    """Abstract base for document discovery backends."""

    def __init__(self, source_name: str) -> None:
        self.source_name = source_name

    @abstractmethod
    async def discover(self) -> list[DocumentReference]:
        """Return references for all documents available from this source."""

    @abstractmethod
    async def fetch(self, reference: DocumentReference) -> RawDocument:
        """Load the raw bytes for a discovered document reference."""
