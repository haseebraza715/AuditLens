from __future__ import annotations

from openai import OpenAI

from backend.layer2.errors import Layer2ProviderError
from backend.layer2.llm.base import BaseLLMClient


class OpenAICompatibleClient(BaseLLMClient):
    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str,
        timeout_seconds: float,
    ) -> None:
        self._model = model
        self._client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout_seconds)

    def complete_json(self, prompt: str) -> str:
        try:
            response = self._client.responses.create(
                model=self._model,
                input=prompt,
                response_format={"type": "json_object"},
            )
            return response.output_text
        except Exception as exc:  # pragma: no cover - external provider behavior
            raise Layer2ProviderError("LLM provider request failed") from exc
