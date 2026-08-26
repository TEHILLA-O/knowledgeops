"""Mock generation provider for demos and testing."""

import re

from app.core.constants import ConfidenceLevel
from app.generation.prompts import sanitize_user_input
from app.providers.base import GenerationProvider
from app.schemas.common import GenerationResult, Message

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


class MockGenerationProvider(GenerationProvider):
    """Produces extractive answers by matching query terms against context."""

    @property
    def provider_name(self) -> str:
        return "mock"

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        messages: list[Message] | None = None,
    ) -> GenerationResult:
        del system_prompt, messages
        context, query = self._parse_user_prompt(user_prompt)
        safe_query = sanitize_user_input(query)

        if not context.strip():
            return GenerationResult(
                answer="I do not have sufficient evidence to answer this question.",
                confidence_score=0.0,
                confidence_level=ConfidenceLevel.INSUFFICIENT_EVIDENCE,
                knowledge_gap=True,
            )

        answer = self._extractive_answer(safe_query, context)
        has_evidence = answer != "I do not have sufficient evidence to answer this question."
        score = 0.72 if has_evidence else 0.2

        return GenerationResult(
            answer=answer,
            confidence_score=score,
            confidence_level=ConfidenceLevel.MEDIUM if has_evidence else ConfidenceLevel.INSUFFICIENT_EVIDENCE,
            knowledge_gap=not has_evidence,
            input_tokens=len(user_prompt.split()),
            output_tokens=len(answer.split()),
            metadata={"provider": self.provider_name, "mode": "extractive"},
        )

    @staticmethod
    def _parse_user_prompt(user_prompt: str) -> tuple[str, str]:
        context = ""
        query = user_prompt
        if "<context>" in user_prompt and "</context>" in user_prompt:
            start = user_prompt.index("<context>") + len("<context>")
            end = user_prompt.index("</context>")
            context = user_prompt[start:end].strip()
            remainder = user_prompt[end + len("</context>") :].strip()
            if remainder.lower().startswith("question:"):
                query = remainder[len("question:") :].strip()
            else:
                query = remainder
        return context, query

    def _extractive_answer(self, query: str, context: str) -> str:
        query_terms = {t.lower() for t in re.findall(r"\w+", query) if len(t) > 2}
        if not query_terms:
            return "I do not have sufficient evidence to answer this question."

        best_sentences: list[str] = []
        best_score = 0
        for block in context.split("\n\n"):
            lines = block.splitlines()
            body = "\n".join(lines[1:]) if len(lines) > 1 else block
            for sentence in _SENTENCE_SPLIT.split(body):
                sentence = sentence.strip()
                if len(sentence) < 20:
                    continue
                terms = {t.lower() for t in re.findall(r"\w+", sentence)}
                overlap = len(query_terms & terms)
                if overlap > best_score:
                    best_score = overlap
                    best_sentences = [sentence]
                elif overlap == best_score and overlap > 0:
                    best_sentences.append(sentence)

        if best_score == 0:
            return "I do not have sufficient evidence to answer this question."

        answer = " ".join(best_sentences[:3])
        if not answer.endswith("."):
            answer += "."
        return answer
