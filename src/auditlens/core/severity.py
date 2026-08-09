from __future__ import annotations

import math

from auditlens.config import SEVERITY_THRESHOLDS
from auditlens.exceptions import AuditLensError


def validate_severity_thresholds(thresholds: dict[str, dict[str, float]]) -> None:
    """Validate a severity threshold table up front for a clear, early error."""
    if not isinstance(thresholds, dict):
        raise AuditLensError("severity_thresholds must be a dict of metric -> {'medium', 'high'}")
    for metric_name, bounds in thresholds.items():
        if not isinstance(bounds, dict):
            raise AuditLensError(
                f"Severity thresholds for metric '{metric_name}' must be a dict, got {bounds!r}"
            )
        try:
            medium = float(bounds["medium"])
            high = float(bounds["high"])
        except (KeyError, TypeError, ValueError) as exc:
            raise AuditLensError(
                f"Severity thresholds for metric '{metric_name}' must define numeric "
                f"'medium' and 'high' values, got {bounds!r}"
            ) from exc
        if not (math.isfinite(medium) and math.isfinite(high)):
            raise AuditLensError(
                f"Severity thresholds for metric '{metric_name}' must be finite, got {bounds!r}"
            )
        if medium < 0 or high < 0 or medium > high:
            raise AuditLensError(
                f"Severity thresholds for metric '{metric_name}' must satisfy "
                f"0 <= medium <= high, got {bounds!r}"
            )


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
    thresholds = table.get(metric_name)
    if thresholds is None:
        thresholds = table.get("cramers_v")
    if thresholds is None:
        raise AuditLensError(
            f"No severity thresholds defined for metric '{metric_name}' "
            f"or the shared 'cramers_v' fallback in the provided threshold table"
        )
    try:
        high = float(thresholds["high"])
        medium = float(thresholds["medium"])
    except (KeyError, TypeError, ValueError) as exc:
        raise AuditLensError(
            f"Severity thresholds for metric '{metric_name}' must define "
            f"numeric 'medium' and 'high' values, got {thresholds!r}"
        ) from exc

    if not math.isfinite(value):
        # A non-finite metric is a code-level invariant violation: reporting it
        # as any severity level would silently mislabel an undefined statistic.
        raise AuditLensError(
            f"Metric '{metric_name}' has a non-finite value ({value!r}); "
            f"analyzers must emit finite scores"
        )

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
