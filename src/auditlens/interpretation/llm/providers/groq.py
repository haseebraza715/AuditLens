from __future__ import annotations

from auditlens.interpretation.llm.providers.openai import OpenAICompatibleClient


class GroqClient(OpenAICompatibleClient):
    """Groq exposes an OpenAI-compatible API surface."""
