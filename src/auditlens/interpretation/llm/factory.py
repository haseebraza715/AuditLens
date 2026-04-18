from __future__ import annotations

from auditlens.config import get_layer2_settings
from auditlens.exceptions import Layer2ConfigurationError
from auditlens.interpretation.llm.base import BaseLLMClient


def create_provider_client() -> BaseLLMClient:
    try:
        settings = get_layer2_settings()
    except Layer2ConfigurationError as exc:
        raise Layer2ConfigurationError(str(exc)) from exc

    if settings.provider == "openai":
        from auditlens.interpretation.llm.providers.openai import OpenAICompatibleClient

        return OpenAICompatibleClient(
            api_key=settings.api_key,
            model=settings.model,
            base_url=settings.base_url,
            timeout_seconds=settings.timeout_seconds,
        )
    if settings.provider == "groq":
        from auditlens.interpretation.llm.providers.groq import GroqClient

        return GroqClient(
            api_key=settings.api_key,
            model=settings.model,
            base_url=settings.base_url,
            timeout_seconds=settings.timeout_seconds,
        )
    if settings.provider == "openrouter":
        from auditlens.interpretation.llm.providers.openrouter import OpenRouterClient

        return OpenRouterClient(
            api_key=settings.api_key,
            model=settings.model,
            base_url=settings.base_url,
            timeout_seconds=settings.timeout_seconds,
        )
    raise Layer2ConfigurationError(f"Unsupported provider: {settings.provider}")
