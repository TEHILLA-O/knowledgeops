"""Full ingestion pipeline orchestration."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.constants import DocumentStatus, IngestionRunStatus
from app.core.exceptions import DocumentProcessingError
from app.core.logging import get_logger
from app.db.models.base import (
    Chunk,
    Document,
    DocumentVersion,
    IngestionError,
    IngestionRun,
    IngestionStep,
    generate_uuid,
)
from app.ingestion.change_detection import DocumentChange, detect_changes, reconcile_content_hash
from app.ingestion.chunking import chunk_document
from app.ingestion.cleaning import clean_text
from app.ingestion.discovery.base import DocumentSource
from app.ingestion.hashing import content_hash
from app.ingestion.metadata import extract_metadata, infer_document_type
from app.ingestion.parsers import ParserRegistry, default_parser_registry
from app.providers.base import EmbeddingProvider
from app.retrieval.qdrant_client import QdrantService
from app.schemas.common import DocumentChunk, IngestionRunSummary

logger = get_logger(__name__)


class IngestionPipeline:
    """Orchestrates discover -> parse -> clean -> chunk -> embed -> index."""

    def __init__(
        self,
        db: AsyncSession,
        qdrant: QdrantService,
        embedding_provider: EmbeddingProvider,
        settings: Settings | None = None,
        parser_registry: ParserRegistry | None = None,
    ) -> None:
        self.db = db
        self.qdrant = qdrant
        self.embedding_provider = embedding_provider
        self.settings = settings or get_settings()
        self.parser_registry = parser_registry or default_parser_registry
        self.ingestion_config = self.settings.ingestion_config.get("ingestion", {})

    async def run(self, source: DocumentSource) -> IngestionRunSummary:
        """Execute a full ingestion run for the given document source."""
        run = IngestionRun(
            id=generate_uuid(),
            status=IngestionRunStatus.RUNNING.value,
            source=source.source_name,
            started_at=datetime.now(tz=UTC),
        )
        self.db.add(run)
        await self.db.flush()

        stats = {
            "documents_discovered": 0,
            "documents_new": 0,
            "documents_modified": 0,
            "documents_unchanged": 0,
            "documents_deleted": 0,
            "documents_failed": 0,
            "chunks_indexed": 0,
            "chunks_removed": 0,
        }

        try:
            discovered = await self._run_step(run, "discover", self._discover, source)
            stats["documents_discovered"] = len(discovered)

            existing_documents = await self._load_existing_documents(source.source_name)
            active_changes, deleted_changes = detect_changes(discovered, existing_documents)

            for change in active_changes:
                if change.status == DocumentStatus.UNCHANGED:
                    stats["documents_unchanged"] += 1
                    await self._mark_unchanged(change)
                    continue

                try:
                    chunks_indexed = await self._process_document(run, source, change)
                    stats["chunks_indexed"] += chunks_indexed
                    if change.status == DocumentStatus.NEW:
                        stats["documents_new"] += 1
                    elif change.status == DocumentStatus.MODIFIED:
                        stats["documents_modified"] += 1
                except Exception as exc:
                    stats["documents_failed"] += 1
                    await self._record_error(run, change, exc)
                    logger.exception(
                        "document_ingestion_failed",
                        stable_id=change.reference.stable_id,
                        error=str(exc),
                    )

            for change in deleted_changes:
                removed = await self._mark_deleted(change)
                stats["documents_deleted"] += 1
                stats["chunks_removed"] += removed

            run.status = (
                IngestionRunStatus.PARTIAL.value
                if stats["documents_failed"]
                else IngestionRunStatus.COMPLETED.value
            )
            run.health_status = "HEALTHY" if not stats["documents_failed"] else "DEGRADED"
        except Exception as exc:
            run.status = IngestionRunStatus.FAILED.value
            run.health_status = "FAILED"
            await self._record_error(run, None, exc)
            logger.exception("ingestion_run_failed", source=source.source_name, error=str(exc))
            raise
        finally:
            run.documents_discovered = stats["documents_discovered"]
            run.documents_new = stats["documents_new"]
            run.documents_modified = stats["documents_modified"]
            run.documents_unchanged = stats["documents_unchanged"]
            run.documents_deleted = stats["documents_deleted"]
            run.documents_failed = stats["documents_failed"]
            run.chunks_indexed = stats["chunks_indexed"]
            run.chunks_removed = stats["chunks_removed"]
            run.completed_at = datetime.now(tz=UTC)
            await self.db.flush()

        return IngestionRunSummary(
            id=run.id,
            status=run.status,
            source=run.source,
            documents_discovered=run.documents_discovered,
            documents_new=run.documents_new,
            documents_modified=run.documents_modified,
            documents_unchanged=run.documents_unchanged,
            documents_deleted=run.documents_deleted,
            chunks_indexed=run.chunks_indexed,
            health_status=run.health_status,
            started_at=run.started_at,
            completed_at=run.completed_at,
        )

    async def _run_step(self, run: IngestionRun, step_name: str, func: Any, *args: Any) -> Any:
        started = datetime.now(tz=UTC)
        step = IngestionStep(
            id=generate_uuid(),
            ingestion_run_id=run.id,
            step_name=step_name,
            status=IngestionRunStatus.RUNNING.value,
        )
        self.db.add(step)
        await self.db.flush()
        try:
            result = await func(*args)
            step.status = IngestionRunStatus.COMPLETED.value
            step.duration_ms = int((datetime.now(tz=UTC) - started).total_seconds() * 1000)
            step.details = {"count": len(result) if isinstance(result, list) else None}
            await self.db.flush()
            return result
        except Exception:
            step.status = IngestionRunStatus.FAILED.value
            step.duration_ms = int((datetime.now(tz=UTC) - started).total_seconds() * 1000)
            await self.db.flush()
            raise

    async def _discover(self, source: DocumentSource) -> list[Any]:
        return await source.discover()

    async def _load_existing_documents(self, source_name: str) -> list[Document]:
        result = await self.db.execute(
            select(Document).where(Document.source == source_name)
        )
        return list(result.scalars().all())

    async def _process_document(
        self,
        run: IngestionRun,
        source: DocumentSource,
        change: DocumentChange,
    ) -> int:
        raw = await source.fetch(change.reference)
        parsed = self.parser_registry.parse(raw)
        cleaned_text = clean_text(parsed.text)
        parsed.text = cleaned_text
        parsed.title = clean_text(parsed.title) or parsed.title

        hash_value = content_hash(cleaned_text)
        change = reconcile_content_hash(change, hash_value)
        if change.status == DocumentStatus.UNCHANGED:
            await self._mark_unchanged(change)
            return 0

        metadata = extract_metadata(change.reference, parsed)
        document = await self._upsert_document(change, parsed, metadata, hash_value)
        chunks = chunk_document(
            parsed,
            document_id=document.id,
            document_stable_id=document.stable_id,
            document_version=document.current_version,
            strategy=self.ingestion_config.get("chunk_strategy", "sentence_aware"),
            chunk_size=int(self.ingestion_config.get("chunk_size", 512)),
            chunk_overlap=int(self.ingestion_config.get("chunk_overlap", 64)),
            min_chunk_length=int(self.ingestion_config.get("min_chunk_length", 100)),
            preserve_headings=bool(self.ingestion_config.get("preserve_headings", True)),
        )

        if change.status == DocumentStatus.MODIFIED and change.existing_document:
            await self._deactivate_old_chunks(change.existing_document.id)
            await self.qdrant.delete_by_document_id(change.existing_document.id)

        indexed_count = await self._index_chunks(document, chunks)
        await self._create_document_version(document, change, hash_value, metadata)
        return indexed_count

    async def _upsert_document(
        self,
        change: DocumentChange,
        parsed: Any,
        metadata: dict[str, Any],
        hash_value: str,
    ) -> Document:
        now = datetime.now(tz=UTC)
        if change.existing_document:
            document = change.existing_document
            document.current_version += 1
            document.status = DocumentStatus.MODIFIED.value
        else:
            document = Document(
                id=generate_uuid(),
                stable_id=change.reference.stable_id,
                filename=change.reference.filename,
                title=parsed.title,
                document_type=infer_document_type(change.reference.filename),
                source=change.reference.source,
                source_url=change.reference.source_url,
                current_version=1,
                status=DocumentStatus.NEW.value,
            )
            self.db.add(document)

        document.title = parsed.title
        document.checksum = change.reference.checksum
        document.content_hash = hash_value
        document.chunk_count = 0
        document.is_deleted = False
        document.last_indexed_at = now
        document.status = DocumentStatus.INDEXED.value
        if metadata.get("department"):
            document.department = str(metadata["department"])
        await self.db.flush()
        return document

    async def _index_chunks(self, document: Document, chunks: list[DocumentChunk]) -> int:
        if not chunks:
            document.chunk_count = 0
            await self.db.flush()
            return 0

        batch_size = int(self.ingestion_config.get("batch_size", 32))
        indexed = 0
        await self.qdrant.ensure_collection(self.embedding_provider.vector_size)

        for start in range(0, len(chunks), batch_size):
            batch = chunks[start : start + batch_size]
            vectors = await self.embedding_provider.embed_texts([chunk.content for chunk in batch])
            points: list[dict[str, Any]] = []
            for chunk, vector in zip(batch, vectors, strict=True):
                point_id = QdrantService.point_id_from_chunk(chunk.chunk_id)
                db_chunk = Chunk(
                    id=generate_uuid(),
                    document_id=document.id,
                    document_version=document.current_version,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    content_hash=chunk.content_hash,
                    token_count=chunk.token_count,
                    section=chunk.section,
                    page_number=chunk.page_number,
                    chunk_strategy=self.ingestion_config.get("chunk_strategy", "sentence_aware"),
                    embedding_model=self.embedding_provider.model_name,
                    embedded_at=datetime.now(tz=UTC),
                    qdrant_point_id=point_id,
                    metadata_json=chunk.metadata,
                    is_active=True,
                )
                self.db.add(db_chunk)
                points.append(
                    {
                        "point_id": point_id,
                        "vector": vector,
                        "payload": {
                            "chunk_id": db_chunk.id,
                            "document_id": document.id,
                            "document_stable_id": document.stable_id,
                            "document_title": document.title,
                            "filename": document.filename,
                            "document_version": document.current_version,
                            "chunk_index": chunk.chunk_index,
                            "content": chunk.content,
                            "section": chunk.section,
                            "page_number": chunk.page_number,
                            "source": document.source,
                            "source_url": document.source_url,
                            "document_type": document.document_type,
                            "department": document.department,
                            "allowed_groups": document.allowed_groups or [],
                        },
                    }
                )
            await self.qdrant.upsert_vectors(points)
            indexed += len(batch)

        document.chunk_count = indexed
        await self.db.flush()
        return indexed

    async def _create_document_version(
        self,
        document: Document,
        change: DocumentChange,
        hash_value: str,
        metadata: dict[str, Any],
    ) -> None:
        version = DocumentVersion(
            id=generate_uuid(),
            document_id=document.id,
            version=document.current_version,
            content_hash=hash_value,
            checksum=document.checksum or change.reference.checksum,
            status=change.status.value,
            source=document.source,
            metadata_json=metadata,
            indexed_at=datetime.now(tz=UTC),
        )
        self.db.add(version)
        await self.db.flush()

    async def _deactivate_old_chunks(self, document_id: str) -> int:
        result = await self.db.execute(
            select(Chunk).where(Chunk.document_id == document_id, Chunk.is_active.is_(True))
        )
        chunks = list(result.scalars().all())
        for chunk in chunks:
            chunk.is_active = False
        await self.db.flush()
        return len(chunks)

    async def _mark_unchanged(self, change: DocumentChange) -> None:
        if not change.existing_document:
            return
        document = change.existing_document
        document.status = DocumentStatus.UNCHANGED.value
        document.checksum = change.reference.checksum
        await self.db.flush()

    async def _mark_deleted(self, change: DocumentChange) -> int:
        if not change.existing_document:
            return 0
        document = change.existing_document
        document.is_deleted = True
        document.status = DocumentStatus.DELETED.value
        removed = await self._deactivate_old_chunks(document.id)
        await self.qdrant.delete_by_document_id(document.id)
        return removed

    async def _record_error(
        self,
        run: IngestionRun,
        change: DocumentChange | None,
        exc: Exception,
    ) -> None:
        document_id = None
        if change and change.existing_document:
            document_id = change.existing_document.id
        elif change:
            document_id = change.reference.metadata.get("document_id")

        error = IngestionError(
            id=generate_uuid(),
            ingestion_run_id=run.id,
            document_id=document_id,
            error_type=exc.__class__.__name__,
            message=str(exc),
        )
        self.db.add(error)
        if isinstance(exc, DocumentProcessingError) and change and change.existing_document:
            change.existing_document.status = DocumentStatus.FAILED.value
        await self.db.flush()
