"""Application configuration."""

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "KnowledgeOps RAG Platform"
    app_env: str = "development"
    debug: bool = False
    log_level: str = "INFO"
    secret_key: str = "change-me"

    database_url: str = "postgresql+asyncpg://knowledgeops:knowledgeops@localhost:15432/knowledgeops"
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "knowledgeops_chunks"

    embedding_provider: str = "local"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    generation_provider: str = "mock"
    reranking_provider: str = "local"
    evaluation_provider: str = "local"

    openai_api_key: str = ""
    anthropic_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"

    demo_knowledge_path: str = "demo_knowledge"
    ingestion_config_path: str = "config/ingestion.yaml"
    retrieval_config_path: str = "config/retrieval.yaml"
    default_user_group: str = "ENGINEERING"

    embedding_cost_per_1k_tokens: float = 0.0
    generation_input_cost_per_1k_tokens: float = 0.0
    generation_output_cost_per_1k_tokens: float = 0.0

    project_root: Path = Field(default_factory=lambda: Path(__file__).resolve().parents[2])

    def load_yaml_config(self, path: str | Path) -> dict[str, Any]:
        config_path = Path(path)
        if not config_path.is_absolute():
            config_path = self.project_root / config_path
        if not config_path.exists():
            return {}
        with config_path.open(encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    @property
    def ingestion_config(self) -> dict[str, Any]:
        return self.load_yaml_config(self.ingestion_config_path)

    @property
    def retrieval_config(self) -> dict[str, Any]:
        return self.load_yaml_config(self.retrieval_config_path)


@lru_cache
def get_settings() -> Settings:
    return Settings()
