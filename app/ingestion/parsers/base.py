"""Document parser abstractions and registry."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.core.exceptions import DocumentProcessingError
from app.schemas.common import ParsedDocument, RawDocument


class DocumentParser(ABC):
    """Abstract parser that converts raw bytes into structured text."""

    @abstractmethod
    def supports(self, content_type: str, filename: str) -> bool:
        """Return True when this parser can handle the given document."""

    @abstractmethod
    def parse(self, raw: RawDocument) -> ParsedDocument:
        """Parse raw document bytes into text and metadata."""


class ParserRegistry:
    """Registry for selecting parsers by content type or filename."""

    def __init__(self) -> None:
        self._parsers: list[DocumentParser] = []

    def register(self, parser: DocumentParser) -> None:
        self._parsers.append(parser)

    def get_parser(self, raw: RawDocument) -> DocumentParser:
        filename = raw.reference.filename
        content_type = raw.content_type
        for parser in self._parsers:
            if parser.supports(content_type, filename):
                return parser
        raise DocumentProcessingError(
            f"No parser available for '{filename}' ({content_type})",
            document_id=raw.reference.stable_id,
        )

    def parse(self, raw: RawDocument) -> ParsedDocument:
        parser = self.get_parser(raw)
        return parser.parse(raw)
