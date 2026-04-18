from __future__ import annotations

import time

import pandas as pd

from auditlens.core.audit import run_layer1_audit
from auditlens.core.analyzers.class_distribution import analyze_class_distribution
from auditlens.core.analyzers.correlations import analyze_sensitive_correlations
from auditlens.core.analyzers.missing_values import analyze_missing_values_by_group
from auditlens.core.analyzers.subgroup_analysis import analyze_subgroup_label_distribution


def test_class_distribution_binary_high() -> None:
    df = pd.DataFrame({"target": [0] * 80 + [1] * 20})
    issues = analyze_class_distribution(df, "target")
    assert len(issues) == 1
    assert issues[0]["severity"] == "high"
    assert issues[0]["metrics"]["imbalance_ratio"] == 4.0


def test_class_distribution_multiclass_medium() -> None:
    df = pd.DataFrame({"target": ["A"] * 60 + ["B"] * 35 + ["C"] * 5})
    issues = analyze_class_distribution(df, "target")
    assert len(issues) == 1
    assert issues[0]["severity"] == "medium"


def test_missingness_gap_detected() -> None:
    df = pd.DataFrame(
        {
            "sex": ["M"] * 50 + ["F"] * 50,
            "feature": [1] * 50 + [None] * 20 + [1] * 30,
            "target": [0, 1] * 50,
        }
    )
    issues = analyze_missing_values_by_group(df, ["sex"])
    assert issues
    assert any(issue["severity"] in {"medium", "high"} for issue in issues)


def test_demographic_parity_gap_detected() -> None:
    df = pd.DataFrame(
        {
            "sex": ["M"] * 50 + ["F"] * 50,
            "target": [1] * 35 + [0] * 15 + [1] * 10 + [0] * 40,
        }
    )
    issues = analyze_subgroup_label_distribution(df, "target", ["sex"])
    assert len(issues) == 1
    assert issues[0]["severity"] == "high"
    assert issues[0]["metrics"]["demographic_parity_gap"] > 0.15


def test_sensitive_correlation_detected() -> None:
    df = pd.DataFrame(
        {
            "race": ["A"] * 40 + ["B"] * 40,
            "target": [1] * 32 + [0] * 8 + [1] * 10 + [0] * 30,
        }
    )
    issues = analyze_sensitive_correlations(df, "target", ["race"])
    assert len(issues) == 1
    assert issues[0]["severity"] in {"medium", "high"}


def test_run_layer1_audit_deterministic_ordering() -> None:
    df = pd.DataFrame(
        {
            "sex": ["M"] * 80 + ["F"] * 20,
            "race": ["A"] * 50 + ["B"] * 50,
            "feature": [1] * 100,
            "target": [0] * 75 + [1] * 25,
        }
    )

    report_a = run_layer1_audit(df, "target", ["sex", "race"])
    report_b = run_layer1_audit(df, "target", ["sex", "race"])

    assert report_a == report_b
    severities = [issue["severity"] for issue in report_a["issues"]]
    assert severities == sorted(severities, key=lambda x: {"high": 0, "medium": 1, "low": 2}[x])


def test_performance_100k_under_10_seconds() -> None:
    rows = 100_000
    df = pd.DataFrame(
        {
            "sex": ["M"] * (rows // 2) + ["F"] * (rows // 2),
            "race": ["A", "B", "C", "D"] * (rows // 4),
            "income": [0] * 75_000 + [1] * 25_000,
            "feature_a": list(range(rows)),
            "feature_b": [None if i % 10 == 0 else i % 7 for i in range(rows)],
        }
    )

    start = time.perf_counter()
    report = run_layer1_audit(df, "income", ["sex", "race"])
    elapsed = time.perf_counter() - start

    assert report["dataset_info"]["rows"] == rows
    assert elapsed < 10.0
