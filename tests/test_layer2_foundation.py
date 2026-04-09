from __future__ import annotations

import json

from fastapi.testclient import TestClient

from backend.layer2.llm.base import BaseLLMClient
from backend.main import app
from backend.utils.config import clear_layer2_settings_cache, get_layer2_settings

client = TestClient(app)


class _FoundationLLM(BaseLLMClient):
    def complete_json(self, prompt: str) -> str:
        if "Extract structured context" in prompt:
            return json.dumps(
                {
                    "task_type": "unknown",
                    "affected_population": "",
                    "decision_impact": "",
                    "stakes_level": "unknown",
                    "confidence": 0.2,
                }
            )
        if "Given task context and one statistical issue" in prompt:
            return json.dumps(
                {
                    "issue_id": "issue",
                    "why_harmful": "Potential harm",
                    "at_risk_groups": [],
                    "likely_model_impact": "Potential disparity",
                    "severity_delta": "equal",
                    "severity_rationale": "Matches statistical severity",
                }
            )
        return json.dumps({"mitigations": []})


def _csv_bytes(content: str) -> bytes:
    return content.encode("utf-8")


def test_layer2_config_parsing_openai(monkeypatch) -> None:
    monkeypatch.setenv("LAYER2_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("LAYER2_TIMEOUT_SECONDS", "10")
    monkeypatch.setenv("LAYER2_MAX_RETRIES", "1")
    clear_layer2_settings_cache()

    settings = get_layer2_settings()
    assert settings.provider == "openai"
    assert settings.api_key == "test-key"
    assert settings.timeout_seconds == 10.0
    assert settings.max_retries == 1


def test_analyze_task_requires_task_description(monkeypatch) -> None:
    monkeypatch.setenv("LAYER2_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    clear_layer2_settings_cache()

    csv_text = "sex,race,target\nM,A,1\nF,B,0\n"
    response = client.post(
        "/analyze-task",
        files=[
            ("file", ("sample.csv", _csv_bytes(csv_text), "text/csv")),
            ("target_column", (None, "target")),
            ("sensitive_columns", (None, "sex")),
        ],
    )
    assert response.status_code == 422


def test_analyze_task_rejects_bad_clarification_json(monkeypatch) -> None:
    monkeypatch.setenv("LAYER2_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    clear_layer2_settings_cache()

    csv_text = "sex,race,target\nM,A,1\nF,B,0\n"
    response = client.post(
        "/analyze-task",
        files=[
            ("file", ("sample.csv", _csv_bytes(csv_text), "text/csv")),
            ("target_column", (None, "target")),
            ("sensitive_columns", (None, "sex")),
            ("task_description", (None, "Predict default risk.")),
            ("clarification_answers", (None, "{bad json")),
        ],
    )
    assert response.status_code == 422
    assert "clarification_answers" in response.json()["detail"]


def test_analyze_task_missing_provider_config(monkeypatch) -> None:
    monkeypatch.setenv("LAYER2_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    clear_layer2_settings_cache()

    csv_text = "sex,race,target\nM,A,1\nF,B,0\n"
    response = client.post(
        "/analyze-task",
        files=[
            ("file", ("sample.csv", _csv_bytes(csv_text), "text/csv")),
            ("target_column", (None, "target")),
            ("sensitive_columns", (None, "sex")),
            ("task_description", (None, "Predict default risk.")),
        ],
    )
    assert response.status_code == 503
    assert "OPENAI_API_KEY" in response.json()["detail"]


def test_analyze_task_placeholder_flow(monkeypatch) -> None:
    monkeypatch.setenv("LAYER2_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr("backend.layer2.agent.create_provider_client", lambda: _FoundationLLM())
    clear_layer2_settings_cache()

    csv_text = "sex,race,target\nM,A,1\nF,B,0\n"
    first = client.post(
        "/analyze-task",
        files=[
            ("file", ("sample.csv", _csv_bytes(csv_text), "text/csv")),
            ("target_column", (None, "target")),
            ("sensitive_columns", (None, "sex")),
            ("task_description", (None, "Predict income class.")),
        ],
    )
    assert first.status_code == 200
    assert first.json()["status"] == "needs_clarification"

    second = client.post(
        "/analyze-task",
        files=[
            ("file", ("sample.csv", _csv_bytes(csv_text), "text/csv")),
            ("target_column", (None, "target")),
            ("sensitive_columns", (None, "sex")),
            ("task_description", (None, "Predict income class.")),
            (
                "clarification_answers",
                (
                    None,
                    '{"task_type":"binary_classification","affected_population":"applicants","decision_impact":"approval","confidence":0.95,"stakes_level":"high"}',
                ),
            ),
        ],
    )
    assert second.status_code == 200
    assert second.json()["status"] == "complete"
