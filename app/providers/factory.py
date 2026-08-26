"""Factory for creating provider instances from application settings."""

from app.core.config import Settings, get_settings
from app.core.exceptions import ConfigurationError
from app.providers.base import (
    EmbeddingProvider,
    EvaluationProvider,
    GenerationProvider,
    RerankingProvider,
)
from app.providers.local_embedding import LocalEmbeddingProvider
from app.providers.local_reranker import DEFAULT_RERANK_MODEL, LocalRerankerProvider
from app.providers.mock_embedding import MockEmbeddingProvider


class LocalEvaluationProvider(EvaluationProvider):
    """Placeholder local evaluator for development."""

    @property
    def provider_name(self) -> str:
        return "local"

    async def evaluate(
        self,
        question: str,
        answer: str,
        contexts: list[str],
        ground_truth: str | None = None,
    ) -> dict[str, object]:
        del question, answer, contexts, ground_truth
        return {"status": "not_implemented"}


def create_embedding_provider(settings: Settings | None = None) -> EmbeddingProvider:
    settings = settings or get_settings()
    provider = settings.embedding_provider.lower()
    if provider == "local":
        return LocalEmbeddingProvider(model_name=settings.embedding_model)
    if provider == "mock":
        return MockEmbeddingProvider()
    raise ConfigurationError(f"Unsupported embedding provider: {provider}")


def create_reranking_provider(settings: Settings | None = None) -> RerankingProvider | None:
    settings = settings or get_settings()
    retrieval_cfg = settings.retrieval_config.get("retrieval", {})
    if not retrieval_cfg.get("enable_reranking", True):
        return None

    provider = settings.reranking_provider.lower()
    if provider == "local":
        model = settings.retrieval_config.get("reranking", {}).get("model", DEFAULT_RERANK_MODEL)
        return LocalRerankerProvider(model_name=model)
    if provider == "none":
        return None
    raise ConfigurationError(f"Unsupported reranking provider: {provider}")


def create_generation_provider(settings: Settings | None = None) -> GenerationProvider:
    settings = settings or get_settings()
    provider = settings.generation_provider.lower()

    if provider == "mock":
        from app.generation.providers.mock import MockGenerationProvider

        return MockGenerationProvider()
    if provider == "ollama":
        from app.generation.providers.ollama import OllamaGenerationProvider

        return OllamaGenerationProvider(base_url=settings.ollama_base_url)
    raise ConfigurationError(f"Unsupported generation provider: {provider}")


def create_evaluation_provider(settings: Settings | None = None) -> EvaluationProvider:
    settings = settings or get_settings()
    provider = settings.evaluation_provider.lower()
    if provider == "local":
        return LocalEvaluationProvider()
    raise ConfigurationError(f"Unsupported evaluation provider: {provider}")
