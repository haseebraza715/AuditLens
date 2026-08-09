"""End-to-end audit on synthetic datasets with a known bias structure.

The biased dataset is constructed so the ground-truth effect sizes are large
(demographic-parity gap ~0.6, point-biserial |r| ~0.6, differential missingness
~0.25); the negative control is structurally unbiased and must produce no
findings. Both are fully deterministic (fixed seed).
"""

from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd

from auditlens import audit


def _biased_dataset(n: int = 4000) -> pd.DataFrame:
    rng = np.random.default_rng(2026)
    sex = np.array(["F"] * (n // 2) + ["M"] * (n // 2))
    rng.shuffle(sex)
    positive_rate = np.where(sex == "F", 0.85, 0.25)
    approved = (rng.random(n) < positive_rate).astype(int)
    income = np.where(sex == "F", rng.normal(70, 10, n), rng.normal(50, 10, n))
    missing = np.where(sex == "M", rng.random(n) < 0.30, rng.random(n) < 0.05)
    income = np.where(missing, np.nan, income)
    return pd.DataFrame({"sex": sex, "approved": approved, "income": income})


def _control_dataset(n: int = 4000) -> pd.DataFrame:
    rng = np.random.default_rng(7)
    sex = np.array(["F"] * (n // 2) + ["M"] * (n // 2))
    rng.shuffle(sex)
    approved = (rng.random(n) < 0.5).astype(int)
    income = np.where(sex == "F", rng.normal(50, 10, n), rng.normal(50, 10, n))
    return pd.DataFrame({"sex": sex, "approved": approved, "income": income})


class _ScriptedLLM:
    def complete_json(self, prompt: str) -> str:
        if "Extract structured context" in prompt:
            return json.dumps(
                {
                    "task_type": "binary_classification",
                    "affected_population": "loan applicants",
                    "decision_impact": "approval decisions",
                    "stakes_level": "high",
                    "confidence": 0.95,
                }
            )
        if "Given task context and one statistical issue" in prompt:
            return json.dumps(
                {
                    "issue_id": "placeholder",
                    "why_harmful": "Systematic subgroup disparity in approvals.",
                    "at_risk_groups": ["women applicants"],
                    "likely_model_impact": "Elevated false negatives for one group.",
                    "severity_delta": "higher",
                    "severity_rationale": "High-stakes lending context amplifies harm.",
                }
            )
        if "ML bias mitigation advisor" in prompt:
            return json.dumps(
                {
                    "mitigations": [
                        {
                            "title": "Group-aware reweighting",
                            "category": "reweighting",
                            "when_to_use": "When approval rates diverge by group.",
                            "tradeoffs": "May shift global accuracy slightly.",
                            "difficulty": "medium",
                            "expected_impact": "Narrows the approval-rate gap.",
                            "code_snippet": "model.fit(X, y, sample_weight=w)",
                        }
                    ]
                }
            )
        return "{}"


class TestSyntheticBiasDetection:
    def test_biased_dataset_raises_high_demographic_parity(self) -> None:
        report = audit(_biased_dataset(), target_col="approved", sensitive_cols=["sex"])
        parity = [i for i in report.issues if i.type == "demographic_parity_gap"]
        assert len(parity) == 1
        issue = parity[0]
        assert issue.severity == "high"
        assert issue.metrics["demographic_parity_gap"] > 0.3
        # Convention: the minority class is picked as the reference positive.
        assert issue.metrics["positive_class"] == "0"
        assert issue.metrics["group_sizes"]["F"] == 2000
        assert issue.metrics["sample_size"] == 4000

    def test_biased_dataset_detects_sensitive_correlation(self) -> None:
        report = audit(_biased_dataset(), target_col="approved", sensitive_cols=["sex"])
        corr = [i for i in report.issues if i.type == "sensitive_correlation"]
        assert len(corr) == 1
        assert corr[0].severity == "high"
        assert corr[0].metrics["absolute_correlation"] > 0.5
        assert corr[0].metrics["method"] in {"point_biserial", "cramers_v"}

    def test_biased_dataset_detects_differential_missingness(self) -> None:
        report = audit(_biased_dataset(), target_col="approved", sensitive_cols=["sex"])
        missing = [i for i in report.issues if i.type == "differential_missingness"]
        assert len(missing) == 1
        assert missing[0].severity == "high"
        assert missing[0].metrics["missingness_gap"] > 0.15
        assert missing[0].affected_column == "income"

    def test_biased_dataset_summary_counts_high_only(self) -> None:
        report = audit(_biased_dataset(), target_col="approved", sensitive_cols=["sex"])
        assert report.summary == {"total_issues": 3, "high_severity": 3, "medium_severity": 0, "low_severity": 0}

    def test_negative_control_has_no_findings(self) -> None:
        report = audit(_control_dataset(), target_col="approved", sensitive_cols=["sex"])
        assert report.summary["total_issues"] == 0
        assert report.summary["high_severity"] == 0

    def test_audit_is_deterministic(self) -> None:
        df = _biased_dataset()
        first = audit(df, target_col="approved", sensitive_cols=["sex"]).to_dict()
        second = audit(df, target_col="approved", sensitive_cols=["sex"]).to_dict()
        assert first == second

    def test_all_metrics_are_finite(self) -> None:
        report = audit(_biased_dataset(), target_col="approved", sensitive_cols=["sex"])
        for issue in report.issues:
            for value in issue.metrics.values():
                if isinstance(value, float):
                    assert math.isfinite(value), f"non-finite metric in {issue.issue_id}"

    def test_to_dict_is_strict_json_safe(self) -> None:
        report = audit(_biased_dataset(), target_col="approved", sensitive_cols=["sex"])
        payload = json.dumps(report.to_dict())
        assert "Infinity" not in payload and "NaN" not in payload

    def test_issues_sorted_by_severity_then_id(self) -> None:
        report = audit(_biased_dataset(), target_col="approved", sensitive_cols=["sex"])
        order = {"high": 0, "medium": 1, "low": 2}
        severities = [order[i.severity] for i in report.issues]
        assert severities == sorted(severities)
        assert [i.issue_id for i in report.issues] == sorted(i.issue_id for i in report.issues)

    def test_full_pipeline_with_scripted_llm(self) -> None:
        report = audit(
            _biased_dataset(n=800),
            target_col="approved",
            sensitive_cols=["sex"],
            task_description="Predict loan approval for applicants; used to gate credit.",
            llm_client=_ScriptedLLM(),
            layer2_provider="test",
            layer2_model="test",
        )
        assert report.status == "complete"
        final = report.final_report
        assert final is not None
        layer1_ids = {i.issue_id for i in report.issues}
        assert {entry.statistical_issue["issue_id"] for entry in final.issues} == layer1_ids
        assert final.task_context.task_type == "binary_classification"

    def test_full_pipeline_markdown_and_pdf_artifacts(self, tmp_path) -> None:
        report = audit(
            _biased_dataset(n=400),
            target_col="approved",
            sensitive_cols=["sex"],
            task_description="Loan approval gating model.",
            llm_client=_ScriptedLLM(),
            layer2_provider="test",
            layer2_model="test",
        )
        md = report.to_markdown()
        assert "# AuditLens Bias Audit Report" in md
        assert "demographic_parity_gap" in md
        pdf_path = tmp_path / "report.pdf"
        report.to_pdf(str(pdf_path))
        assert pdf_path.read_bytes().startswith(b"%PDF")

    def test_layer1_only_markdown_covers_findings(self) -> None:
        report = audit(_biased_dataset(n=200), target_col="approved", sensitive_cols=["sex"])
        md = report.to_markdown()
        assert "demographic_parity_gap" in md
        assert "High severity" in md or "high" in md.lower()

    def test_tiny_unbiased_sample_does_not_crash(self) -> None:
        rng = np.random.default_rng(3)
        df = pd.DataFrame(
            {
                "sex": rng.choice(["F", "M"], size=20),
                "approved": rng.integers(0, 2, size=20),
                "income": rng.normal(size=20),
            }
        )
        report = audit(df, target_col="approved", sensitive_cols=["sex"])
        assert isinstance(report.summary["total_issues"], int)
        for issue in report.issues:
            for value in issue.metrics.values():
                if isinstance(value, float):
                    assert math.isfinite(value)

    def test_threshold_override_removes_findings(self) -> None:
        from auditlens.config import SEVERITY_THRESHOLDS

        lax = {k: dict(v) for k, v in SEVERITY_THRESHOLDS.items()}
        lax["demographic_parity_gap"] = {"medium": 0.95, "high": 0.99}
        lax["cramers_v"] = {"medium": 0.95, "high": 0.99}
        lax["differential_missingness"] = {"medium": 0.95, "high": 0.99}
        report = audit(
            _biased_dataset(), target_col="approved", sensitive_cols=["sex"], severity_thresholds=lax
        )
        assert report.summary["total_issues"] == 0

    def test_sensitive_column_unicode_safe_end_to_end(self) -> None:
        df = _biased_dataset(n=400).rename(columns={"sex": "性别"})
        report = audit(df, target_col="approved", sensitive_cols=["性别"])
        assert report.summary["high_severity"] >= 2
        assert "性别" in report.to_dict()["layer1_report"]["dataset_info"]["sensitive_columns"]
