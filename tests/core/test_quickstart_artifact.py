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
    assert isinstance(report.summary, dict)
    assert len(report.issues) == 2
