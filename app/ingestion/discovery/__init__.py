"""Document discovery sources."""

from app.ingestion.discovery.base import DocumentSource
from app.ingestion.discovery.demo import DemoSource
from app.ingestion.discovery.local_folder import LocalFolderSource
from app.ingestion.discovery.web import WebPageSource

__all__ = [
    "DemoSource",
    "DocumentSource",
    "LocalFolderSource",
    "WebPageSource",
]
