from __future__ import annotations

import io
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


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
