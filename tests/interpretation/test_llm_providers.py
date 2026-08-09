"""LLM provider factory and OpenAI-compatible client tests (fully offline)."""

from __future__ import annotations

import pytest

from auditlens.config import clear_layer2_settings_cache
from auditlens.exceptions import (
    Layer2ConfigurationError,
    Layer2InvalidResponseError,
    Layer2ProviderError,
)
from auditlens.interpretation.llm.factory import create_provider_client
from auditlens.interpretation.llm.providers.groq import GroqClient
from auditlens.interpretation.llm.providers.openai import OpenAICompatibleClient
from auditlens.interpretation.llm.providers.openrouter import OpenRouterClient
from auditlens.interpretation.nodes.common import parse_json_with_retries, shorten_text


class _FakeOpenAIClass:
    captured: list[dict] = []

    def __init__(self, **kwargs: object) -> None:
        _FakeOpenAIClass.captured.append(kwargs)


def _configure_provider(monkeypatch: pytest.MonkeyPatch, provider: str, key: str = "test-key") -> None:
    monkeypatch.setenv("LAYER2_PROVIDER", provider)
    monkeypatch.setenv(f"{provider.upper()}_API_KEY", key)
    clear_layer2_settings_cache()


class TestProviderFactory:
    @pytest.mark.parametrize(
        ("provider", "expected_cls"),
        [("openai", OpenAICompatibleClient), ("groq", GroqClient), ("openrouter", OpenRouterClient)],
    )
    def test_factory_builds_each_provider(
        self, monkeypatch: pytest.MonkeyPatch, provider: str, expected_cls: type
    ) -> None:
        monkeypatch.setattr(
            "auditlens.interpretation.llm.providers.openai._openai_client_cls", lambda: _FakeOpenAIClass
        )
        _configure_provider(monkeypatch, provider)
        client = create_provider_client()
        assert isinstance(client, expected_cls)

    def test_factory_passes_settings_to_client(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "auditlens.interpretation.llm.providers.openai._openai_client_cls", lambda: _FakeOpenAIClass
        )
        _configure_provider(monkeypatch, "openai")
        monkeypatch.setenv("OPENAI_MODEL", "my-model")
        monkeypatch.setenv("OPENAI_BASE_URL", "https://example.invalid/v1")
        monkeypatch.setenv("LAYER2_TIMEOUT_SECONDS", "9.5")
        clear_layer2_settings_cache()
        client = create_provider_client()
        captured = _FakeOpenAIClass.captured[-1]
        assert client._model == "my-model"
        assert captured["base_url"] == "https://example.invalid/v1"
        assert captured["timeout"] == 9.5
        assert captured["api_key"] == "test-key"

    def test_openrouter_sends_app_headers(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "auditlens.interpretation.llm.providers.openai._openai_client_cls", lambda: _FakeOpenAIClass
        )
        _configure_provider(monkeypatch, "openrouter")
        monkeypatch.setenv("OPENROUTER_APP_URL", "https://app.example.com")
        monkeypatch.setenv("OPENROUTER_APP_TITLE", "AuditLens")
        clear_layer2_settings_cache()
        create_provider_client()
        headers = _FakeOpenAIClass.captured[-1]["default_headers"]
        assert headers == {"HTTP-Referer": "https://app.example.com", "X-Title": "AuditLens"}

    def test_missing_api_key_raises_configuration_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LAYER2_PROVIDER", "openai")
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        clear_layer2_settings_cache()
        with pytest.raises(Layer2ConfigurationError, match="OPENAI_API_KEY is required"):
            create_provider_client()

    def test_invalid_provider_raises_configuration_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LAYER2_PROVIDER", "anthropic")
        clear_layer2_settings_cache()
        with pytest.raises(Layer2ConfigurationError, match="one of: openai, groq, openrouter"):
            create_provider_client()


