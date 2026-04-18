from __future__ import annotations

from typing import Any

import pandas as pd

from auditlens.core.severity import score_threshold_metric


def _resolve_positive_class(target: pd.Series) -> str:
    normalized = target.fillna("__MISSING__").astype(str)
    counts = normalized.value_counts(dropna=False)
    if len(counts) <= 1:
        return str(counts.index[0])

    min_count = counts.min()
    candidates = sorted(str(label) for label, count in counts.items() if count == min_count)
    return candidates[0]


def analyze_subgroup_label_distribution(
    df: pd.DataFrame,
    target_column: str,
    sensitive_columns: list[str],
    positive_class: str | None = None,
    *,
    severity_thresholds: dict[str, dict[str, float]] | None = None,
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []

    target = df[target_column].fillna("__MISSING__").astype(str)
    resolved_positive = positive_class or _resolve_positive_class(target)

    for sensitive_col in sensitive_columns:
        groups = df[sensitive_col].fillna("__MISSING_GROUP__").astype(str)
        rates: dict[str, float] = {}

        for group_value in sorted(groups.unique().tolist()):
            mask = groups == group_value
            group_size = int(mask.sum())
            if group_size == 0:
                continue
            rate = float((target[mask] == resolved_positive).mean())
            rates[group_value] = rate

        if len(rates) < 2:
            continue

        max_rate = max(rates.values())
        min_rate = min(rates.values())
        gap = max_rate - min_rate

        severity, justification = score_threshold_metric(
            "demographic_parity_gap", gap, severity_thresholds=severity_thresholds
        )
        if severity == "low":
            continue

        highest_group = max(rates, key=rates.get)
        lowest_group = min(rates, key=rates.get)

        issues.append(
            {
                "issue_id": f"demographic_parity_{sensitive_col}_{target_column}",
                "type": "demographic_parity_gap",
                "description": (
                    f"Demographic parity gap for '{sensitive_col}' is {gap:.3f} for target '{target_column}'"
                ),
                "affected_column": sensitive_col,
                "severity": severity,
                "metrics": {
                    "sensitive_column": sensitive_col,
                    "target_column": target_column,
                    "positive_class": resolved_positive,
                    "positive_rates": rates,
                    "demographic_parity_gap": gap,
                    "highest_positive_rate_group": highest_group,
                    "lowest_positive_rate_group": lowest_group,
                },
                "justification": justification,
            }
        )

    return issues
