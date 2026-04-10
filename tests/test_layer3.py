from __future__ import annotations

import base64
import json

from fastapi.testclient import TestClient

from backend.layer2.llm.base import BaseLLMClient
from backend.layer3.report_generator import build_markdown_report, build_pdf_report
from backend.layer3.visualizations import build_issue_type_chart, build_severity_summary_chart
from backend.main import app
from backend.utils.config import clear_layer2_settings_cache

client = TestClient(app)


class _Layer3LLM(BaseLLMClient):
    def complete_json(self, prompt: str) -> str:
        if "Extract structured context" in prompt:
            return json.dumps(
                {
                    "task_type": "binary_classification",
                    "affected_population": "applicants",
                    "decision_impact": "approval decisions",
                    "stakes_level": "high",
                    "confidence": 0.95,
                }
            )
        if "Given task context and one statistical issue" in prompt:
            return json.dumps(
                {
                    "issue_id": "issue_1",
                    "why_harmful": "This can skew predictions by subgroup.",
                    "at_risk_groups": ["group_a"],
                    "likely_model_impact": "Uneven error rates across groups.",
                    "severity_delta": "equal",
                    "severity_rationale": "Task impact matches statistical evidence.",
                }
            )
        if "ML bias mitigation advisor" in prompt:
            return json.dumps(
                {
                    "mitigations": [
                        {
                            "title": "Use subgroup reweighting",
                            "category": "reweighting",
                            "when_to_use": "When subgroup outcomes are imbalanced.",
                            "tradeoffs": "May reduce global accuracy slightly.",
                            "difficulty": "medium",
                            "expected_impact": "Improves fairness metrics.",
                            "code_snippet": "model.fit(X_train, y_train, sample_weight=weights)",
                        }
                    ]
                }
            )
        return "{}"


class _ClarifyLLM(BaseLLMClient):
    def complete_json(self, prompt: str) -> str:
        if "Extract structured context" in prompt:
            return json.dumps(
                {
                    "task_type": "unknown",
                    "affected_population": "",
                    "decision_impact": "",
                    "stakes_level": "unknown",
                    "confidence": 0.1,
                }
            )
        return "{}"


def test_build_markdown_report_contains_key_sections() -> None:
    final_report = {
        "task_description": "Predict loan approvals",
        "task_context": {
            "task_type": "binary_classification",
            "stakes_level": "high",
            "affected_population": "loan applicants",
            "decision_impact": "credit decisions",
        },
        "issues": [
            {
                "statistical_issue": {
                    "issue_id": "class_imbalance_target",
                    "type": "class_imbalance",
                    "severity": "high",
                    "description": "Target classes are imbalanced",
                },
                "interpretation": {
                    "issue_id": "class_imbalance_target",
                    "why_harmful": "Minority class may be under-predicted.",
                    "at_risk_groups": ["group_a"],
                    "likely_model_impact": "Lower recall for minority outcomes.",
                    "severity_delta": "higher",
                    "severity_rationale": "High-stakes decision setting.",
                },
                "mitigations": [
                    {
                        "title": "Apply class weighting",
                        "category": "reweighting",
                        "when_to_use": "If positive class is rare.",
                        "tradeoffs": "Can reduce precision.",
                        "difficulty": "easy",
                        "expected_impact": "Improves minority recall.",
                        "code_snippet": "model.fit(X_train, y_train, sample_weight=w)",
                    }
                ],
            }
        ],
        "summary": "One high-priority issue detected.",
        "disclaimer": "Human review required.",
    }
    layer1_report = {
        "dataset_info": {
            "rows": 100,
            "columns": 10,
            "target_column": "approved",
            "sensitive_columns": ["sex", "race"],
        }
    }

    output = build_markdown_report(final_report=final_report, layer1_report=layer1_report)
    assert "# AuditLens Bias Audit Report" in output
    assert "## Executive Summary" in output
    assert "## Findings" in output
    assert "## Disclaimer" in output
    assert "class_imbalance_target" in output
    assert "```python" in output


