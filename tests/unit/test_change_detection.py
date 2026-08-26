"""Tests for document change detection."""

from app.core.constants import DocumentStatus
from app.db.models import Document
from app.ingestion.change_detection import detect_changes, reconcile_content_hash
from app.schemas.common import DocumentReference


def _reference(stable_id: str, checksum: str) -> DocumentReference:
    return DocumentReference(
        stable_id=stable_id,
        filename=f"{stable_id}.md",
        source="demo",
        checksum=checksum,
    )


def _document(stable_id: str, checksum: str, content_hash: str | None = None) -> Document:
    return Document(
        id=f"id-{stable_id}",
        stable_id=stable_id,
        filename=f"{stable_id}.md",
        title=stable_id,
        document_type="markdown",
        source="demo",
        checksum=checksum,
        content_hash=content_hash,
    )


def test_detect_new_documents() -> None:
    discovered = [_reference("doc-a", "checksum-a")]
    active, deleted = detect_changes(discovered, [])
    assert len(active) == 1
    assert active[0].status == DocumentStatus.NEW
    assert deleted == []


def test_detect_unchanged_by_checksum() -> None:
    discovered = [_reference("doc-a", "checksum-a")]
    existing = [_document("doc-a", "checksum-a", "hash-a")]
    active, deleted = detect_changes(discovered, existing)
    assert active[0].status == DocumentStatus.UNCHANGED
    assert deleted == []


def test_detect_modified_checksum() -> None:
    discovered = [_reference("doc-a", "checksum-new")]
    existing = [_document("doc-a", "checksum-old", "hash-old")]
    active, _ = detect_changes(discovered, existing)
    assert active[0].status == DocumentStatus.MODIFIED


def test_detect_deleted_documents() -> None:
    existing = [_document("doc-a", "checksum-a")]
    active, deleted = detect_changes([], existing)
    assert active == []
    assert len(deleted) == 1
    assert deleted[0].status == DocumentStatus.DELETED


def test_reconcile_content_hash_downgrades_modified_to_unchanged() -> None:
    from app.ingestion.change_detection import DocumentChange

    change = DocumentChange(
        reference=_reference("doc-a", "new-checksum"),
        status=DocumentStatus.MODIFIED,
        existing_document=_document("doc-a", "old-checksum", "same-hash"),
        previous_content_hash="same-hash",
    )
    result = reconcile_content_hash(change, "same-hash")
    assert result.status == DocumentStatus.UNCHANGED
