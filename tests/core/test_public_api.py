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


def test_audit_lens_report_repr_and_html_and_dict() -> None:
    df = pd.DataFrame({"y": [0] * 80 + [1] * 20, "g": ["A", "B"] * 50})
    report = audit(df, target_col="y", sensitive_cols=["g"])
    text = repr(report)
    assert "AuditLensReport" in text
    assert "issues=" in text
    assert "high=" in text
    html_out = report._repr_html_()
    assert "<table" in html_out
    assert "class_imbalance" in html_out or "Type" in html_out
    blob = report.to_dict()
    assert blob["status"] is None
    assert blob["summary"]["total_issues"] >= 1
    assert len(blob["issues"]) >= 1
    assert blob["final_report"] is None
    assert "layer1_report" in blob
