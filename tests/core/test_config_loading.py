"""Layer 2 environment-driven configuration parsing and validation."""

from __future__ import annotations

import pytest

from auditlens.config import clear_layer2_settings_cache, get_layer2_settings
from auditlens.exceptions import Layer2ConfigurationError


@pytest.fixture(autouse=True)
def _fresh_cache() -> None:
    clear_layer2_settings_cache()
    yield
    clear_layer2_settings_cache()


class TestProviderSettings:
    @pytest.mark.parametrize(
        ("provider", "key_env", "expected_base_url"),
        [
            ("openai", "OPENAI_API_KEY", "https://api.openai.com/v1"),
            ("groq", "GROQ_API_KEY", "https://api.groq.com/openai/v1"),
            ("openrouter", "OPENROUTER_API_KEY", "https://openrouter.ai/api/v1"),
        ],
    )
    def test_provider_defaults(
        self, monkeypatch: pytest.MonkeyPatch, provider: str, key_env: str, expected_base_url: str
    ) -> None:
        monkeypatch.setenv("LAYER2_PROVIDER", provider)
        monkeypatch.setenv(key_env, "key-123")
        settings = get_layer2_settings()
        assert settings.provider == provider
        assert settings.api_key == "key-123"
        assert settings.base_url == expected_base_url

    def test_custom_model_and_base_url(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LAYER2_PROVIDER", "openai")
        monkeypatch.setenv("OPENAI_API_KEY", "k")
        monkeypatch.setenv("OPENAI_MODEL", "my-custom-model")
        monkeypatch.setenv("OPENAI_BASE_URL", "https://localhost:9999/v1")
        settings = get_layer2_settings()
        assert settings.model == "my-custom-model"
        assert settings.base_url == "https://localhost:9999/v1"

    def test_missing_key_raises_configuration_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LAYER2_PROVIDER", "groq")
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        with pytest.raises(Layer2ConfigurationError, match="GROQ_API_KEY is required"):
            get_layer2_settings()

    def test_provider_case_insensitive(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LAYER2_PROVIDER", "OpenAI")
        monkeypatch.setenv("OPENAI_API_KEY", "k")
        assert get_layer2_settings().provider == "openai"

    def test_unknown_provider_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LAYER2_PROVIDER", "gemini")
        with pytest.raises(Layer2ConfigurationError, match="one of: openai, groq, openrouter"):
            get_layer2_settings()


class TestNumericSettings:
    def test_timeout_parsed_as_float(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LAYER2_PROVIDER", "openai")
        monkeypatch.setenv("OPENAI_API_KEY", "k")
        monkeypatch.setenv("LAYER2_TIMEOUT_SECONDS", "12.5")
        assert get_layer2_settings().timeout_seconds == 12.5

    def test_retries_and_description_chars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LAYER2_PROVIDER", "openai")
        monkeypatch.setenv("OPENAI_API_KEY", "k")
        monkeypatch.setenv("LAYER2_MAX_RETRIES", "4")
        monkeypatch.setenv("LAYER2_MAX_TASK_DESCRIPTION_CHARS", "3000")
        settings = get_layer2_settings()
        assert settings.max_retries == 4
        assert settings.max_task_description_chars == 3000

    @pytest.mark.parametrize(
        ("env", "value", "match"),
        [
            ("LAYER2_TIMEOUT_SECONDS", "abc", "must be a number"),
            ("LAYER2_MAX_RETRIES", "abc", "must be an integer"),
            ("LAYER2_MAX_TASK_DESCRIPTION_CHARS", "abc", "must be an integer"),
        ],
    )
    def test_invalid_numeric_env_raises(
        self, monkeypatch: pytest.MonkeyPatch, env: str, value: str, match: str
    ) -> None:
        monkeypatch.setenv("LAYER2_PROVIDER", "openai")
        monkeypatch.setenv("OPENAI_API_KEY", "k")
        monkeypatch.setenv(env, value)
        with pytest.raises(Layer2ConfigurationError, match=match):
            get_layer2_settings()

    @pytest.mark.parametrize(
        ("env", "value"),
        [
            ("LAYER2_TIMEOUT_SECONDS", "0"),
            ("LAYER2_TIMEOUT_SECONDS", "-5"),
            ("LAYER2_MAX_RETRIES", "-1"),
            ("LAYER2_MAX_TASK_DESCRIPTION_CHARS", "199"),
        ],
    )
    def test_out_of_range_env_raises(self, monkeypatch: pytest.MonkeyPatch, env: str, value: str) -> None:
        monkeypatch.setenv("LAYER2_PROVIDER", "openai")
        monkeypatch.setenv("OPENAI_API_KEY", "k")
        monkeypatch.setenv(env, value)
        with pytest.raises(Layer2ConfigurationError):
            get_layer2_settings()


class TestCacheBehavior:
    def test_settings_are_cached_until_cleared(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LAYER2_PROVIDER", "openai")
        monkeypatch.setenv("OPENAI_API_KEY", "first")
        get_layer2_settings()
        monkeypatch.setenv("OPENAI_API_KEY", "second")
        assert get_layer2_settings().api_key == "first"
        clear_layer2_settings_cache()
        assert get_layer2_settings().api_key == "second"
