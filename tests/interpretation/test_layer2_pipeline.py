from __future__ import annotations

import json
import re
import time

from fastapi.testclient import TestClient

from backend.layer2.agent import run_layer2_pipeline
from backend.layer2.errors import Layer2ProviderError
from backend.layer2.llm.base import BaseLLMClient
from backend.layer2.nodes.analyze import analyze_node
from backend.layer2.nodes.parse import parse_node
from backend.main import app
from backend.utils.config import clear_layer2_settings_cache

client = TestClient(app)


class ScriptedLLMClient(BaseLLMClient):
    def __init__(
        self,
        *,
        analyze_payload: dict[str, object],
        interpret_invalid: bool = False,
        recommend_invalid: bool = False,
        invalid_analyze_first: bool = False,
    ) -> None:
        self.analyze_payload = analyze_payload
        self.interpret_invalid = interpret_invalid
        self.recommend_invalid = recommend_invalid
        self.invalid_analyze_first = invalid_analyze_first
        self._analyze_calls = 0

    def complete_json(self, prompt: str) -> str:
        if "Extract structured context" in prompt:
            self._analyze_calls += 1
            if self.invalid_analyze_first and self._analyze_calls == 1:
                return "not-json"
            return json.dumps(self.analyze_payload)

        if "Given task context and one statistical issue" in prompt:
            if self.interpret_invalid:
                return "not-json"
            issue_id_match = re.search(r'"issue_id"\s*:\s*"([^"]+)"', prompt)
            issue_id = issue_id_match.group(1) if issue_id_match else "unknown_issue"
            return json.dumps(
                {
                    "issue_id": issue_id,
                    "why_harmful": "This issue can skew model behavior for specific subgroups.",
                    "at_risk_groups": ["group_a"],
                    "likely_model_impact": "May increase error disparity.",
                    "severity_delta": "equal",
                    "severity_rationale": "Task impact aligns with statistical severity.",
                }
            )

        if "ML bias mitigation advisor" in prompt:
            if self.recommend_invalid:
                return "not-json"
            return json.dumps(
                {
                    "mitigations": [
                        {
                            "title": "Apply class-balanced reweighting",
                            "category": "reweighting",
                            "when_to_use": "When subgroup outcomes are imbalanced.",
                            "tradeoffs": "Can shift global optimization behavior.",
                            "difficulty": "medium",
                            "expected_impact": "Improves subgroup parity.",
                            "code_snippet": "model.fit(X_train, y_train, sample_weight=weights)",
                        }
                    ]
                }
            )

        return "{}"


def _layer1_report() -> dict[str, object]:
    return {
        "dataset_info": {
            "rows": 4,
            "columns": 4,
            "target_column": "target",
            "sensitive_columns": ["sex"],
        },
        "issues": [
            {
                "issue_id": "z_issue",
                "type": "missingness_gap",
                "description": "Missingness differs by group",
                "affected_column": "feature_a",
                "severity": "medium",
                "metrics": {"differential_missingness": 0.2},
                "justification": "Gap above medium threshold",
            },
            {
                "issue_id": "a_issue",
                "type": "class_imbalance",
                "description": "Imbalanced classes",
                "affected_column": "target",
                "severity": "high",
                "metrics": {"imbalance_ratio": 4.0},
                "justification": "Ratio above high threshold",
            },
        ],
        "summary": {"total_issues": 2, "high_severity": 1, "medium_severity": 1, "low_severity": 0},
    }


def test_parse_node_orders_issues() -> None:
    state = parse_node({"raw_json": _layer1_report()})
    issue_ids = [issue["issue_id"] for issue in state["parsed_issues"]]
    assert issue_ids == ["a_issue", "z_issue"]


def test_analyze_node_retries_invalid_json_and_marks_ambiguous() -> None:
    fake_llm = ScriptedLLMClient(
        analyze_payload={
            "task_type": "unknown",
            "affected_population": "",
            "decision_impact": "",
            "stakes_level": "unknown",
            "confidence": 0.3,
        },
        invalid_analyze_first=True,
    )
    result = analyze_node(
        {
            "task_description": "predict something",
            "clarification_answers": {},
            "llm_client": fake_llm,
            "max_retries": 1,
        }
    )
    assert result["needs_clarification"] is True
    assert result["task_context"]["task_type"] == "unknown"


