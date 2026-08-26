"""Tests for text cleaning."""

from app.ingestion.cleaning.text_cleaner import (
    clean_text,
    collapse_whitespace,
    normalize_unicode,
    remove_control_characters,
    standardize_bullets,
)


def test_normalize_unicode() -> None:
    assert normalize_unicode("café") == "café"


def test_remove_control_characters() -> None:
    assert remove_control_characters("hello\x00world") == "helloworld"


def test_standardize_bullets() -> None:
    assert standardize_bullets("• item") == "- item"


def test_collapse_whitespace() -> None:
    assert collapse_whitespace("hello   world\n\n\n\ntest") == "hello world\n\ntest"


def test_clean_text_pipeline() -> None:
    dirty = "  Hello\x00  world.  \n\n\n• Bullet  "
    cleaned = clean_text(dirty)
    assert "\x00" not in cleaned
    assert "•" not in cleaned
    assert cleaned.startswith("Hello")
