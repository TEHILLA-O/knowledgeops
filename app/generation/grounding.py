"""Grounding checks for generated answers."""

import re

from app.schemas.common import RetrievedChunk

_WORD_PATTERN = re.compile(r"\w+")


def _tokenize(text: str) -> set[str]:
    return {t.lower() for t in _WORD_PATTERN.findall(text) if len(t) > 2}


def grounding_score(answer: str, context_chunks: list[RetrievedChunk]) -> float:
    """Compute lexical overlap between answer and retrieved context."""
    if not answer.strip() or not context_chunks:
        return 0.0

    answer_terms = _tokenize(answer)
    if not answer_terms:
        return 0.0

    context_terms: set[str] = set()
    for chunk in context_chunks:
        context_terms |= _tokenize(chunk.content)

    if not context_terms:
        return 0.0

    overlap = len(answer_terms & context_terms)
    return overlap / len(answer_terms)


def is_answer_grounded(
    answer: str,
    context_chunks: list[RetrievedChunk],
    min_score: float = 0.25,
) -> bool:
    """Return True when the answer appears supported by retrieved context."""
    insufficient_phrases = (
        "do not have sufficient evidence",
        "insufficient evidence",
        "cannot answer",
        "don't know",
        "do not know",
    )
    lower = answer.lower()
    if any(phrase in lower for phrase in insufficient_phrases):
        return True
    return grounding_score(answer, context_chunks) >= min_score


def unsupported_claims(answer: str, context_chunks: list[RetrievedChunk]) -> list[str]:
    """Identify answer sentences with low context support."""
    sentences = re.split(r"(?<=[.!?])\s+", answer.strip())
    context_text = " ".join(c.content for c in context_chunks)
    context_terms = _tokenize(context_text)
    unsupported: list[str] = []
    for sentence in sentences:
        terms = _tokenize(sentence)
        if not terms:
            continue
        support = len(terms & context_terms) / len(terms)
        if support < 0.2 and len(sentence) > 30:
            unsupported.append(sentence)
    return unsupported
