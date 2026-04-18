from __future__ import annotations

from backend.layer2.llm.openai_client import OpenAICompatibleClient


class GroqClient(OpenAICompatibleClient):
    """Groq exposes an OpenAI-compatible API surface."""
