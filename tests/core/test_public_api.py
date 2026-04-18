from __future__ import annotations

import pandas as pd

from auditlens import AuditLensReport, audit
from auditlens.core.schema import AuditIssue


def test_audit_layer1_returns_report() -> None:
    df = pd.DataFrame({"y": [0] * 80 + [1] * 20, "g": ["A", "B"] * 50})
    report = audit(df, target_col="y", sensitive_cols=["g"])
    assert isinstance(report, AuditLensReport)
    assert report.summary["total_issues"] >= 1
    assert all(isinstance(i, AuditIssue) for i in report.issues)
    md = report.to_markdown()
    assert "Layer 1" in md or "statistical" in md.lower()
