from __future__ import annotations

import io
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import PercentFormatter

_SPINE_COLOR = "#e0e0e0"
_FONT_COLOR = "#102a43"
_SEVERITY_COLORS = {"high": "#d32f2f", "medium": "#ed6c02", "low": "#455a64"}


def _apply_base_style(ax: Any, title: str) -> None:
    ax.set_title(title, fontsize=12, fontweight="bold", color=_FONT_COLOR, pad=10)
    ax.tick_params(colors=_FONT_COLOR, labelsize=9)
    for spine in ax.spines.values():
        spine.set_edgecolor(_SPINE_COLOR)
    ax.set_facecolor("#fafafa")


def _fig_to_png_bytes() -> bytes:
    buffer = io.BytesIO()
    plt.tight_layout(pad=1.5)
    plt.savefig(buffer, format="png", dpi=160, facecolor="white")
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

    fig, ax = plt.subplots(figsize=(5.2, 3.2))
    bars = ax.bar(labels, values, color=colors)
    ax.bar_label(bars, padding=3, fontweight="bold", color=_FONT_COLOR)
    ax.set_ylabel("Issue Count", color=_FONT_COLOR)
    ax.grid(axis="y", linestyle="--", alpha=0.25)
    _apply_base_style(ax, "Issue Severity Summary")
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

    sorted_counts = sorted(counts.items(), key=lambda item: item[1], reverse=True)
    labels = [item[0] for item in sorted_counts]
    values = [item[1] for item in sorted_counts]

    fig, ax = plt.subplots(figsize=(6.0, 3.4))
    color_scale = plt.cm.Blues(np.linspace(0.45, 0.9, len(labels)))
    bars = ax.barh(labels, values, color=color_scale)
    ax.invert_yaxis()
    ax.bar_label(bars, padding=3, color=_FONT_COLOR, fontweight="bold")
    ax.set_xlabel("Count", color=_FONT_COLOR)
    ax.grid(axis="x", linestyle="--", alpha=0.25)
    _apply_base_style(ax, "Issues by Type")
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
    total = max(sum(values), 1)
    majority_idx = int(np.argmax(values))
    colors = ["#c5cae9"] * len(values)
    colors[majority_idx] = "#3949ab"

    fig, ax = plt.subplots(figsize=(5.6, 3.2))
    bars = ax.bar(labels, values, color=colors)
    bar_labels = [f"{count} ({(count / total) * 100:.1f}%)" for count in values]
    ax.bar_label(bars, labels=bar_labels, padding=3, color=_FONT_COLOR, fontsize=8)
    ax.set_ylabel("Count", color=_FONT_COLOR)
    ax.grid(axis="y", linestyle="--", alpha=0.2)
    _apply_base_style(ax, "Target Class Distribution")
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
    fig, ax = plt.subplots(figsize=(6.2, 3.4))
    bars = ax.bar(labels, values, color="#00897b")
    ax.set_ylim(0, 1.0)
    ax.axhline(0.8, color="#ef6c00", linestyle="--", linewidth=1.2, label="80% threshold")
    ax.bar_label(bars, labels=[f"{v:.1%}" for v in values], padding=3, color=_FONT_COLOR, fontsize=8)
    ax.yaxis.set_major_formatter(PercentFormatter(1.0))
    ax.set_ylabel("Rate", color=_FONT_COLOR)
    ax.grid(axis="y", linestyle="--", alpha=0.25)
    ax.legend(frameon=False, fontsize=8, loc="upper right")
    _apply_base_style(ax, "Demographic Parity (Positive Label Rate)")
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
    fig, ax = plt.subplots(figsize=(max(4.8, 0.9 * len(labels)), 2.8))
    heatmap = ax.imshow(matrix, cmap="YlOrRd", aspect="auto", vmin=0.0, vmax=max(max(values), 0.3))
    fig.colorbar(heatmap, label="Absolute correlation")
    ax.set_yticks([0], ["target"])
    ax.set_xticks(range(len(labels)), labels, rotation=30, ha="right")
    for col_idx, value in enumerate(values):
        ax.text(col_idx, 0, f"{value:.2f}", ha="center", va="center", color=_FONT_COLOR, fontsize=8)
    _apply_base_style(ax, "Sensitive Correlation Heatmap (0.30 concern threshold)")
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

    fig, ax = plt.subplots(figsize=(max(5.0, 0.8 * len(feature_labels)), max(2.8, 0.8 * len(sensitive_labels))))
    heatmap = ax.imshow(matrix, cmap="Blues", aspect="auto", vmin=0.0, vmax=max(float(matrix.max()), 0.15))
    fig.colorbar(heatmap, label="Missingness gap")
    ax.set_yticks(range(len(sensitive_labels)), sensitive_labels)
    ax.set_xticks(range(len(feature_labels)), feature_labels, rotation=30, ha="right")
    for row_idx in range(matrix.shape[0]):
        for col_idx in range(matrix.shape[1]):
            ax.text(col_idx, row_idx, f"{matrix[row_idx, col_idx]:.2f}", ha="center", va="center", color=_FONT_COLOR, fontsize=8)
    _apply_base_style(ax, "Differential Missingness Heatmap (0.05 concern threshold)")
    return _fig_to_png_bytes()


def build_fairness_overview_chart(layer1_report: dict[str, Any] | None) -> bytes:
    issues = list((layer1_report or {}).get("issues", []) or [])
    labels: list[str] = []
    values: list[float] = []
    severities: list[str] = []

    for issue in issues:
        issue_type = str(issue.get("type", "")).strip()
        severity = str(issue.get("severity", "low")).lower()
        metrics = issue.get("metrics", {}) or {}
        if issue_type == "demographic_parity_gap":
            labels.append(f"{issue_type}:{metrics.get('sensitive_column', 'group')}")
            values.append(float(metrics.get("demographic_parity_gap", 0.0) or 0.0))
            severities.append(severity)
        elif issue_type == "sensitive_correlation":
            labels.append(f"{issue_type}:{metrics.get('sensitive_column', 'group')}")
            values.append(float(metrics.get("absolute_correlation", 0.0) or 0.0))
            severities.append(severity)

    if not labels:
        labels = ["no fairness metrics"]
        values = [0.0]
        severities = ["low"]

    chart_colors = [_SEVERITY_COLORS.get(level, _SEVERITY_COLORS["low"]) for level in severities]

    fig, ax = plt.subplots(figsize=(max(7.0, 0.4 * len(labels)), 3.2))
    y_pos = np.arange(len(labels))
    bars = ax.barh(y_pos, values, color=chart_colors)
    ax.set_yticks(y_pos, labels)
    ax.invert_yaxis()
    ax.axvline(0.1, color="#ef6c00", linestyle="--", linewidth=1.2, label="0.10 threshold")
    ax.bar_label(bars, labels=[f"{value:.2f}" for value in values], padding=3, color=_FONT_COLOR, fontsize=8)
    ax.grid(axis="x", linestyle="--", alpha=0.25)
    ax.legend(frameon=False, fontsize=8, loc="lower right")
    ax.set_xlabel("Gap magnitude", color=_FONT_COLOR)
    _apply_base_style(ax, "Fairness Overview (Gap Metrics)")
    return _fig_to_png_bytes()
