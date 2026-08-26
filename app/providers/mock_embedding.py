"""Deterministic mock embedding provider for tests and CI."""

from __future__ import annotations

import hashlib
import math

from app.core.constants import QDRANT_VECTOR_SIZE
from app.providers.base import EmbeddingProvider


class MockEmbeddingProvider(EmbeddingProvider):
    """Produces deterministic normalized vectors from text hashes."""

    def __init__(self, vector_size: int = QDRANT_VECTOR_SIZE, model_name: str = "mock-embedding") -> None:
        self._vector_size = vector_size
        self._model_name = model_name

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def vector_size(self) -> int:
        return self._vector_size

    def _hash_to_vector(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        values: list[float] = []
        while len(values) < self._vector_size:
            for byte in digest:
                values.append((byte / 127.5) - 1.0)
                if len(values) >= self._vector_size:
                    break
            digest = hashlib.sha256(digest).digest()
        norm = math.sqrt(sum(v * v for v in values)) or 1.0
        return [v / norm for v in values]

    async def embed_text(self, text: str) -> list[float]:
        return self._hash_to_vector(text)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self._hash_to_vector(text) for text in texts]
