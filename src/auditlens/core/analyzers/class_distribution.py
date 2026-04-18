from __future__ import annotations

from typing import Any

import pandas as pd

from auditlens.core.severity import score_threshold_metric


def _normalize_series(series: pd.Series) -> pd.Series:
    return series.fillna("__MISSING__").astype(str)


def analyze_class_distribution(
    df: pd.DataFrame,
    target_column: str,
    *,
    severity_thresholds: dict[str, dict[str, float]] | None = None,
) -> list[dict[str, Any]]:
    target = _normalize_series(df[target_column])
    counts = target.value_counts(dropna=False)
    proportions = (counts / counts.sum()).to_dict()

    gini_impurity = 1.0 - sum(p * p for p in proportions.values())
    issues: list[dict[str, Any]] = []

    if counts.empty:
        return issues

    if len(counts) == 1:
        issues.append(
            {
                "issue_id": f"class_imbalance_{target_column}",
                "type": "class_imbalance",
                "description": f"Target column '{target_column}' has only one class",
                "affected_column": target_column,
                "severity": "high",
                "metrics": {
                    "class_counts": counts.to_dict(),
                    "class_percentages": proportions,
                    "gini_impurity": gini_impurity,
                    "imbalance_ratio": float("inf"),
                },
                "justification": "Single-class target cannot support supervised classification.",
            }
        )
        return issues

    majority_label = counts.idxmax()
    majority_count = int(counts.max())
    minority_label = counts.idxmin()
    minority_count = int(counts.min())

    imbalance_ratio = float("inf") if minority_count == 0 else majority_count / minority_count

    if len(counts) == 2:
        severity, justification = score_threshold_metric(
            "imbalance_ratio", imbalance_ratio, severity_thresholds=severity_thresholds
        )
    else:
        min_prop = float(min(proportions.values()))
        if min_prop < 0.05:
            severity = "high"
            justification = (
                f"minimum class representation={min_prop:.4f} is below high threshold 0.0500"
            )
        elif min_prop < 0.10:
            severity = "medium"
            justification = (
                f"minimum class representation={min_prop:.4f} is below medium threshold 0.1000"
            )
        else:
            severity = "low"
            justification = f"minimum class representation={min_prop:.4f} is within low-risk threshold"

    if severity != "low":
        issues.append(
            {
                "issue_id": f"class_imbalance_{target_column}",
                "type": "class_imbalance",
                "description": (
                    f"Target column '{target_column}' has imbalance ratio of {imbalance_ratio:.3f}:1"
                ),
                "affected_column": target_column,
                "severity": severity,
                "metrics": {
                    "majority_class": str(majority_label),
                    "minority_class": str(minority_label),
                    "majority_count": majority_count,
                    "minority_count": minority_count,
                    "imbalance_ratio": imbalance_ratio,
                    "class_counts": counts.to_dict(),
                    "class_percentages": proportions,
                    "gini_impurity": gini_impurity,
                },
                "justification": justification,
            }
        )

    return issues
