from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency, pearsonr, pointbiserialr, spearmanr

from auditlens.core.severity import score_threshold_metric


def _is_numeric(series: pd.Series) -> bool:
    return pd.api.types.is_numeric_dtype(series)


def _is_categorical(series: pd.Series) -> bool:
    return not _is_numeric(series)


def _clean_pair(a: pd.Series, b: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Align two columns and drop rows with missing or non-finite values.

    Convention: rows are excluded from a correlation when either column is NaN
    or (for numeric columns) +/-inf. Non-finite values cannot be compared by a
    correlation coefficient, and silently dropping only NaN while keeping inf
    made `pd.qcut` raise on real-world data.
    """
    frame = pd.DataFrame({"a": a, "b": b})
    if _is_numeric(frame["a"]):
        frame = frame[np.isfinite(frame["a"].to_numpy(dtype=float))]
    if _is_numeric(frame["b"]):
        frame = frame[np.isfinite(frame["b"].to_numpy(dtype=float))]
    frame = frame.dropna()
    return frame["a"], frame["b"]


def _cramers_v(a: pd.Series, b: pd.Series) -> float:
    contingency = pd.crosstab(a.astype(str), b.astype(str))
    if contingency.shape[0] < 2 or contingency.shape[1] < 2:
        return 0.0

    chi2, _, _, _ = chi2_contingency(contingency, correction=False)
    if not np.isfinite(chi2) or chi2 < 0:
        # Zero-expected cells make chi2_contingency emit inf/nan; the table is
        # perfectly determined, which the clip below caps at a score of 1.0.
        return 1.0

    n = contingency.values.sum()
    if n == 0:
        return 0.0

    r, c = contingency.shape
    denom = n * (min(r, c) - 1)
    if denom <= 0:
        return 0.0

    value = float(np.sqrt(chi2 / denom))
    # Cramer's V is bounded by [0, 1]; chi2 can exceed n*(min(r,c)-1) on
    # small tables, which would otherwise inflate the score beyond 1.0.
    return min(max(value, 0.0), 1.0)


def _point_biserial(categorical_binary: pd.Series, continuous: pd.Series) -> float:
    labels = categorical_binary.astype(str).unique().tolist()
    if len(labels) != 2:
        return 0.0
    if continuous.nunique(dropna=True) < 2:
        # Zero-variance continuous column: coefficient is undefined, not zero.
        return 0.0
    mapping = {labels[0]: 0, labels[1]: 1}
    encoded = categorical_binary.astype(str).map(mapping)
    try:
        value, _ = pointbiserialr(encoded, continuous)
    except ValueError:
        return 0.0
    if not np.isfinite(value):
        return 0.0
    return min(max(float(value), -1.0), 1.0)


def _continuous_corr(a: pd.Series, b: pd.Series) -> tuple[str, float]:
    if a.nunique(dropna=True) < 2 or b.nunique(dropna=True) < 2:
        # Deterministic choice: a correlation is undefined when either input
        # is constant, so the score is reported as zero (no evidence).
        return "pearson", 0.0
    # Deterministic choice: use Spearman when either variable has low cardinality.
    if a.nunique(dropna=True) < 20 or b.nunique(dropna=True) < 20:
        try:
            value, _ = spearmanr(a, b)
        except ValueError:
            return "spearman", 0.0
        method = "spearman"
    else:
        try:
            value, _ = pearsonr(a, b)
        except ValueError:
            return "pearson", 0.0
        method = "pearson"
    if not np.isfinite(value):
        return method, 0.0
    return method, min(max(float(value), -1.0), 1.0)


def _bin_numeric(series: pd.Series, q: int = 4) -> pd.Series | None:
    """Bin a numeric series into quantile categories for Cramer's V.

    Returns None when the series cannot be binned (fewer than two distinct
    finite values, or quantile edges that collapse to a single category);
    callers then skip the column pair instead of fabricating a score.
    """
    clean = series.dropna()
    if _is_numeric(clean):
        clean = clean[np.isfinite(clean.to_numpy(dtype=float))]
    if clean.nunique(dropna=True) < 2:
        return None
    try:
        binned = pd.qcut(clean, q=q, duplicates="drop")
    except ValueError:
        return None
    if binned.nunique(dropna=True) < 2:
        return None
    return binned


def analyze_sensitive_correlations(
    df: pd.DataFrame,
    target_column: str,
    sensitive_columns: list[str],
    *,
    severity_thresholds: dict[str, dict[str, float]] | None = None,
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
                binned_target = _bin_numeric(clean_target)
                if binned_target is None:
                    continue
                method = "cramers_v_binned"
                score = _cramers_v(clean_sensitive, binned_target)
        elif _is_numeric(clean_sensitive) and _is_categorical(clean_target):
            if clean_target.astype(str).nunique() == 2:
                method = "point_biserial"
                score = _point_biserial(clean_target, clean_sensitive)
            else:
                binned_sensitive = _bin_numeric(clean_sensitive)
                if binned_sensitive is None:
                    continue
                method = "cramers_v_binned"
                score = _cramers_v(binned_sensitive, clean_target)
        else:
            method, score = _continuous_corr(clean_sensitive, clean_target)

        abs_score = abs(float(score))
        # Thresholds live under "cramers_v" in the shared table; pass the real
        # method name so the justification text is honest about the statistic.
        severity, justification = score_threshold_metric(
            method, abs_score, severity_thresholds=severity_thresholds
        )
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
