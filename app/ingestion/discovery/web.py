"""Web page document discovery."""

from __future__ import annotations

from datetime import UTC, datetime
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from app.core.exceptions import DocumentProcessingError
from app.ingestion.discovery.base import DocumentSource
from app.ingestion.hashing import checksum_bytes, stable_id
from app.schemas.common import DocumentReference, RawDocument


class WebPageSource(DocumentSource):
    """Discover and fetch documents from HTTP(S) URLs."""

    def __init__(
        self,
        urls: list[str],
        source_name: str = "web",
        timeout_seconds: float = 30.0,
    ) -> None:
        super().__init__(source_name=source_name)
        self.urls = urls
        self.timeout_seconds = timeout_seconds

    def _filename_from_url(self, url: str) -> str:
        parsed = urlparse(url)
        path = parsed.path.rstrip("/")
        if path and "/" in path:
            name = path.rsplit("/", 1)[-1]
            if name:
                return name
        host = parsed.netloc or "page"
        return f"{host}.html"

    def _build_reference(self, url: str, content: bytes) -> DocumentReference:
        return DocumentReference(
            stable_id=stable_id(self.source_name, url),
            filename=self._filename_from_url(url),
            source=self.source_name,
            source_url=url,
            checksum=checksum_bytes(content),
            modified_at=datetime.now(tz=UTC),
            metadata={
                "url": url,
                "extension": ".html",
                "size_bytes": len(content),
            },
        )

    async def discover(self) -> list[DocumentReference]:
        references: list[DocumentReference] = []
        async with httpx.AsyncClient(timeout=self.timeout_seconds, follow_redirects=True) as client:
            for url in self.urls:
                response = await client.get(url)
                response.raise_for_status()
                references.append(self._build_reference(url, response.content))
        return references

    async def fetch(self, reference: DocumentReference) -> RawDocument:
        url = reference.source_url or reference.metadata.get("url")
        if not url:
            raise DocumentProcessingError(
                f"Missing URL for web document {reference.stable_id}",
                document_id=reference.stable_id,
            )
        async with httpx.AsyncClient(timeout=self.timeout_seconds, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            content = response.content

        content_type = response.headers.get("content-type", "text/html").split(";")[0].strip()
        if "html" in content_type:
            soup = BeautifulSoup(content, "lxml")
            for tag in soup(["script", "style", "noscript"]):
                tag.decompose()
            text_preview = soup.get_text(" ", strip=True)[:500]
            reference.metadata["text_preview"] = text_preview

        return RawDocument(
            reference=reference,
            content=content,
            content_type=content_type,
        )
