"""Local cross-encoder reranking provider."""

from typing import cast

import asyncio
from functools import lru_cache

from sentence_transformers import CrossEncoder

from app.core.exceptions import ProviderError
from app.core.logging import get_logger
from app.providers.base import RerankingProvider

logger = get_logger(__name__)

DEFAULT_RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"


@lru_cache(maxsize=4)
def _load_cross_encoder(model_name: str) -> CrossEncoder:
    return cast(CrossEncoder, CrossEncoder(model_name))


class LocalRerankerProvider(RerankingProvider):
    """Reranks passages with a local cross-encoder model."""

    def __init__(self, model_name: str = DEFAULT_RERANK_MODEL) -> None:
        self._model_name = model_name
        try:
            self._model = _load_cross_encoder(model_name)
        except Exception as exc:
            raise ProviderError(f"Failed to load reranker model: {exc}", provider="local") from exc

    @property
    def model_name(self) -> str:
        return self._model_name

    async def rerank(
        self,
        query: str,
        documents: list[str],
    ) -> list[tuple[int, float]]:
        if not documents:
            return []

        pairs = [(query, doc) for doc in documents]
        scores = await asyncio.to_thread(
            lambda: self._model.predict(pairs, show_progress_bar=False),
        )

        ranked = sorted(
            ((idx, float(score)) for idx, score in enumerate(scores)),
            key=lambda item: item[1],
            reverse=True,
        )
        return ranked
