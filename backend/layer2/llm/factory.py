from __future__ import annotations

from backend.layer2.errors import Layer2ConfigurationError
from backend.layer2.llm.base import BaseLLMClient
from backend.layer2.llm.groq_client import GroqClient
from backend.layer2.llm.openai_client import OpenAICompatibleClient
from backend.layer2.llm.openrouter_client import OpenRouterClient
from backend.utils.config import Layer2ConfigurationError as ConfigError
from backend.utils.config import get_layer2_settings


def create_provider_client() -> BaseLLMClient:
    try:
        settings = get_layer2_settings()
    except ConfigError as exc:
        raise Layer2ConfigurationError(str(exc)) from exc

    if settings.provider == "openai":
        return OpenAICompatibleClient(
            api_key=settings.api_key,
            model=settings.model,
            base_url=settings.base_url,
            timeout_seconds=settings.timeout_seconds,
        )
    if settings.provider == "groq":
        return GroqClient(
            api_key=settings.api_key,
            model=settings.model,
            base_url=settings.base_url,
            timeout_seconds=settings.timeout_seconds,
        )
    if settings.provider == "openrouter":
        return OpenRouterClient(
            api_key=settings.api_key,
            model=settings.model,
            base_url=settings.base_url,
            timeout_seconds=settings.timeout_seconds,
        )
    raise Layer2ConfigurationError(f"Unsupported provider: {settings.provider}")
