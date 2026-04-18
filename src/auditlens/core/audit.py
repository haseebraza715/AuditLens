from __future__ import annotations

from typing import Any

import pandas as pd

from auditlens.config import SEVERITY_ORDER, SEVERITY_THRESHOLDS
from auditlens.core.analyzers.class_distribution import analyze_class_distribution
from auditlens.core.analyzers.correlations import analyze_sensitive_correlations
from auditlens.core.analyzers.missing_values import analyze_missing_values_by_group
from auditlens.core.analyzers.subgroup_analysis import analyze_subgroup_label_distribution
from auditlens.core.severity import summarize_issues


def sort_issues(issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        issues,
        key=lambda issue: (SEVERITY_ORDER[issue["severity"]], issue["issue_id"]),
    )


def run_layer1_audit(
    df: pd.DataFrame,
    target_col: str,
    sensitive_cols: list[str],
    *,
    severity_thresholds: dict[str, dict[str, float]] | None = None,
) -> dict[str, Any]:
    thresholds = severity_thresholds if severity_thresholds is not None else SEVERITY_THRESHOLDS
    issues: list[dict[str, Any]] = []

    issues.extend(analyze_class_distribution(df, target_col, severity_thresholds=thresholds))
    issues.extend(analyze_missing_values_by_group(df, sensitive_cols, severity_thresholds=thresholds))
    issues.extend(
        analyze_sensitive_correlations(df, target_col, sensitive_cols, severity_thresholds=thresholds)
    )
    issues.extend(
        analyze_subgroup_label_distribution(df, target_col, sensitive_cols, severity_thresholds=thresholds)
    )

    sorted_issues = sort_issues(issues)

    return {
        "dataset_info": {
            "rows": int(len(df)),
            "columns": int(df.shape[1]),
            "target_column": target_col,
            "sensitive_columns": sensitive_cols,
        },
        "issues": sorted_issues,
        "summary": summarize_issues(sorted_issues),
        "severity_thresholds": thresholds,
    }
