"""Abstract provider interfaces for embeddings, generation, reranking, and evaluation."""

from abc import ABC, abstractmethod
from typing import Any

from app.schemas.common import GenerationResult, Message


class EmbeddingProvider(ABC):
    """Embeds text into dense vectors."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Human-readable model identifier."""

    @property
    @abstractmethod
    def vector_size(self) -> int:
        """Output embedding dimension."""

    @abstractmethod
    async def embed_text(self, text: str) -> list[float]:
        """Embed a single text string."""

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts in one call."""

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Alias for embed_batch used by the ingestion pipeline."""
        return await self.embed_batch(texts)


class GenerationProvider(ABC):
    """Generates answers from prompts and context."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Provider identifier (e.g. mock, ollama, openai)."""

    @abstractmethod
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        messages: list[Message] | None = None,
    ) -> GenerationResult:
        """Generate an answer from system and user prompts."""


class RerankingProvider(ABC):
    """Reranks candidate passages for a query."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Human-readable reranker model identifier."""

    @abstractmethod
    async def rerank(
        self,
        query: str,
        documents: list[str],
    ) -> list[tuple[int, float]]:
        """Return (original_index, score) pairs sorted by descending relevance."""


class EvaluationProvider(ABC):
    """Evaluates RAG quality metrics."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Evaluator identifier."""

    @abstractmethod
    async def evaluate(
        self,
        question: str,
        answer: str,
        contexts: list[str],
        ground_truth: str | None = None,
    ) -> dict[str, Any]:
        """Run evaluation and return metric scores."""
