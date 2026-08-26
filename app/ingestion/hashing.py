"""Checksum and content hash utilities."""

from __future__ import annotations

import hashlib


def checksum_bytes(data: bytes) -> str:
    """Return a SHA-256 checksum for raw file bytes."""
    return hashlib.sha256(data).hexdigest()


def content_hash(text: str) -> str:
    """Return a SHA-256 hash for normalized document text content."""
    normalized = text.strip().encode("utf-8")
    return hashlib.sha256(normalized).hexdigest()


def stable_id(source: str, path: str) -> str:
    """Derive a deterministic document identifier from source and path."""
    key = f"{source}::{path}".lower().encode("utf-8")
    return hashlib.sha256(key).hexdigest()


def chunk_content_hash(document_stable_id: str, chunk_index: int, content: str) -> str:
    """Return a stable hash for an individual chunk."""
    key = f"{document_stable_id}:{chunk_index}:{content.strip()}".encode()
    return hashlib.sha256(key).hexdigest()
