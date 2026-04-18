from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Literal

from auditlens.exceptions import Layer2ConfigurationError


SEVERITY_THRESHOLDS = {
    "imbalance_ratio": {"medium": 1.5, "high": 3.0},
    "cramers_v": {"medium": 0.1, "high": 0.3},
    "demographic_parity_gap": {"medium": 0.05, "high": 0.15},
    "differential_missingness": {"medium": 0.05, "high": 0.15},
}

SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


@dataclass(frozen=True)
class Layer2Settings:
    provider: Literal["openai", "groq", "openrouter"]
    api_key: str
    model: str
    base_url: str
    timeout_seconds: float
    max_retries: int
    max_task_description_chars: int


def _parse_int(name: str, default: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        return int(raw)
    except ValueError as exc:
        raise Layer2ConfigurationError(f"{name} must be an integer") from exc


def _parse_float(name: str, default: float) -> float:
    raw = os.getenv(name, str(default)).strip()
    try:
        return float(raw)
    except ValueError as exc:
        raise Layer2ConfigurationError(f"{name} must be a number") from exc


def _provider_settings(provider: str) -> tuple[str, str, str]:
    if provider == "openai":
        return (
            os.getenv("OPENAI_API_KEY", "").strip(),
            os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip(),
            os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").strip(),
        )
    if provider == "groq":
        return (
            os.getenv("GROQ_API_KEY", "").strip(),
            os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile").strip(),
            os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1").strip(),
        )
    if provider == "openrouter":
        return (
            os.getenv("OPENROUTER_API_KEY", "").strip(),
            os.getenv("OPENROUTER_MODEL", "google/gemma-4-31b-it:free").strip(),
            os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").strip(),
        )
    raise Layer2ConfigurationError("LAYER2_PROVIDER must be one of: openai, groq, openrouter")


@lru_cache(maxsize=1)
def get_layer2_settings() -> Layer2Settings:
    provider = os.getenv("LAYER2_PROVIDER", "openai").strip().lower()
    api_key, model, base_url = _provider_settings(provider)

    if not api_key:
        env_name = {
            "openai": "OPENAI_API_KEY",
            "groq": "GROQ_API_KEY",
            "openrouter": "OPENROUTER_API_KEY",
        }.get(provider, "API_KEY")
        raise Layer2ConfigurationError(
            f"{env_name} is required when LAYER2_PROVIDER={provider}"
        )

    timeout_seconds = _parse_float("LAYER2_TIMEOUT_SECONDS", 20.0)
    max_retries = _parse_int("LAYER2_MAX_RETRIES", 2)
    max_task_description_chars = _parse_int("LAYER2_MAX_TASK_DESCRIPTION_CHARS", 5000)

    if timeout_seconds <= 0:
        raise Layer2ConfigurationError("LAYER2_TIMEOUT_SECONDS must be > 0")
    if max_retries < 0:
        raise Layer2ConfigurationError("LAYER2_MAX_RETRIES must be >= 0")
    if max_task_description_chars < 200:
        raise Layer2ConfigurationError("LAYER2_MAX_TASK_DESCRIPTION_CHARS must be >= 200")

    return Layer2Settings(
        provider=provider,  # type: ignore[arg-type]
        api_key=api_key,
        model=model,
        base_url=base_url,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
        max_task_description_chars=max_task_description_chars,
    )


def clear_layer2_settings_cache() -> None:
    get_layer2_settings.cache_clear()
