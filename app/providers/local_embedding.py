"""Local sentence-transformers embedding provider."""

from typing import cast

import asyncio
from functools import lru_cache

from sentence_transformers import SentenceTransformer

from app.core.constants import QDRANT_VECTOR_SIZE
from app.core.exceptions import ProviderError
from app.core.logging import get_logger
from app.providers.base import EmbeddingProvider

logger = get_logger(__name__)


@lru_cache(maxsize=4)
def _load_model(model_name: str) -> SentenceTransformer:
    return SentenceTransformer(model_name)


class LocalEmbeddingProvider(EmbeddingProvider):
    """Embeds text using a local sentence-transformers model."""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> None:
        self._model_name = model_name
        try:
            self._model = _load_model(model_name)
        except Exception as exc:
            raise ProviderError(f"Failed to load embedding model: {exc}", provider="local") from exc

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def vector_size(self) -> int:
        dim = self._model.get_sentence_embedding_dimension()
        return dim if dim is not None else QDRANT_VECTOR_SIZE

    async def embed_text(self, text: str) -> list[float]:
        if not text.strip():
            raise ProviderError("Cannot embed empty text", provider="local")
        vector = await asyncio.to_thread(
            self._model.encode,
            text,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return cast(list[float], vector.tolist())

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors = await asyncio.to_thread(
            self._model.encode,
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return [v.tolist() for v in vectors]