class _ChatCompletions:
    def __init__(self, responses: list) -> None:
        self._responses = list(responses)
        self.calls: list[dict] = []

    def create(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class _FakeChat:
    def __init__(self, completions: _ChatCompletions) -> None:
        self.completions = completions


class _FakeClient:
    def __init__(self, chat: _FakeChat) -> None:
        self.chat = chat


def _response(content: str) -> object:
    return type("Response", (), {"choices": [type("Choice", (), {"message": type("Message", (), {"content": content})()})()]})()


def _empty_response() -> object:
    return type("Response", (), {"choices": []})()


def _build_client(completions: _ChatCompletions) -> OpenAICompatibleClient:
    client = OpenAICompatibleClient.__new__(OpenAICompatibleClient)
    client._model = "model"
    client._client = _FakeClient(_FakeChat(completions))
    return client


class TestOpenAICompatibleClient:
    def test_complete_json_returns_content(self) -> None:
        c = _ChatCompletions([_response('{"ok": true}')])
        client = _build_client(c)
        assert client.complete_json("prompt") == '{"ok": true}'
        assert c.calls[0]["response_format"] == {"type": "json_object"}

    def test_empty_choices_raise_provider_error(self) -> None:
        client = _build_client(_ChatCompletions([_empty_response()]))
        with pytest.raises(Layer2ProviderError, match="empty response"):
            client.complete_json("prompt")

    def test_empty_content_raises_provider_error(self) -> None:
        client = _build_client(_ChatCompletions([_response("")]))
        with pytest.raises(Layer2ProviderError, match="empty response"):
            client.complete_json("prompt")

    def test_fallback_when_response_format_is_rejected(self) -> None:
        # First call raises (json_object unsupported); fallback call succeeds.
        c = _ChatCompletions([RuntimeError("bad request: json_object"), _response("fallback ok")])
        client = _build_client(c)
        assert client.complete_json("prompt") == "fallback ok"
        assert len(c.calls) == 2
        assert "response_format" not in c.calls[1]

    def test_double_failure_raises_provider_error(self) -> None:
        c = _ChatCompletions([RuntimeError("first"), RuntimeError("second")])
        client = _build_client(c)
        with pytest.raises(Layer2ProviderError, match="LLM provider request failed"):
            client.complete_json("prompt")


class _AlwaysInvalidJSON:
    def __init__(self, payload: str = "not json") -> None:
        self._payload = payload

    def complete_json(self, prompt: str) -> str:
        return self._payload


class TestParseJsonWithRetries:
    def test_valid_json_first_try(self) -> None:
        class _Ok:
            def complete_json(self, prompt: str) -> str:
                return '{"a": 1}'

        assert parse_json_with_retries(client=_Ok(), prompt="p", max_retries=3) == {"a": 1}

    def test_invalid_then_valid_within_retries(self) -> None:
        class _Recover:
            def __init__(self) -> None:
                self.calls = 0

            def complete_json(self, prompt: str) -> str:
                self.calls += 1
                return "bad" if self.calls == 1 else '{"b": 2}'

        client = _Recover()
        assert parse_json_with_retries(client=client, prompt="p", max_retries=2) == {"b": 2}
        assert client.calls == 2

    def test_always_invalid_raises_after_retries(self) -> None:
        client = _AlwaysInvalidJSON()
        with pytest.raises(Layer2InvalidResponseError, match="invalid JSON"):
            parse_json_with_retries(client=client, prompt="p", max_retries=2)

    def test_zero_retries_allows_one_attempt(self) -> None:
        client = _AlwaysInvalidJSON()
        with pytest.raises(Layer2InvalidResponseError):
            parse_json_with_retries(client=client, prompt="p", max_retries=0)

    def test_non_dict_json_keeps_retrying(self) -> None:
        client = _AlwaysInvalidJSON(payload='[1, 2, 3]')
        with pytest.raises(Layer2InvalidResponseError):
            parse_json_with_retries(client=client, prompt="p", max_retries=1)


class TestShortenText:
    def test_short_text_passthrough(self) -> None:
        assert shorten_text("  hello   world  ") == "hello world"

    def test_long_text_truncates_with_ellipsis(self) -> None:
        out = shorten_text("x" * 100, limit=20)
        assert len(out) <= 20
        assert out.endswith("...")

    def test_custom_limit(self) -> None:
        assert shorten_text("abcdefghij", limit=6) == "abc..."
