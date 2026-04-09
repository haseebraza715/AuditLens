from __future__ import annotations

SEVERITY_THRESHOLDS = {
    "imbalance_ratio": {"medium": 1.5, "high": 3.0},
    "cramers_v": {"medium": 0.1, "high": 0.3},
    "demographic_parity_gap": {"medium": 0.05, "high": 0.15},
    "differential_missingness": {"medium": 0.05, "high": 0.15},
}

SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}
