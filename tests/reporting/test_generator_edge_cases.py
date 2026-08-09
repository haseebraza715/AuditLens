"""Robustness tests for markdown/PDF report generation."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from auditlens.reporting.generator import (
    _severity_badge,
    build_markdown_report,
    build_pdf_report,
    encode_pdf_base64,
)


def _minimal_final_report() -> dict:
    return {
        "task_description": "Predict approvals",
        "task_context": {
            "task_type": "binary_classification",
            "stakes_level": "high",
            "affected_population": "applicants",
            "decision_impact": "gating",
        },
        "issues": [],
        "summary": "Nothing found.",
        "disclaimer": "Review before use.",
        "reproducibility": {},
    }


class TestMarkdownRobustness:
    def test_empty_issues_section(self) -> None:
        md = build_markdown_report(final_report=_minimal_final_report())
        assert "No issues were included" in md
        assert "# AuditLens Bias Audit Report" in md

    def test_none_fields_do_not_crash(self) -> None:
        final_report = {
            "task_description": None,
            "task_context": None,
            "issues": None,
            "summary": None,
            "disclaimer": None,
            "reproducibility": None,
        }
        md = build_markdown_report(final_report=final_report)
        assert "_Not provided_" in md
        assert "_No summary generated._" in md

    def test_deterministic_output(self) -> None:
        final_report = _minimal_final_report()
        generated_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
        first = build_markdown_report(final_report=final_report, generated_at_utc=generated_at)
        second = build_markdown_report(final_report=final_report, generated_at_utc=generated_at)
        assert first == second

    def test_unicode_and_emoji_preserved(self) -> None:
        final_report = _minimal_final_report()
        final_report["task_description"] = "Crédit scoring — αβγ 🔍"
        final_report["issues"] = [
            {
                "statistical_issue": {
                    "issue_id": "ix",
                    "type": "class_imbalance",
                    "severity": "high",
                    "description": "Détail avec émojis 🚀 et <tags>",
                },
                "interpretation": {
                    "issue_id": "ix",
                    "why_harmful": "Conséquence pour les 用户",
                    "at_risk_groups": ["group α"],
                    "likely_model_impact": "impact",
                    "severity_delta": "equal",
                    "severity_rationale": "r",
                },
                "mitigations": [{"title": "Rééquilibrage", "difficulty": "easy"}],
            }
        ]
        md = build_markdown_report(final_report=final_report)
        assert "Crédit scoring" in md
        assert "émojis 🚀" in md
        assert "用户" in md
        assert "Rééquilibrage" in md

    def test_many_issues_all_render(self) -> None:
        issues = []
        for i in range(200):
            issues.append(
                {
                    "statistical_issue": {
                        "issue_id": f"issue_{i:03d}",
                        "type": "class_imbalance",
                        "severity": "medium" if i % 2 else "low",
                        "description": f"Finding number {i}",
                    },
                    "interpretation": {
                        "issue_id": f"issue_{i:03d}",
                        "why_harmful": f"harm {i}",
                        "likely_model_impact": "impact",
                        "severity_delta": "equal",
                        "severity_rationale": "r",
                    },
                    "mitigations": [],
                }
            )
        final_report = _minimal_final_report()
        final_report["issues"] = issues
        md = build_markdown_report(final_report=final_report)
        assert "Total issues: `200`" in md
        issue_headings = [line for line in md.splitlines() if line.startswith("### ")]
        assert len(issue_headings) == 200
        assert "issue_199" in md

    def test_severity_thresholds_rendered_when_present(self) -> None:
        final_report = _minimal_final_report()
        final_report["reproducibility"] = {
            "generated_at_utc": "2026-01-01T00:00:00+00:00",
            "request_id": "req-1",
            "layer2_provider": "openai",
            "layer2_model": "gpt-4o-mini",
            "severity_thresholds": {"cramers_v": {"medium": 0.1, "high": 0.3}},
        }
        md = build_markdown_report(final_report=final_report)
        assert "req-1" in md
        assert "cramers_v" in md
        assert "medium=`0.1`" in md

    def test_invalid_thresholds_shape_is_ignored_gracefully(self) -> None:
        final_report = _minimal_final_report()
        final_report["reproducibility"] = {"severity_thresholds": "not-a-dict"}
        md = build_markdown_report(final_report=final_report)
        assert "Not available" in md


class TestSeverityBadge:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [("high", "HIGH"), ("HIGH", "HIGH"), ("medium", "MEDIUM"), ("low", "LOW"), ("", "LOW"), (None, "LOW")],
    )
    def test_badge_normalizes(self, value, expected: str) -> None:
        assert _severity_badge(value) == expected


class TestPdfRobustness:
    def test_pdf_with_empty_issues(self) -> None:
        pdf = build_pdf_report(final_report=_minimal_final_report(), layer1_report=None)
        assert pdf.startswith(b"%PDF")
        assert len(pdf) > 1000

    def test_pdf_with_special_characters(self) -> None:
        final_report = _minimal_final_report()
        final_report["task_description"] = "R&D & growth <priority>"
        final_report["issues"] = [
            {
                "statistical_issue": {
                    "issue_id": "i1",
                    "type": "class_imbalance",
                    "severity": "high",
                    "description": "R&D spend & <growth> signals > 5%",
                },
                "interpretation": {
                    "issue_id": "i1",
                    "why_harmful": "Harms & biases <groups>",
                    "likely_model_impact": "x",
                    "severity_delta": "equal",
                    "severity_rationale": "n/a",
                },
                "mitigations": [{"title": "a & b <c>", "difficulty": "easy"}],
            }
        ]
        pdf = build_pdf_report(final_report=final_report)
        assert pdf.startswith(b"%PDF")

    def test_pdf_unicode_roundtrip(self) -> None:
        final_report = _minimal_final_report()
        final_report["task_description"] = "Crédit — 贷款审批"
        final_report["issues"] = [
            {
                "statistical_issue": {
                    "issue_id": "i1", "type": "class_imbalance", "severity": "high",
                    "description": "αβγ description",
                },
                "interpretation": {
                    "issue_id": "i1", "why_harmful": "用户 harm",
                    "likely_model_impact": "x", "severity_delta": "equal", "severity_rationale": "r",
                },
                "mitigations": [],
            }
        ]
        pdf = build_pdf_report(final_report=final_report)
        assert pdf.startswith(b"%PDF")

    def test_pdf_fixed_timestamp_is_reproducible(self) -> None:
        generated_at = datetime(2026, 5, 5, tzinfo=timezone.utc)
        first = build_pdf_report(final_report=_minimal_final_report(), generated_at_utc=generated_at)
        second = build_pdf_report(final_report=_minimal_final_report(), generated_at_utc=generated_at)
        assert first == second

    def test_encode_pdf_base64_roundtrip(self) -> None:
        import base64

        pdf = build_pdf_report(final_report=_minimal_final_report())
        encoded = encode_pdf_base64(pdf)
        assert base64.b64decode(encoded.encode("ascii")) == pdf
