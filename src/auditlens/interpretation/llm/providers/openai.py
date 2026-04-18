from __future__ import annotations

from auditlens.exceptions import Layer2ProviderError
from auditlens.interpretation.llm.base import BaseLLMClient


def _openai_client_cls():  # lazy import for optional extra
    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover - exercised via extras
        raise ImportError(
            "OpenAI support requires the 'openai' SDK. Install with: pip install auditlens[openai]"
        ) from exc
    return OpenAI


class OpenAICompatibleClient(BaseLLMClient):
    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str,
        timeout_seconds: float,
        default_headers: dict[str, str] | None = None,
    ) -> None:
        OpenAI = _openai_client_cls()
        self._model = model
        self._client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout_seconds,
            default_headers=default_headers,
        )

    @staticmethod
    def _extract_content(response: object) -> str:
        choices = getattr(response, "choices", None)
        if not choices:
            raise Layer2ProviderError("LLM provider returned empty response")

        first_choice = choices[0]
        message = getattr(first_choice, "message", None)
        content = getattr(message, "content", "") if message is not None else ""
        if not content:
            raise Layer2ProviderError("LLM provider returned empty response")
        return content

    def complete_json(self, prompt: str) -> str:
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
            )
            return self._extract_content(response)
        except Layer2ProviderError:
            raise
        except Exception:
            # Some OpenAI-compatible providers/models reject response_format=json_object.
            try:
                fallback_response = self._client.chat.completions.create(
                    model=self._model,
                    messages=[{"role": "user", "content": prompt}],
                )
                return self._extract_content(fallback_response)
            except Layer2ProviderError:
                raise
            except Exception as exc:  # pragma: no cover - external provider behavior
                detail = str(exc).strip() or exc.__class__.__name__
                raise Layer2ProviderError(f"LLM provider request failed: {detail}") from exc
