"""Local filesystem document discovery."""

from __future__ import annotations

import mimetypes
from datetime import UTC, datetime
from pathlib import Path

from app.core.config import Settings, get_settings
from app.core.exceptions import DocumentProcessingError
from app.ingestion.discovery.base import DocumentSource
from app.ingestion.hashing import checksum_bytes, stable_id
from app.schemas.common import DocumentReference, RawDocument


class LocalFolderSource(DocumentSource):
    """Discover documents from a local directory tree."""

    def __init__(
        self,
        folder_path: str | Path,
        source_name: str = "local_folder",
        settings: Settings | None = None,
        supported_extensions: list[str] | None = None,
    ) -> None:
        super().__init__(source_name=source_name)
        self.settings = settings or get_settings()
        path = Path(folder_path)
        if not path.is_absolute():
            path = self.settings.project_root / path
        self.folder_path = path.resolve()
        config = self.settings.ingestion_config.get("ingestion", {})
        self.supported_extensions = supported_extensions or config.get(
            "supported_extensions",
            [".pdf", ".docx", ".md", ".txt", ".html"],
        )

    def _iter_files(self) -> list[Path]:
        if not self.folder_path.exists():
            return []
        files: list[Path] = []
        for path in self.folder_path.rglob("*"):
            if path.is_file() and path.suffix.lower() in self.supported_extensions:
                files.append(path)
        return sorted(files)

    def _relative_path(self, file_path: Path) -> str:
        return file_path.relative_to(self.folder_path).as_posix()

    def _build_reference(self, file_path: Path) -> DocumentReference:
        relative_path = self._relative_path(file_path)
        content = file_path.read_bytes()
        modified_at = datetime.fromtimestamp(file_path.stat().st_mtime, tz=UTC)
        return DocumentReference(
            stable_id=stable_id(self.source_name, relative_path),
            filename=file_path.name,
            source=self.source_name,
            source_url=None,
            checksum=checksum_bytes(content),
            modified_at=modified_at,
            metadata={
                "path": relative_path,
                "absolute_path": str(file_path),
                "extension": file_path.suffix.lower(),
                "size_bytes": len(content),
            },
        )

    async def discover(self) -> list[DocumentReference]:
        return [self._build_reference(path) for path in self._iter_files()]

    async def fetch(self, reference: DocumentReference) -> RawDocument:
        relative_path = reference.metadata.get("path")
        if not relative_path:
            raise DocumentProcessingError(
                f"Missing path metadata for document {reference.stable_id}",
                document_id=reference.stable_id,
            )
        file_path = self.folder_path / relative_path
        if not file_path.exists():
            raise DocumentProcessingError(
                f"File not found: {file_path}",
                document_id=reference.stable_id,
            )
        content = file_path.read_bytes()
        content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        return RawDocument(
            reference=reference,
            content=content,
            content_type=content_type,
        )
