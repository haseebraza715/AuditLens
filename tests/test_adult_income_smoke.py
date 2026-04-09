from __future__ import annotations

from pathlib import Path

import pandas as pd

from backend.layer1.audit import run_layer1_audit


ADULT_COLUMNS = [
    "age",
    "workclass",
    "fnlwgt",
    "education",
    "education_num",
    "marital_status",
    "occupation",
    "relationship",
    "race",
    "sex",
    "capital_gain",
    "capital_loss",
    "hours_per_week",
    "native_country",
    "income",
]


def test_adult_income_smoke() -> None:
    fixture_path = Path(__file__).resolve().parent / "fixtures" / "adult.data"
    df = pd.read_csv(
        fixture_path,
        header=None,
        names=ADULT_COLUMNS,
        skipinitialspace=True,
        na_values="?",
    )

    report = run_layer1_audit(df, "income", ["sex", "race"])

    issue_map = {issue["issue_id"]: issue for issue in report["issues"]}

    class_issue = issue_map.get("class_imbalance_income")
    assert class_issue is not None
    assert class_issue["metrics"]["imbalance_ratio"] > 3.0

    parity_sex = issue_map.get("demographic_parity_sex_income")
    assert parity_sex is not None
    assert parity_sex["metrics"]["demographic_parity_gap"] > 0.15

    corr_sex = issue_map.get("correlation_sex_income")
    assert corr_sex is not None
    assert abs(corr_sex["metrics"]["correlation_value"]) > 0.1
