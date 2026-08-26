"""Document parsers."""

from app.ingestion.parsers.base import DocumentParser, ParserRegistry
from app.ingestion.parsers.docx_parser import DocxParser
from app.ingestion.parsers.html_parser import HtmlParser
from app.ingestion.parsers.markdown_parser import MarkdownParser
from app.ingestion.parsers.pdf_parser import PdfParser
from app.ingestion.parsers.text_parser import TextParser


def create_parser_registry() -> ParserRegistry:
    """Create a registry with all built-in parsers registered."""
    registry = ParserRegistry()
    registry.register(PdfParser())
    registry.register(DocxParser())
    registry.register(MarkdownParser())
    registry.register(HtmlParser())
    registry.register(TextParser())
    return registry


default_parser_registry = create_parser_registry()

__all__ = [
    "DocxParser",
    "DocumentParser",
    "HtmlParser",
    "MarkdownParser",
    "ParserRegistry",
    "PdfParser",
    "TextParser",
    "create_parser_registry",
    "default_parser_registry",
]
