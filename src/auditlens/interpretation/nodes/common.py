from __future__ import annotations

import json
from typing import Any

from backend.layer2.errors import Layer2InvalidResponseError
from backend.layer2.llm.base import BaseLLMClient


def parse_json_with_retries(
    *,
    client: BaseLLMClient,
    prompt: str,
    max_retries: int,
) -> dict[str, Any]:
    last_payload = ""
    attempts = max(max_retries + 1, 1)
    for _ in range(attempts):
        last_payload = client.complete_json(prompt)
        try:
            parsed = json.loads(last_payload)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    raise Layer2InvalidResponseError("Provider returned invalid JSON response")


def shorten_text(value: str, limit: int = 600) -> str:
    collapsed = " ".join(value.strip().split())
    if len(collapsed) <= limit:
        return collapsed
    return f"{collapsed[: limit - 3]}..."
