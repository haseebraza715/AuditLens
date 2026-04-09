from __future__ import annotations

from typing import Any

import pandas as pd

from backend.layer1.severity_scorer import score_threshold_metric


def analyze_missing_values_by_group(
    df: pd.DataFrame,
    sensitive_columns: list[str],
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []

    for sensitive_col in sensitive_columns:
        group_series = df[sensitive_col].fillna("__MISSING_GROUP__").astype(str)
        group_values = sorted(group_series.unique().tolist())

        for feature_col in df.columns:
            if feature_col == sensitive_col:
                continue

            missing_rates: dict[str, float] = {}
            for group_value in group_values:
                mask = group_series == group_value
                group_size = int(mask.sum())
                if group_size == 0:
                    continue
                rate = float(df.loc[mask, feature_col].isna().mean())
                missing_rates[group_value] = rate

            if len(missing_rates) < 2:
                continue

            max_rate = max(missing_rates.values())
            min_rate = min(missing_rates.values())
            gap = max_rate - min_rate

            severity, justification = score_threshold_metric("differential_missingness", gap)
            if severity == "low":
                continue

            highest_group = max(missing_rates, key=missing_rates.get)
            lowest_group = min(missing_rates, key=missing_rates.get)

            issues.append(
                {
                    "issue_id": f"missingness_gap_{sensitive_col}_{feature_col}",
                    "type": "differential_missingness",
                    "description": (
                        f"Missingness differs by {gap:.3f} for '{feature_col}' across '{sensitive_col}' groups"
                    ),
                    "affected_column": feature_col,
                    "severity": severity,
                    "metrics": {
                        "sensitive_column": sensitive_col,
                        "feature_column": feature_col,
                        "missingness_gap": gap,
                        "missingness_rates": missing_rates,
                        "highest_missing_group": highest_group,
                        "lowest_missing_group": lowest_group,
                    },
                    "justification": justification,
                }
            )

    return issues
