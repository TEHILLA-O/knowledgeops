"""Document change detection for ingestion runs."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.constants import DocumentStatus
from app.db.models.base import Document
from app.schemas.common import DocumentReference


@dataclass
class DocumentChange:
    """Represents the detected status of a document during ingestion."""

    reference: DocumentReference
    status: DocumentStatus
    existing_document: Document | None = None
    previous_content_hash: str | None = None
    new_content_hash: str | None = None


def detect_changes(
    discovered: list[DocumentReference],
    existing_documents: list[Document],
) -> tuple[list[DocumentChange], list[DocumentChange]]:
    """
    Compare discovered references against indexed documents.

    Returns a tuple of (active_changes, deleted_changes).
    Active changes include NEW, UNCHANGED, and MODIFIED documents.
    Deleted changes represent documents present in the index but missing from discovery.
    """
    existing_by_stable_id = {
        document.stable_id: document
        for document in existing_documents
        if not document.is_deleted
    }
    discovered_ids = {reference.stable_id for reference in discovered}

    active_changes: list[DocumentChange] = []
    for reference in discovered:
        existing = existing_by_stable_id.get(reference.stable_id)
        if existing is None:
            active_changes.append(
                DocumentChange(
                    reference=reference,
                    status=DocumentStatus.NEW,
                )
            )
            continue

        if existing.checksum and existing.checksum == reference.checksum:
            active_changes.append(
                DocumentChange(
                    reference=reference,
                    status=DocumentStatus.UNCHANGED,
                    existing_document=existing,
                    previous_content_hash=existing.content_hash,
                )
            )
        else:
            active_changes.append(
                DocumentChange(
                    reference=reference,
                    status=DocumentStatus.MODIFIED,
                    existing_document=existing,
                    previous_content_hash=existing.content_hash,
                )
            )

    deleted_changes: list[DocumentChange] = []
    for stable_id, existing in existing_by_stable_id.items():
        if stable_id not in discovered_ids:
            deleted_changes.append(
                DocumentChange(
                    reference=DocumentReference(
                        stable_id=existing.stable_id,
                        filename=existing.filename,
                        source=existing.source,
                        source_url=existing.source_url,
                        checksum=existing.checksum or "",
                        metadata={"document_id": existing.id},
                    ),
                    status=DocumentStatus.DELETED,
                    existing_document=existing,
                    previous_content_hash=existing.content_hash,
                )
            )

    return active_changes, deleted_changes


def reconcile_content_hash(change: DocumentChange, content_hash_value: str) -> DocumentChange:
    """
    Refine MODIFIED vs UNCHANGED using parsed content hashes.

    If checksum changed but cleaned content hash is identical, treat as UNCHANGED.
    """
    change.new_content_hash = content_hash_value
    if (
        change.status == DocumentStatus.MODIFIED
        and change.previous_content_hash
        and change.previous_content_hash == content_hash_value
    ):
        change.status = DocumentStatus.UNCHANGED
    return change