def test_analyze_task_report_complete(monkeypatch) -> None:
    monkeypatch.setenv("LAYER2_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    clear_layer2_settings_cache()
    monkeypatch.setattr("backend.layer2.agent.create_provider_client", lambda: _Layer3LLM())

    csv_text = "sex,race,target\nM,A,1\nF,B,0\n"
    response = client.post(
        "/analyze-task-report",
        files=[
            ("file", ("sample.csv", csv_text.encode("utf-8"), "text/csv")),
            ("target_column", (None, "target")),
            ("sensitive_columns", (None, "sex")),
            ("task_description", (None, "Predict approval outcomes")),
        ],
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "complete"
    assert payload["report_artifact"]["format"] == "markdown"
    assert payload["report_artifact"]["filename"] == "auditlens_report.md"
    assert "# AuditLens Bias Audit Report" in payload["report_artifact"]["content"]


def test_analyze_task_report_needs_clarification(monkeypatch) -> None:
    monkeypatch.setenv("LAYER2_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    clear_layer2_settings_cache()
    monkeypatch.setattr("backend.layer2.agent.create_provider_client", lambda: _ClarifyLLM())

    csv_text = "sex,race,target\nM,A,1\nF,B,0\n"
    response = client.post(
        "/analyze-task-report",
        files=[
            ("file", ("sample.csv", csv_text.encode("utf-8"), "text/csv")),
            ("target_column", (None, "target")),
            ("sensitive_columns", (None, "sex")),
            ("task_description", (None, "Predict outcomes")),
        ],
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "needs_clarification"
    assert payload["clarifying_questions"]


def test_build_charts_return_png_bytes() -> None:
    layer1_report = {
        "summary": {"high_severity": 2, "medium_severity": 1, "low_severity": 0},
    }
    final_report = {
        "issues": [
            {"statistical_issue": {"type": "class_imbalance"}},
            {"statistical_issue": {"type": "class_imbalance"}},
            {"statistical_issue": {"type": "missingness_gap"}},
        ]
    }
    severity_png = build_severity_summary_chart(layer1_report)
    issue_type_png = build_issue_type_chart(final_report)
    assert severity_png.startswith(b"\x89PNG")
    assert issue_type_png.startswith(b"\x89PNG")


def test_build_pdf_report_returns_pdf_bytes() -> None:
    final_report = {
        "task_description": "Predict approvals",
        "task_context": {
            "task_type": "binary_classification",
            "stakes_level": "high",
            "affected_population": "applicants",
            "decision_impact": "approval decisions",
        },
        "issues": [
            {
                "statistical_issue": {
                    "issue_id": "issue_1",
                    "type": "class_imbalance",
                    "severity": "high",
                    "description": "Imbalanced classes",
                },
                "interpretation": {
                    "issue_id": "issue_1",
                    "why_harmful": "Minority class may be under-predicted.",
                    "likely_model_impact": "Higher false negatives for minority class.",
                },
                "mitigations": [
                    {"title": "Apply reweighting", "difficulty": "medium"},
                ],
            }
        ],
        "summary": "One high-priority issue.",
        "disclaimer": "Human review required.",
    }
    layer1_report = {
        "dataset_info": {
            "rows": 100,
            "columns": 8,
            "target_column": "approved",
            "sensitive_columns": ["sex", "race"],
        },
        "summary": {"high_severity": 1, "medium_severity": 0, "low_severity": 0},
    }
    pdf_bytes = build_pdf_report(final_report=final_report, layer1_report=layer1_report)
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 1000


def test_analyze_task_report_pdf_complete(monkeypatch) -> None:
    monkeypatch.setenv("LAYER2_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    clear_layer2_settings_cache()
    monkeypatch.setattr("backend.layer2.agent.create_provider_client", lambda: _Layer3LLM())

    csv_text = "sex,race,target\nM,A,1\nF,B,0\n"
    response = client.post(
        "/analyze-task-report-pdf",
        files=[
            ("file", ("sample.csv", csv_text.encode("utf-8"), "text/csv")),
            ("target_column", (None, "target")),
            ("sensitive_columns", (None, "sex")),
            ("task_description", (None, "Predict approval outcomes")),
        ],
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "complete"
    assert payload["report_artifact"]["format"] == "pdf_base64"
    assert payload["report_artifact"]["filename"] == "auditlens_report.pdf"
    decoded = base64.b64decode(payload["report_artifact"]["content"])
    assert decoded.startswith(b"%PDF")


def test_analyze_task_report_pdf_needs_clarification(monkeypatch) -> None:
    monkeypatch.setenv("LAYER2_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    clear_layer2_settings_cache()
    monkeypatch.setattr("backend.layer2.agent.create_provider_client", lambda: _ClarifyLLM())

    csv_text = "sex,race,target\nM,A,1\nF,B,0\n"
    response = client.post(
        "/analyze-task-report-pdf",
        files=[
            ("file", ("sample.csv", csv_text.encode("utf-8"), "text/csv")),
            ("target_column", (None, "target")),
            ("sensitive_columns", (None, "sex")),
            ("task_description", (None, "Predict outcomes")),
        ],
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "needs_clarification"
    assert payload["clarifying_questions"]
