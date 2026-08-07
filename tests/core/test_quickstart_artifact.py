from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd

from auditlens import audit

ROOT = Path(__file__).resolve().parents[2]
EXPECTED_SHA256 = "f63570b45c870afb874ae39eb2b366e30f5a170b4fc4b3c0bf4c59172a43df68"


def test_committed_quickstart_is_reproducible() -> None:
    path = ROOT / "examples" / "quickstart.csv"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == EXPECTED_SHA256
    report = audit(
        pd.read_csv(path),
        target_col="target",
        sensitive_cols=["group", "sex"],
    )
    assert report.status is None  # Layer 1-only reports do not claim Layer 2 status.
    assert report.summary == {
        "total_issues": 2,
        "high_severity": 2,
        "medium_severity": 0,
        "low_severity": 0,
    }
    assert len(report.issues) == 2

    by_id = {issue.issue_id: issue for issue in report.issues}
    corr = by_id["correlation_sex_target"]
    assert corr.type == "sensitive_correlation"
    assert corr.severity == "high"
    assert corr.metrics["method"] == "point_biserial"
    assert corr.metrics["sample_size"] == 8
    assert abs(corr.metrics["absolute_correlation"] - 0.5) < 1e-9

    parity = by_id["demographic_parity_sex_target"]
    assert parity.type == "demographic_parity_gap"
    assert parity.severity == "high"
    assert parity.metrics["positive_class"] == "1"
    assert abs(parity.metrics["demographic_parity_gap"] - 0.5) < 1e-9
    assert abs(parity.metrics["positive_rates"]["F"] - 0.25) < 1e-9
    assert abs(parity.metrics["positive_rates"]["M"] - 0.75) < 1e-9
    assert parity.metrics["sample_size"] == 8


def test_quickstart_markdown_matches_committed_example() -> None:
    path = ROOT / "examples" / "quickstart.csv"
    report = audit(
        pd.read_csv(path),
        target_col="target",
        sensitive_cols=["group", "sex"],
    )
    markdown = report.to_markdown()
    committed = (ROOT / "docs" / "examples" / "quickstart-result.md").read_text(encoding="utf-8")
    assert "Total issues: `2`" in committed
    assert "Demographic parity gap for 'sex' is 0.500 for target 'target'" in committed
    assert markdown in committed
