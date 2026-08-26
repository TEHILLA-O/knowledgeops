"""Deterministic text cleaning utilities."""

from __future__ import annotations

import re
import unicodedata

WHITESPACE_PATTERN = re.compile(r"[ \t]+")
MULTI_NEWLINE_PATTERN = re.compile(r"\n{3,}")
CONTROL_CHARS_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
BULLET_PATTERN = re.compile(r"[•●▪◦]")


def normalize_unicode(text: str) -> str:
    """Normalize unicode characters to a consistent form."""
    return unicodedata.normalize("NFKC", text)


def collapse_whitespace(text: str) -> str:
    """Collapse repeated spaces and normalize line endings."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = WHITESPACE_PATTERN.sub(" ", text)
    text = MULTI_NEWLINE_PATTERN.sub("\n\n", text)
    return text.strip()


def remove_control_characters(text: str) -> str:
    """Remove non-printable control characters."""
    return CONTROL_CHARS_PATTERN.sub("", text)


def standardize_bullets(text: str) -> str:
    """Normalize bullet characters to a single style."""
    return BULLET_PATTERN.sub("-", text)


def clean_text(text: str) -> str:
    """Apply the full deterministic cleaning pipeline to document text."""
    if not text:
        return ""
    cleaned = normalize_unicode(text)
    cleaned = remove_control_characters(cleaned)
    cleaned = standardize_bullets(cleaned)
    cleaned = collapse_whitespace(cleaned)
    return cleaned
