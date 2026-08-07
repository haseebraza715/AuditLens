from __future__ import annotations

from auditlens.config import SEVERITY_THRESHOLDS


def score_threshold_metric(
    metric_name: str,
    value: float,
    *,
    severity_thresholds: dict[str, dict[str, float]] | None = None,
) -> tuple[str, str]:
    table = severity_thresholds if severity_thresholds is not None else SEVERITY_THRESHOLDS
    # All correlation statistics (point_biserial, spearman, pearson, cramers_v)
    # share the same magnitude thresholds; fall back so custom threshold tables
    # that only define "cramers_v" keep working.
    thresholds = table.get(metric_name) or table["cramers_v"]
    high = thresholds["high"]
    medium = thresholds["medium"]

    if value > high:
        return "high", f"{metric_name}={value:.4f} exceeds high threshold {high:.4f}"
    if value > medium:
        return "medium", f"{metric_name}={value:.4f} exceeds medium threshold {medium:.4f}"
    return "low", f"{metric_name}={value:.4f} is within low-risk threshold"


def summarize_issues(issues: list[dict]) -> dict[str, int]:
    high_count = sum(1 for issue in issues if issue["severity"] == "high")
    medium_count = sum(1 for issue in issues if issue["severity"] == "medium")
    low_count = sum(1 for issue in issues if issue["severity"] == "low")

    return {
        "total_issues": len(issues),
        "high_severity": high_count,
        "medium_severity": medium_count,
        "low_severity": low_count,
    }
