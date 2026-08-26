"""Ollama generation provider."""

import httpx

from app.core.constants import ConfidenceLevel
from app.core.exceptions import ProviderError
from app.core.logging import get_logger
from app.providers.base import GenerationProvider
from app.schemas.common import GenerationResult, Message

logger = get_logger(__name__)


class OllamaGenerationProvider(GenerationProvider):
    """Generates answers via a local Ollama HTTP API."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3.2",
        timeout: float = 120.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    @property
    def provider_name(self) -> str:
        return "ollama"

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        messages: list[Message] | None = None,
    ) -> GenerationResult:
        chat_messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
        if messages:
            chat_messages.extend({"role": m.role, "content": m.content} for m in messages)
        chat_messages.append({"role": "user", "content": user_prompt})

        payload = {
            "model": self.model,
            "messages": chat_messages,
            "stream": False,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(f"{self.base_url}/api/chat", json=payload)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as exc:
            raise ProviderError(f"Ollama request failed: {exc}", provider="ollama") from exc

        message = data.get("message", {})
        answer = str(message.get("content", "")).strip()
        if not answer:
            raise ProviderError("Ollama returned empty response", provider="ollama")

        prompt_tokens = int(data.get("prompt_eval_count", len(user_prompt.split())))
        output_tokens = int(data.get("eval_count", len(answer.split())))

        return GenerationResult(
            answer=answer,
            confidence_score=0.65,
            confidence_level=ConfidenceLevel.MEDIUM,
            knowledge_gap=False,
            input_tokens=prompt_tokens,
            output_tokens=output_tokens,
            metadata={"provider": self.provider_name, "model": self.model},
        )
