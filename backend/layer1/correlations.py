from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency, pearsonr, pointbiserialr, spearmanr

from backend.layer1.severity_scorer import score_threshold_metric


def _is_numeric(series: pd.Series) -> bool:
    return pd.api.types.is_numeric_dtype(series)


def _is_categorical(series: pd.Series) -> bool:
    return not _is_numeric(series)


def _clean_pair(a: pd.Series, b: pd.Series) -> tuple[pd.Series, pd.Series]:
    clean = pd.DataFrame({"a": a, "b": b}).dropna()
    return clean["a"], clean["b"]


def _cramers_v(a: pd.Series, b: pd.Series) -> float:
    contingency = pd.crosstab(a.astype(str), b.astype(str))
    if contingency.shape[0] < 2 or contingency.shape[1] < 2:
        return 0.0

    chi2, _, _, _ = chi2_contingency(contingency, correction=False)
    n = contingency.values.sum()
    if n == 0:
        return 0.0

    r, c = contingency.shape
    denom = n * (min(r, c) - 1)
    if denom <= 0:
        return 0.0

    return float(np.sqrt(chi2 / denom))


def _point_biserial(categorical_binary: pd.Series, continuous: pd.Series) -> float:
    labels = categorical_binary.astype(str).unique().tolist()
    if len(labels) != 2:
        return 0.0
    mapping = {labels[0]: 0, labels[1]: 1}
    encoded = categorical_binary.astype(str).map(mapping)
    value, _ = pointbiserialr(encoded, continuous)
    return 0.0 if np.isnan(value) else float(value)


def _continuous_corr(a: pd.Series, b: pd.Series) -> tuple[str, float]:
    # Deterministic choice: use Spearman when either variable has low cardinality.
    if a.nunique(dropna=True) < 20 or b.nunique(dropna=True) < 20:
        value, _ = spearmanr(a, b)
        return "spearman", 0.0 if np.isnan(value) else float(value)
    value, _ = pearsonr(a, b)
    return "pearson", 0.0 if np.isnan(value) else float(value)


def analyze_sensitive_correlations(
    df: pd.DataFrame,
    target_column: str,
    sensitive_columns: list[str],
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    target = df[target_column]

    for sensitive_col in sensitive_columns:
        sensitive = df[sensitive_col]
        clean_sensitive, clean_target = _clean_pair(sensitive, target)
        if len(clean_sensitive) < 3:
            continue

        method = ""
        score = 0.0

        if _is_categorical(clean_sensitive) and _is_categorical(clean_target):
            method = "cramers_v"
            score = _cramers_v(clean_sensitive, clean_target)
        elif _is_categorical(clean_sensitive) and _is_numeric(clean_target):
            if clean_sensitive.astype(str).nunique() == 2:
                method = "point_biserial"
                score = _point_biserial(clean_sensitive, clean_target)
            else:
                method = "cramers_v_binned"
                binned_target = pd.qcut(clean_target, q=4, duplicates="drop")
                score = _cramers_v(clean_sensitive, binned_target)
        elif _is_numeric(clean_sensitive) and _is_categorical(clean_target):
            if clean_target.astype(str).nunique() == 2:
                method = "point_biserial"
                score = _point_biserial(clean_target, clean_sensitive)
            else:
                method = "cramers_v_binned"
                binned_sensitive = pd.qcut(clean_sensitive, q=4, duplicates="drop")
                score = _cramers_v(binned_sensitive, clean_target)
        else:
            method, score = _continuous_corr(clean_sensitive, clean_target)

        abs_score = abs(float(score))
        severity, justification = score_threshold_metric("cramers_v", abs_score)
        if severity == "low":
            continue

        issues.append(
            {
                "issue_id": f"correlation_{sensitive_col}_{target_column}",
                "type": "sensitive_correlation",
                "description": (
                    f"Correlation score between sensitive column '{sensitive_col}' and target "
                    f"'{target_column}' is {abs_score:.3f}"
                ),
                "affected_column": sensitive_col,
                "severity": severity,
                "metrics": {
                    "sensitive_column": sensitive_col,
                    "target_column": target_column,
                    "method": method,
                    "correlation_value": float(score),
                    "absolute_correlation": abs_score,
                    "sample_size": int(len(clean_sensitive)),
                },
                "justification": justification,
            }
        )

    return issues
