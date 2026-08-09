"""Severity mapping and audit orchestration edge cases."""

from __future__ import annotations

import math

import pandas as pd
import pytest

from auditlens.config import SEVERITY_THRESHOLDS
from auditlens.core.audit import run_layer1_audit, sort_issues
from auditlens.core.severity import score_threshold_metric, summarize_issues, validate_severity_thresholds
from auditlens.exceptions import AuditLensError


class TestScoreThresholdMetric:
    def test_default_table_binary_ratio(self) -> None:
        assert score_threshold_metric("imbalance_ratio", 4.0)[0] == "high"
        assert score_threshold_metric("imbalance_ratio", 2.0)[0] == "medium"
        assert score_threshold_metric("imbalance_ratio", 1.2)[0] == "low"

    def test_exact_threshold_boundary_is_lower_level(self) -> None:
        # Convention: `value > high` and `value > medium` are strict, so a value
        # exactly on a boundary scores the level below it.
        assert score_threshold_metric("imbalance_ratio", 3.0)[0] == "medium"
        assert score_threshold_metric("imbalance_ratio", 1.5)[0] == "low"

    def test_shared_cramers_v_fallback_for_correlation_metrics(self) -> None:
        partial = {"cramers_v": {"medium": 0.1, "high": 0.3}}
        for metric in ("point_biserial", "spearman", "pearson", "cramers_v_binned"):
            severity, justification = score_threshold_metric(metric, 0.5, severity_thresholds=partial)
            assert severity == "high"
            assert metric in justification

    def test_metric_specific_thresholds_win_over_fallback(self) -> None:
        table = {
            "imbalance_ratio": {"medium": 1.5, "high": 3.0},
            "cramers_v": {"medium": 0.1, "high": 0.3},
        }
        assert score_threshold_metric("imbalance_ratio", 0.2, severity_thresholds=table)[0] == "low"

    def test_unknown_metric_without_fallback_raises_clear_error(self) -> None:
        table = {"imbalance_ratio": {"medium": 1.5, "high": 3.0}}
        with pytest.raises(AuditLensError, match="No severity thresholds defined"):
            score_threshold_metric("bogus_metric", 0.5, severity_thresholds=table)

    @pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
    def test_non_finite_metric_raises(self, bad: float) -> None:
        with pytest.raises(AuditLensError, match="non-finite"):
            score_threshold_metric("imbalance_ratio", bad)

    def test_malformed_threshold_entry_raises_clear_error(self) -> None:
        for bad_table in [
            {"imbalance_ratio": {"medium": "x", "high": 3.0}},
            {"imbalance_ratio": {"high": 3.0}},
            {"imbalance_ratio": {"medium": 1.5, "high": "y"}},
        ]:
            with pytest.raises(AuditLensError, match="'medium' and 'high'"):
                score_threshold_metric("imbalance_ratio", 2.0, severity_thresholds=bad_table)

    def test_justification_reports_real_statistic_name(self) -> None:
        _, justification = score_threshold_metric("spearman", 0.42)
        assert "spearman=0.4200" in justification


class TestValidateSeverityThresholds:
    def test_default_table_is_valid(self) -> None:
        validate_severity_thresholds(SEVERITY_THRESHOLDS)

    def test_not_a_dict_raises(self) -> None:
        with pytest.raises(AuditLensError, match="dict"):
            validate_severity_thresholds(["imbalance_ratio"])

    def test_bounds_not_a_dict_raises(self) -> None:
        with pytest.raises(AuditLensError, match="must be a dict"):
            validate_severity_thresholds({"x": 3.0})

    def test_missing_or_non_numeric_bounds_raise(self) -> None:
        for bad in [
            {"m": {"high": 3.0}},
            {"m": {"medium": "not-a-number", "high": 3.0}},
            {"m": {"medium": None, "high": 3.0}},
        ]:
            with pytest.raises(AuditLensError):
                validate_severity_thresholds(bad)

    @pytest.mark.parametrize("bad", [{"medium": -0.1, "high": 3.0}, {"medium": 2.0, "high": 1.0}])
    def test_order_and_sign_are_enforced(self, bad: dict) -> None:
        with pytest.raises(AuditLensError, match="0 <= medium <= high"):
            validate_severity_thresholds({"m": bad})

    def test_non_finite_bounds_raise(self) -> None:
        with pytest.raises(AuditLensError, match="finite"):
            validate_severity_thresholds({"m": {"medium": 1.0, "high": math.inf}})


