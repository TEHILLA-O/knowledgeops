"""Tests for hashing utilities."""

from app.ingestion.hashing import checksum_bytes, chunk_content_hash, content_hash, stable_id


def test_checksum_bytes_deterministic() -> None:
    data = b"hello world"
    assert checksum_bytes(data) == checksum_bytes(data)
    assert len(checksum_bytes(data)) == 64


def test_content_hash_normalizes_whitespace() -> None:
    assert content_hash("  hello  ") == content_hash("hello")


def test_stable_id_deterministic() -> None:
    id1 = stable_id("demo", "hr/handbook.md")
    id2 = stable_id("demo", "hr/handbook.md")
    id3 = stable_id("demo", "hr/policy.md")
    assert id1 == id2
    assert id1 != id3


def test_chunk_content_hash_includes_index() -> None:
    h1 = chunk_content_hash("doc-1", 0, "content")
    h2 = chunk_content_hash("doc-1", 1, "content")
    assert h1 != h2
