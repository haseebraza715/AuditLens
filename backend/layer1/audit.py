from __future__ import annotations

from typing import Any

import pandas as pd

from backend.layer1.class_distribution import analyze_class_distribution
from backend.layer1.correlations import analyze_sensitive_correlations
from backend.layer1.missing_values import analyze_missing_values_by_group
from backend.layer1.severity_scorer import summarize_issues
from backend.layer1.subgroup_analysis import analyze_subgroup_label_distribution
from backend.utils.config import SEVERITY_ORDER


def sort_issues(issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        issues,
        key=lambda issue: (SEVERITY_ORDER[issue["severity"]], issue["issue_id"]),
    )


def run_layer1_audit(
    df: pd.DataFrame,
    target_col: str,
    sensitive_cols: list[str],
) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []

    issues.extend(analyze_class_distribution(df, target_col))
    issues.extend(analyze_missing_values_by_group(df, sensitive_cols))
    issues.extend(analyze_sensitive_correlations(df, target_col, sensitive_cols))
    issues.extend(analyze_subgroup_label_distribution(df, target_col, sensitive_cols))

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
    }