class TestSummarizeIssues:
    def test_counts_by_severity(self) -> None:
        issues = [
            {"severity": "high", "issue_id": "a"},
            {"severity": "medium", "issue_id": "b"},
            {"severity": "low", "issue_id": "c"},
            {"severity": "high", "issue_id": "d"},
        ]
        assert summarize_issues(issues) == {
            "total_issues": 4,
            "high_severity": 2,
            "medium_severity": 1,
            "low_severity": 1,
        }

    def test_empty_list(self) -> None:
        assert summarize_issues([]) == {
            "total_issues": 0,
            "high_severity": 0,
            "medium_severity": 0,
            "low_severity": 0,
        }


class TestSortIssues:
    def test_severity_order_then_issue_id(self) -> None:
        issues = [
            {"severity": "low", "issue_id": "z"},
            {"severity": "high", "issue_id": "b"},
            {"severity": "medium", "issue_id": "a"},
            {"severity": "high", "issue_id": "a"},
        ]
        ordered = sort_issues(issues)
        assert [i["issue_id"] for i in ordered] == ["a", "b", "a", "z"]
        assert [i["severity"] for i in ordered] == ["high", "high", "medium", "low"]


class TestRunLayer1AuditValidation:
    def test_rejects_non_dataframe(self) -> None:
        with pytest.raises(AuditLensError, match="DataFrame"):
            run_layer1_audit({"t": [0, 1]}, "t", ["g"])

    def test_rejects_non_list_sensitive_cols(self) -> None:
        df = pd.DataFrame({"t": [0, 1], "g": ["a", "b"]})
        with pytest.raises(AuditLensError, match="list or tuple of column name strings"):
            run_layer1_audit(df, "t", "g")

    def test_tuple_sensitive_cols_are_accepted(self) -> None:
        df = pd.DataFrame({"t": [0, 1, 1, 1], "g": ["a", "b", "a", "b"]})
        report = run_layer1_audit(df, "t", ("g",))
        assert report["dataset_info"]["sensitive_columns"] == ["g"]

    def test_rejects_target_also_in_sensitive(self) -> None:
        df = pd.DataFrame({"t": [0, 1, 0, 1], "g": ["a", "b", "a", "b"]})
        with pytest.raises(AuditLensError, match="must not also be listed"):
            run_layer1_audit(df, "t", ["t"])

    def test_duplicate_sensitive_cols_are_deduplicated(self) -> None:
        df = pd.DataFrame({"g": ["a"] * 4 + ["b"] * 4, "t": [0, 1, 1, 1, 0, 0, 0, 1]})
        report = run_layer1_audit(df, "t", ["g", "g"])
        assert report["dataset_info"]["sensitive_columns"] == ["g"]
        assert len(report["issues"]) == len(run_layer1_audit(df, "t", ["g"])["issues"])

    def test_bad_threshold_table_raises_before_analysis(self) -> None:
        df = pd.DataFrame({"g": ["a", "b"] * 4, "t": [0, 1] * 4})
        bad = {"imbalance_ratio": {"medium": 5.0, "high": 2.0}}
        with pytest.raises(AuditLensError, match="0 <= medium <= high"):
            run_layer1_audit(df, "t", ["g"], severity_thresholds=bad)

    def test_custom_thresholds_propagate_to_report(self) -> None:
        df = pd.DataFrame({"g": ["a", "b"] * 4, "t": [0, 0, 1, 1] * 2})
        custom = {k: dict(v) for k, v in SEVERITY_THRESHOLDS.items()}
        custom["demographic_parity_gap"] = {"medium": 0.9, "high": 0.95}
        report = run_layer1_audit(df, "t", ["g"], severity_thresholds=custom)
        assert report["severity_thresholds"] is custom
        assert report["summary"]["total_issues"] == 0

    def test_empty_frame_is_a_valid_report(self) -> None:
        df = pd.DataFrame({"t": pd.Series([], dtype=int), "g": pd.Series([], dtype=str)})
        report = run_layer1_audit(df, "t", ["g"])
        assert report["summary"] == {
            "total_issues": 0,
            "high_severity": 0,
            "medium_severity": 0,
            "low_severity": 0,
        }
        assert report["dataset_info"]["rows"] == 0
