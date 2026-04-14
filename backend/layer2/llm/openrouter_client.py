from __future__ import annotations

import os

from backend.layer2.llm.openai_client import OpenAICompatibleClient


class OpenRouterClient(OpenAICompatibleClient):
    """OpenRouter exposes an OpenAI-compatible API surface."""

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str,
        timeout_seconds: float,
    ) -> None:
        headers: dict[str, str] = {}
        app_url = os.getenv("OPENROUTER_APP_URL", "").strip()
        app_title = os.getenv("OPENROUTER_APP_TITLE", "").strip()
        if app_url:
            headers["HTTP-Referer"] = app_url
        if app_title:
            headers["X-Title"] = app_title

        super().__init__(
            api_key=api_key,
            model=model,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
            default_headers=headers or None,
        )