def test_pipeline_clarification_then_complete(monkeypatch) -> None:
    monkeypatch.setenv("LAYER2_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    clear_layer2_settings_cache()

    fake_llm = ScriptedLLMClient(
        analyze_payload={
            "task_type": "unknown",
            "affected_population": "",
            "decision_impact": "",
            "stakes_level": "unknown",
            "confidence": 0.2,
        }
    )
    first = run_layer2_pipeline(
        layer1_report=_layer1_report(),
        task_description="Predict risk score",
        llm_client=fake_llm,
    )
    assert first["status"] == "needs_clarification"

    second = run_layer2_pipeline(
        layer1_report=_layer1_report(),
        task_description="Predict risk score",
        clarification_answers={
            "task_type": "binary_classification",
            "affected_population": "loan applicants",
            "decision_impact": "approval decisions",
            "confidence": 0.95,
            "stakes_level": "high",
        },
        llm_client=fake_llm,
    )
    assert second["status"] == "complete"
    assert second["final_report"]["issues"]


def test_pipeline_fallbacks_on_bad_interpret_recommend(monkeypatch) -> None:
    monkeypatch.setenv("LAYER2_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    clear_layer2_settings_cache()

    fake_llm = ScriptedLLMClient(
        analyze_payload={
            "task_type": "binary_classification",
            "affected_population": "users",
            "decision_impact": "eligibility decisions",
            "stakes_level": "high",
            "confidence": 0.9,
        },
        interpret_invalid=True,
        recommend_invalid=True,
    )
    result = run_layer2_pipeline(
        layer1_report=_layer1_report(),
        task_description="Decide eligibility",
        llm_client=fake_llm,
    )
    assert result["status"] == "complete"
    issues = result["final_report"]["issues"]
    assert len(issues) == 2
    assert issues[0]["interpretation"]["why_harmful"]
    assert issues[0]["mitigations"]


def test_pipeline_deterministic_postprocessing(monkeypatch) -> None:
    monkeypatch.setenv("LAYER2_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    clear_layer2_settings_cache()

    payload = {
        "task_type": "binary_classification",
        "affected_population": "users",
        "decision_impact": "product eligibility",
        "stakes_level": "medium",
        "confidence": 0.9,
    }
    run_a = run_layer2_pipeline(
        layer1_report=_layer1_report(),
        task_description="Eligibility classification",
        llm_client=ScriptedLLMClient(analyze_payload=payload),
    )
    run_b = run_layer2_pipeline(
        layer1_report=_layer1_report(),
        task_description="Eligibility classification",
        llm_client=ScriptedLLMClient(analyze_payload=payload),
    )
    assert run_a == run_b


def test_analyze_task_api_flow(monkeypatch) -> None:
    monkeypatch.setenv("LAYER2_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    clear_layer2_settings_cache()

    fake = ScriptedLLMClient(
        analyze_payload={
            "task_type": "unknown",
            "affected_population": "",
            "decision_impact": "",
            "stakes_level": "unknown",
            "confidence": 0.2,
        }
    )
    monkeypatch.setattr("backend.layer2.agent.create_provider_client", lambda: fake)

    csv_text = "sex,race,target\nM,A,1\nF,B,0\n"
    first = client.post(
        "/analyze-task",
        files=[
            ("file", ("sample.csv", csv_text.encode("utf-8"), "text/csv")),
            ("target_column", (None, "target")),
            ("sensitive_columns", (None, "sex")),
            ("task_description", (None, "Predict approvals")),
        ],
    )
    assert first.status_code == 200
    assert first.json()["status"] == "needs_clarification"

    second = client.post(
        "/analyze-task",
        files=[
            ("file", ("sample.csv", csv_text.encode("utf-8"), "text/csv")),
            ("target_column", (None, "target")),
            ("sensitive_columns", (None, "sex")),
            ("task_description", (None, "Predict approvals")),
            (
                "clarification_answers",
                (
                    None,
                    '{"task_type":"binary_classification","affected_population":"applicants","decision_impact":"approvals","confidence":0.9,"stakes_level":"high"}',
                ),
            ),
        ],
    )
    assert second.status_code == 200
    assert second.json()["status"] == "complete"


def test_analyze_task_provider_failure_returns_502(monkeypatch) -> None:
    monkeypatch.setenv("LAYER2_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    clear_layer2_settings_cache()

    def _raise() -> BaseLLMClient:
        raise Layer2ProviderError("provider unavailable")

    monkeypatch.setattr("backend.layer2.agent.create_provider_client", _raise)

    csv_text = "sex,race,target\nM,A,1\nF,B,0\n"
    response = client.post(
        "/analyze-task",
        files=[
            ("file", ("sample.csv", csv_text.encode("utf-8"), "text/csv")),
            ("target_column", (None, "target")),
            ("sensitive_columns", (None, "sex")),
            ("task_description", (None, "Predict approvals")),
        ],
    )
    assert response.status_code == 502


def test_layer2_performance_sanity(monkeypatch) -> None:
    monkeypatch.setenv("LAYER2_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    clear_layer2_settings_cache()

    large_report = _layer1_report()
    issues = list(large_report["issues"]) * 30
    large_report["issues"] = issues
    large_report["summary"]["total_issues"] = len(issues)
    fake_llm = ScriptedLLMClient(
        analyze_payload={
            "task_type": "binary_classification",
            "affected_population": "users",
            "decision_impact": "decision support",
            "stakes_level": "medium",
            "confidence": 0.9,
        }
    )

    start = time.perf_counter()
    result = run_layer2_pipeline(
        layer1_report=large_report,
        task_description="Support a binary decision",
        llm_client=fake_llm,
    )
    elapsed = time.perf_counter() - start

    assert result["status"] == "complete"
    assert elapsed < 5.0
