"""Layer 2 pipeline behavior with an empty Layer 1 report."""

from __future__ import annotations

import json

from auditlens.interpretation.llm.base import BaseLLMClient
from auditlens.interpretation.pipeline import run_layer2_pipeline


class _ScriptedLLM(BaseLLMClient):
    def complete_json(self, prompt: str) -> str:
        if "Extract structured context" in prompt:
            return json.dumps(
                {
                    "task_type": "binary_classification",
                    "affected_population": "users",
                    "decision_impact": "decisions",
                    "stakes_level": "low",
                    "confidence": 0.95,
                }
            )
        return "{}"


def _empty_layer1() -> dict:
    return {
        "dataset_info": {"rows": 10, "columns": 3, "target_column": "t", "sensitive_columns": ["s"]},
        "issues": [],
        "summary": {"total_issues": 0, "high_severity": 0, "medium_severity": 0, "low_severity": 0},
        "severity_thresholds": {},
    }


def test_pipeline_completes_with_zero_issues() -> None:
    out = run_layer2_pipeline(
        layer1_report=_empty_layer1(),
        task_description="Predict churn",
        llm_client=_ScriptedLLM(),
        layer2_provider="test",
        layer2_model="test",
    )
    assert out["status"] == "complete"
    final = out["final_report"]
    assert final["issues"] == []
    assert "0 issue(s)" in final["summary"]
    assert final["task_context"]["task_type"] == "binary_classification"


def test_pipeline_clarification_path_returns_questions() -> None:
    class _VagueLLM(BaseLLMClient):
        def complete_json(self, prompt: str) -> str:
            if "Extract structured context" in prompt:
                return json.dumps(
                    {"task_type": "unknown", "confidence": 0.1, "assumptions": []}
                )
            return "{}"

    out = run_layer2_pipeline(
        layer1_report=_empty_layer1(),
        task_description="Vague",
        llm_client=_VagueLLM(),
    )
    assert out["status"] == "needs_clarification"
    assert out["clarifying_questions"]
    assert out["layer1_report"]["issues"] == []
    assert "severity_thresholds" not in out["layer1_report"]


def test_pipeline_all_provider_failures_raise() -> None:
    class _BrokenLLM(BaseLLMClient):
        def complete_json(self, prompt: str) -> str:
            return "not json at all"

    from auditlens.exceptions import Layer2InvalidResponseError

    try:
        run_layer2_pipeline(
            layer1_report=_empty_layer1(),
            task_description="Predict churn",
            llm_client=_BrokenLLM(),
        )
        raise AssertionError("expected Layer2InvalidResponseError")
    except Layer2InvalidResponseError:
        pass
