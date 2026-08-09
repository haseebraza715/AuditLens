"""Public `audit()` API contract edge cases."""

from __future__ import annotations

import json
import math

import pandas as pd
import pytest

from auditlens import AuditLensReport, audit
from auditlens.api import _json_safe
from auditlens.exceptions import AuditLensError


class TestAuditInputValidation:
    def test_non_dataframe_raises_clear_error(self) -> None:
        with pytest.raises(AuditLensError, match="DataFrame"):
            audit({"t": [0, 1]}, target_col="t", sensitive_cols=["s"])

    def test_missing_target_and_sensitive_raise(self) -> None:
        df = pd.DataFrame({"t": [0, 1], "s": ["a", "b"]})
        with pytest.raises(AuditLensError, match="target_col 'x' not found"):
            audit(df, target_col="x", sensitive_cols=["s"])
        with pytest.raises(AuditLensError, match="sensitive_cols not found"):
            audit(df, target_col="t", sensitive_cols=["x"])

    def test_target_in_sensitive_raises(self) -> None:
        df = pd.DataFrame({"t": [0, 1, 0, 1], "s": ["a", "b", "a", "b"]})
        with pytest.raises(AuditLensError, match="must not also be listed"):
            audit(df, target_col="t", sensitive_cols=["t"])

    def test_whitespace_task_description_skips_layer2(self) -> None:
        df = pd.DataFrame({"t": [0, 1], "s": ["a", "b"]})
        report = audit(df, target_col="t", sensitive_cols=["s"], task_description="   ")
        assert report.status is None


class TestJsonSafe:
    def test_non_finite_floats_become_none(self) -> None:
        assert _json_safe(float("inf")) is None
        assert _json_safe(float("-inf")) is None
        assert _json_safe(float("nan")) is None
        assert _json_safe(3.5) == 3.5

    def test_recursive_walk(self) -> None:
        payload = {
            "a": [1.0, float("inf"), {"b": float("nan")}],
            "c": (2.0, "x"),
            "d": None,
        }
        safe = _json_safe(payload)
        assert safe["a"] == [1.0, None, {"b": None}]
        assert safe["c"] == [2.0, "x"]
        json.dumps(safe)

    def test_int_and_string_untouched(self) -> None:
        assert _json_safe(5) == 5
        assert _json_safe("inf") == "inf"


class TestReportJsonSafety:
    def test_single_class_inf_metric_is_null_in_to_dict(self) -> None:
        df = pd.DataFrame({"t": [0] * 4, "s": ["a", "a", "b", "b"]})
        report = audit(df, target_col="t", sensitive_cols=["s"])
        issue = report.to_dict()["issues"][0]
        assert issue["metrics"]["imbalance_ratio"] is None
        assert math.isfinite(report.issues[0].metrics["imbalance_ratio"]) is False
        payload = json.dumps(report.to_dict())
        assert "Infinity" not in payload

    def test_to_dict_matches_summary(self) -> None:
        df = pd.DataFrame({"t": [0, 1, 1, 1], "s": ["a", "b", "a", "b"]})
        snapshot = audit(df, target_col="t", sensitive_cols=["s"]).to_dict()
        assert snapshot["summary"] == snapshot["layer1_report"]["summary"]
        assert snapshot["severity_thresholds"] is not None
        assert snapshot["status"] is None
        assert snapshot["final_report"] is None


class TestAuditLensReportWrapper:
    def test_issues_property_returns_models(self) -> None:
        df = pd.DataFrame({"t": [0, 1, 1, 1], "s": ["a", "b", "a", "b"]})
        report = audit(df, target_col="t", sensitive_cols=["s"])
        assert all(isinstance(issue, object) for issue in report.issues)
        assert report.summary["total_issues"] == len(report.issues)

    def test_layer1_only_markdown_lists_findings(self) -> None:
        df = pd.DataFrame({"t": [0, 1, 1, 1], "s": ["a", "b", "a", "b"]})
        report = audit(df, target_col="t", sensitive_cols=["s"])
        md = report.to_markdown()
        assert "## Findings" in md
        assert "class_imbalance" in md
        assert "Layer 2 interpretation was not run" in md

    def test_repr_is_brief_and_informative(self) -> None:
        df = pd.DataFrame({"t": [0, 1, 1, 1], "s": ["a", "b", "a", "b"]})
        text = repr(audit(df, target_col="t", sensitive_cols=["s"]))
        assert "AuditLensReport" in text
        assert "high=" in text

    def test_empty_report_repr_html(self) -> None:
        empty = {
            "dataset_info": {"rows": 0, "columns": 0, "target_column": "", "sensitive_columns": []},
            "issues": [],
            "summary": {"total_issues": 0, "high_severity": 0, "medium_severity": 0, "low_severity": 0},
            "severity_thresholds": {},
        }
        report = AuditLensReport(empty)
        html = report._repr_html_()
        assert "No issues" in html
        assert report.to_dict()["summary"]["total_issues"] == 0

    def test_needs_clarification_status_exposes_questions(self) -> None:
        report = AuditLensReport(
            {
                "dataset_info": {"rows": 1, "columns": 1, "target_column": "t", "sensitive_columns": []},
                "issues": [],
                "summary": {"total_issues": 0, "high_severity": 0, "medium_severity": 0, "low_severity": 0},
            },
            {
                "status": "needs_clarification",
                "clarifying_questions": ["What is the task type?"],
                "task_context_partial": {},
            },
        )
        assert report.status == "needs_clarification"
        assert report.clarifying_questions == ["What is the task type?"]
        assert report.final_report is None

    def test_complete_status_exposes_final_report(self) -> None:
        layer1 = {
            "dataset_info": {"rows": 4, "columns": 2, "target_column": "t", "sensitive_columns": ["s"]},
            "issues": [
                {
                    "issue_id": "ix",
                    "type": "class_imbalance",
                    "description": "d",
                    "affected_column": "t",
                    "severity": "high",
                    "metrics": {},
                    "justification": "j",
                }
            ],
            "summary": {"total_issues": 1, "high_severity": 1, "medium_severity": 0, "low_severity": 0},
            "severity_thresholds": {},
        }
        interpretation = {
            "status": "complete",
            "final_report": {
                "task_description": "Task",
                "task_context": {"task_type": "binary_classification"},
                "issues": [
                    {
                        "statistical_issue": layer1["issues"][0],
                        "interpretation": {
                            "issue_id": "ix",
                            "why_harmful": "h",
                            "likely_model_impact": "i",
                            "severity_delta": "equal",
                            "severity_rationale": "r",
                        },
                        "mitigations": [],
                    }
                ],
                "summary": "S",
                "disclaimer": "D",
            },
        }
        report = AuditLensReport(layer1, interpretation)
        assert report.status == "complete"
        assert report.final_report is not None
        assert report.final_report.task_description == "Task"
        md = report.to_markdown()
        assert "## Findings" in md
        assert "ix" in md
