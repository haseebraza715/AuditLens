"""Golden reproducibility tests for the committed UCI Adult evidence artifact.

The evidence pipeline is defined in scripts/evidence_adult.py and its output is
committed under docs/evidence/. These tests re-run the deterministic Layer 1
audit on the vendored public UCI Adult fixture and verify:

* the fixture SHA-256 stays pinned to the recorded value;
* issue ordering, summary, and core magnitudes match the committed golden JSON;
* the script's JSON and Markdown regenerate byte-for-byte identically;
* a seeded balanced negative control produces no parity/correlation findings;
* the report still renders to Markdown and PDF.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd

from auditlens import audit

REPO_ROOT = Path(__file__).resolve().parents[2]

EXPECTED_SHA256 = "5b00264637dbfec36bdeaab5676b0b309ff9eb788d63554ca0a249491c86603d"

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


def _load_evidence_module():
    spec = importlib.util.spec_from_file_location("evidence_adult", REPO_ROOT / "scripts" / "evidence_adult.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_adult() -> pd.DataFrame:
    path = REPO_ROOT / "tests" / "fixtures" / "adult.data"
    return pd.read_csv(
        path,
        header=None,
        names=ADULT_COLUMNS,
        skipinitialspace=True,
        na_values="?",
    )


def _golden() -> dict:
    path = REPO_ROOT / "docs" / "evidence" / "adult-income-report.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _run_adult_audit():
    return audit(_load_adult(), target_col="income", sensitive_cols=["sex", "race"])


# --- Fixture integrity ------------------------------------------------------


def test_adult_fixture_sha256_is_pinned() -> None:
    path = REPO_ROOT / "tests" / "fixtures" / "adult.data"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == EXPECTED_SHA256


def test_evidence_script_pins_same_sha256() -> None:
    mod = _load_evidence_module()
    assert mod.EXPECTED_SHA256 == EXPECTED_SHA256
    assert mod.TARGET_COL == "income"
    assert mod.SENSITIVE_COLS == ["sex", "race"]


# --- Golden ordering and magnitudes ----------------------------------------


def test_adult_issue_ordering_matches_golden() -> None:
    report = _run_adult_audit()
    golden = _golden()

    assert report.status is None  # Layer 1 only: no Layer 2 claim.
    assert report.summary == golden["summary"]
    assert report.summary == {
        "total_issues": 6,
        "high_severity": 3,
        "medium_severity": 3,
        "low_severity": 0,
    }

    live = report.to_dict()["layer1_report"]["issues"]
    golden_issues = golden["layer1_report"]["issues"]
    assert [i["issue_id"] for i in live] == [g["issue_id"] for g in golden_issues]
    for lv, gv in zip(live, golden_issues):
        assert lv["type"] == gv["type"]
        assert lv["severity"] == gv["severity"]


def _assert_metrics_close(live_metrics: dict, golden_metrics: dict, tol: float) -> None:
    assert set(live_metrics) == set(golden_metrics)
    for key in golden_metrics:
        if isinstance(golden_metrics[key], dict):
            _assert_metrics_close(live_metrics[key], golden_metrics[key], tol)
        elif isinstance(golden_metrics[key], float):
            assert abs(live_metrics[key] - golden_metrics[key]) <= tol, key
        else:
            assert live_metrics[key] == golden_metrics[key], key


def test_adult_core_magnitudes_match_golden_and_literature() -> None:
    report = _run_adult_audit()
    golden = _golden()
    live = report.to_dict()["layer1_report"]["issues"]

    for lv, gv in zip(live, golden["layer1_report"]["issues"]):
        _assert_metrics_close(lv["metrics"], gv["metrics"], tol=1e-4)

    by_id = {i["issue_id"]: i for i in live}
    imbalance = by_id["class_imbalance_income"]["metrics"]["imbalance_ratio"]
    assert 3.0 < imbalance < 3.3  # ~3.15:1, the published <=50K majority ratio.
    assert by_id["demographic_parity_sex_income"]["metrics"]["demographic_parity_gap"] > 0.15
    assert by_id["demographic_parity_race_income"]["metrics"]["demographic_parity_gap"] > 0.15
    assert abs(by_id["correlation_sex_income"]["metrics"]["correlation_value"]) > 0.1
    assert by_id["missingness_gap_race_native_country"]["metrics"]["missingness_gap"] > 0.05


# --- Byte-stable regeneration ----------------------------------------------


def test_adult_json_and_markdown_regenerate_byte_identical() -> None:
    mod = _load_evidence_module()
    df = mod.load_adult()
    report = audit(df, target_col=mod.TARGET_COL, sensitive_cols=mod.SENSITIVE_COLS)
    sha256 = mod.fixture_sha256()

    committed_json = (REPO_ROOT / "docs" / "evidence" / "adult-income-report.json").read_text(encoding="utf-8")
    committed_md = (REPO_ROOT / "docs" / "evidence" / "adult-income-report.md").read_text(encoding="utf-8")
    assert mod.report_to_json(report) == committed_json
    assert mod.build_markdown(report, sha256, len(df)) == committed_md


# --- Negative control -------------------------------------------------------


def test_balanced_random_negative_control_no_high_parity_or_correlation() -> None:
    rng = np.random.default_rng(42)
    n = 20_000
    df = pd.DataFrame(
        {
            "sex": rng.choice(["M", "F"], size=n),
            "race": rng.choice(["A", "B"], size=n),
            "income": rng.choice([0, 1], size=n),
            "age": rng.integers(18, 90, size=n),
        }
    )

    report = audit(df, target_col="income", sensitive_cols=["sex", "race"])
    assert report.summary["high_severity"] == 0
    assert not any(i.type in {"demographic_parity_gap", "sensitive_correlation"} for i in report.issues)

    rerun = audit(df, target_col="income", sensitive_cols=["sex", "race"])
    assert [i.issue_id for i in rerun.issues] == [i.issue_id for i in report.issues]


# --- Render smoke -----------------------------------------------------------


def test_adult_report_renders_markdown_and_pdf(tmp_path) -> None:
    report = _run_adult_audit()
    markdown = report.to_markdown()
    assert "Rows: `32561`" in markdown
    assert "Total issues: `6`" in markdown
    assert "High severity: `3`" in markdown

    pdf_path = tmp_path / "adult-report.pdf"
    report.to_pdf(str(pdf_path))
    raw = pdf_path.read_bytes()
    assert raw.startswith(b"%PDF")
    assert len(raw) > 1000
