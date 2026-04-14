from __future__ import annotations

import io
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def _fig_to_png_bytes() -> bytes:
    buffer = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buffer, format="png", dpi=140)
    plt.close()
    buffer.seek(0)
    return buffer.read()


def build_severity_summary_chart(layer1_report: dict[str, Any] | None) -> bytes:
    summary = (layer1_report or {}).get("summary", {}) or {}
    labels = ["High", "Medium", "Low"]
    values = [
        int(summary.get("high_severity", 0) or 0),
        int(summary.get("medium_severity", 0) or 0),
        int(summary.get("low_severity", 0) or 0),
    ]
    colors = ["#c62828", "#ef6c00", "#2e7d32"]

    plt.figure(figsize=(5.2, 3.2))
    plt.bar(labels, values, color=colors)
    plt.title("Issue Severity Summary")
    plt.ylabel("Issue Count")
    return _fig_to_png_bytes()


def build_issue_type_chart(final_report: dict[str, Any]) -> bytes:
    issues = list(final_report.get("issues", []) or [])
    counts: dict[str, int] = {}
    for entry in issues:
        statistical_issue = entry.get("statistical_issue", {}) or {}
        issue_type = str(statistical_issue.get("type", "unknown")).replace("_", " ")
        counts[issue_type] = counts.get(issue_type, 0) + 1

    if not counts:
        counts = {"no issues": 1}

    labels = list(counts.keys())
    values = list(counts.values())

    plt.figure(figsize=(6.0, 3.4))
    plt.barh(labels, values, color="#1565c0")
    plt.title("Issues by Type")
    plt.xlabel("Count")
    return _fig_to_png_bytes()


def build_class_distribution_chart(layer1_report: dict[str, Any] | None) -> bytes:
    issues = list((layer1_report or {}).get("issues", []) or [])
    class_counts: dict[str, int] = {}
    for issue in issues:
        if issue.get("type") != "class_imbalance":
            continue
        metrics = issue.get("metrics", {}) or {}
        counts = metrics.get("class_counts", {}) or {}
        if isinstance(counts, dict):
            class_counts = {str(k): int(v) for k, v in counts.items()}
            break

    if not class_counts:
        class_counts = {"unknown": 1}

    labels = list(class_counts.keys())
    values = list(class_counts.values())
    plt.figure(figsize=(5.6, 3.2))
    plt.bar(labels, values, color="#6a1b9a")
    plt.title("Target Class Distribution")
    plt.ylabel("Count")
    return _fig_to_png_bytes()


def build_demographic_parity_chart(layer1_report: dict[str, Any] | None) -> bytes:
    issues = list((layer1_report or {}).get("issues", []) or [])
    best_issue: dict[str, Any] | None = None
    best_gap = -1.0
    for issue in issues:
        if issue.get("type") != "demographic_parity_gap":
            continue
        gap = float((issue.get("metrics", {}) or {}).get("demographic_parity_gap", 0.0) or 0.0)
        if gap > best_gap:
            best_gap = gap
            best_issue = issue

    rates = ((best_issue or {}).get("metrics", {}) or {}).get("positive_rates", {}) or {}
    if not isinstance(rates, dict) or not rates:
        rates = {"no-data": 0.0}

    labels = list(rates.keys())
    values = [float(v) for v in rates.values()]
    plt.figure(figsize=(6.2, 3.4))
    plt.bar(labels, values, color="#00897b")
    plt.ylim(0, 1.0)
    plt.title("Demographic Parity (Positive Label Rate)")
    plt.ylabel("Rate")
    return _fig_to_png_bytes()


def build_correlation_heatmap(layer1_report: dict[str, Any] | None) -> bytes:
    issues = list((layer1_report or {}).get("issues", []) or [])
    labels: list[str] = []
    values: list[float] = []
    for issue in issues:
        if issue.get("type") != "sensitive_correlation":
            continue
        metrics = issue.get("metrics", {}) or {}
        labels.append(str(metrics.get("sensitive_column", "unknown")))
        values.append(float(metrics.get("absolute_correlation", 0.0) or 0.0))

    if not labels:
        labels = ["no-data"]
        values = [0.0]

    matrix = np.array([values], dtype=float)
    plt.figure(figsize=(max(4.8, 0.9 * len(labels)), 2.8))
    plt.imshow(matrix, cmap="YlOrRd", aspect="auto", vmin=0.0, vmax=max(max(values), 0.3))
    plt.colorbar(label="Absolute correlation")
    plt.yticks([0], ["target"])
    plt.xticks(range(len(labels)), labels, rotation=30, ha="right")
    plt.title("Sensitive Correlation Heatmap")
    return _fig_to_png_bytes()


def build_missingness_heatmap(layer1_report: dict[str, Any] | None) -> bytes:
    issues = list((layer1_report or {}).get("issues", []) or [])
    sensitive_labels: list[str] = []
    feature_labels: list[str] = []
    gap_map: dict[tuple[str, str], float] = {}

    for issue in issues:
        if issue.get("type") != "differential_missingness":
            continue
        metrics = issue.get("metrics", {}) or {}
        sensitive = str(metrics.get("sensitive_column", "unknown"))
        feature = str(metrics.get("feature_column", "unknown"))
        gap = float(metrics.get("missingness_gap", 0.0) or 0.0)
        if sensitive not in sensitive_labels:
            sensitive_labels.append(sensitive)
        if feature not in feature_labels:
            feature_labels.append(feature)
        gap_map[(sensitive, feature)] = gap

    if not sensitive_labels or not feature_labels:
        sensitive_labels = ["no-data"]
        feature_labels = ["no-data"]
        gap_map = {("no-data", "no-data"): 0.0}

    matrix = np.zeros((len(sensitive_labels), len(feature_labels)))
    for i, sensitive in enumerate(sensitive_labels):
        for j, feature in enumerate(feature_labels):
            matrix[i, j] = gap_map.get((sensitive, feature), 0.0)

    plt.figure(figsize=(max(5.0, 0.8 * len(feature_labels)), max(2.8, 0.8 * len(sensitive_labels))))
    plt.imshow(matrix, cmap="Blues", aspect="auto", vmin=0.0, vmax=max(float(matrix.max()), 0.15))
    plt.colorbar(label="Missingness gap")
    plt.yticks(range(len(sensitive_labels)), sensitive_labels)
    plt.xticks(range(len(feature_labels)), feature_labels, rotation=30, ha="right")
    plt.title("Differential Missingness Heatmap")
    return _fig_to_png_bytes()
