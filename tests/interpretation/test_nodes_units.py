"""Unit tests for Layer 2 graph node post-processing (no network)."""

from __future__ import annotations

import pytest

from auditlens.interpretation.nodes.analyze import _needs_clarification, _to_context
from auditlens.interpretation.nodes.clarify import _build_questions
from auditlens.interpretation.nodes.common import parse_json_with_retries, shorten_text
from auditlens.interpretation.nodes.interpret import _normalize_interpretation
from auditlens.interpretation.nodes.parse import _sort_issues
from auditlens.interpretation.nodes.recommend import (
    _fallback_mitigations,
    _normalize_mitigation,
    _sort_and_dedupe,
)
from auditlens.interpretation.nodes.report import _build_summary, _fallback_interpretation


class TestToContext:
    def test_valid_payload_passes_through(self) -> None:
        payload = {
            "task_type": "binary_classification",
            "stakes_level": "high",
            "confidence": 0.9,
            "affected_population": "applicants",
            "decision_impact": "gating",
            "assumptions": ["a", "b"],
        }
        ctx = _to_context(payload, {})
        assert ctx["task_type"] == "binary_classification"
        assert ctx["stakes_level"] == "high"
        assert ctx["confidence"] == 0.9
        assert ctx["assumptions"] == ["a", "b"]

    def test_invalid_enum_values_coerce_to_unknown(self) -> None:
        ctx = _to_context({"task_type": "quantum_computing", "stakes_level": "extreme"}, {})
        assert ctx["task_type"] == "unknown"
        assert ctx["stakes_level"] == "unknown"

    @pytest.mark.parametrize(
        "raw", ["1.4", "0.5", "-3", "banana", None, 0.999]
    )
    def test_confidence_clamped_to_unit_interval(self, raw) -> None:
        ctx = _to_context({"confidence": raw}, {})
        assert 0.0 <= ctx["confidence"] <= 1.0

    def test_clarification_answers_override_payload(self) -> None:
        ctx = _to_context({"task_type": "unknown"}, {"task_type": "regression"})
        assert ctx["task_type"] == "regression"

    def test_non_list_assumptions_wrapped(self) -> None:
        ctx = _to_context({"assumptions": "single assumption"}, {})
        assert ctx["assumptions"] == ["single assumption"]

    def test_fields_are_truncated(self) -> None:
        ctx = _to_context({"affected_population": "word " * 300}, {})
        assert len(ctx["affected_population"]) <= 600


class TestNeedsClarification:
    def test_unknown_task_type_triggers(self) -> None:
        assert _needs_clarification({"task_type": "unknown", "affected_population": "x", "decision_impact": "y", "confidence": 0.9})

    def test_empty_population_triggers(self) -> None:
        assert _needs_clarification({"task_type": "regression", "affected_population": "", "decision_impact": "y", "confidence": 0.9})

    def test_low_confidence_triggers(self) -> None:
        assert _needs_clarification({"task_type": "regression", "affected_population": "x", "decision_impact": "y", "confidence": 0.5})

    def test_complete_context_does_not_trigger(self) -> None:
        assert not _needs_clarification({"task_type": "regression", "affected_population": "x", "decision_impact": "y", "confidence": 0.8})


class TestBuildQuestions:
    def test_questions_bounded_to_two(self) -> None:
        ctx = {"task_type": "unknown", "affected_population": "", "decision_impact": "", "confidence": 0.1}
        assert len(_build_questions(ctx)) == 2

    def test_question_for_each_missing_field(self) -> None:
        ctx = {"task_type": "unknown", "affected_population": "users", "decision_impact": "y", "confidence": 0.9}
        questions = _build_questions(ctx)
        assert len(questions) == 1
        assert "task type" in questions[0]

    def test_no_questions_when_context_complete(self) -> None:
        ctx = {"task_type": "regression", "affected_population": "x", "decision_impact": "y", "confidence": 0.9}
        assert _build_questions(ctx) == []


class TestNormalizeInterpretation:
    def test_missing_fields_fall_back(self) -> None:
        issue = {"issue_id": "ix", "type": "class_imbalance", "severity": "high"}
        interp = _normalize_interpretation({}, issue)
        assert interp["issue_id"] == "ix"
        assert interp["severity_delta"] == "equal"
        assert "class imbalance" in interp["why_harmful"]

    def test_invalid_severity_delta_coerced(self) -> None:
        issue = {"issue_id": "ix", "type": "t", "severity": "low"}
        interp = _normalize_interpretation({"severity_delta": "sideways"}, issue)
        assert interp["severity_delta"] == "equal"

    def test_at_risk_groups_wrapped_when_scalar(self) -> None:
        issue = {"issue_id": "ix", "type": "t", "severity": "low"}
        interp = _normalize_interpretation({"at_risk_groups": "women"}, issue)
        assert interp["at_risk_groups"] == ["women"]

    def test_provided_fields_are_preserved(self) -> None:
        issue = {"issue_id": "ix", "type": "t", "severity": "low"}
        interp = _normalize_interpretation(
            {"issue_id": "ix", "why_harmful": "harm", "likely_model_impact": "impact",
             "severity_delta": "higher", "severity_rationale": "because"},
            issue,
        )
        assert interp["why_harmful"] == "harm"
        assert interp["severity_delta"] == "higher"


class TestParseSorting:
    def test_sort_by_severity_then_id(self) -> None:
        issues = [
            {"severity": "medium", "issue_id": "b"},
            {"severity": "high", "issue_id": "z"},
            {"severity": "low", "issue_id": "a"},
        ]
        ordered = _sort_issues(issues)
        assert [i["issue_id"] for i in ordered] == ["z", "b", "a"]

    def test_missing_severity_sorts_as_low(self) -> None:
        issues = [{"issue_id": "x"}, {"severity": "high", "issue_id": "y"}]
        assert [i["issue_id"] for i in _sort_issues(issues)] == ["y", "x"]


class TestMitigationNormalization:
    def test_invalid_category_and_difficulty_coerced(self) -> None:
        item = _normalize_mitigation({"category": "nuclear option", "difficulty": "extreme"})
        assert item["category"] == "reweighting"
        assert item["difficulty"] == "medium"

    def test_category_underscored_and_lowered(self) -> None:
        item = _normalize_mitigation({"category": "Post Processing"})
        assert item["category"] == "post_processing"

    def test_defaults_for_empty_item(self) -> None:
        item = _normalize_mitigation({})
        assert item["title"] == "Mitigation option"
        assert item["code_snippet"] == ""

    def test_dedupe_and_sort_by_category_priority(self) -> None:
        items = [
            {"title": "Post-process", "category": "post_processing"},
            {"title": "Reweight", "category": "reweighting"},
            {"title": "Reweight", "category": "reweighting"},
        ]
        normalized = [_normalize_mitigation(i) for i in items]
        deduped = _sort_and_dedupe(normalized)
        assert [i["title"] for i in deduped] == ["Reweight", "Post-process"]

    def test_fallback_mitigations_vary_for_missingness(self) -> None:
        generic = _fallback_mitigations("demographic_parity_gap")
        missing = _fallback_mitigations("differential_missingness")
        assert generic[0]["category"] == "reweighting"
        assert missing[0]["category"] == "feature_engineering"


class TestReportNodeHelpers:
    def test_summary_matches_inputs(self) -> None:
        summary = _build_summary(total_issues=3, task_type="binary_classification", stakes_level="high")
        assert "3 issue(s)" in summary
        assert "binary_classification" in summary
        assert "high" in summary

    def test_fallback_interpretation_is_complete(self) -> None:
        fallback = _fallback_interpretation("ix")
        assert fallback["issue_id"] == "ix"
        assert fallback["severity_delta"] == "equal"
        assert fallback["at_risk_groups"] == []


def test_parse_json_with_retries_and_shorten_text_smoke() -> None:
    class _Ok:
        def complete_json(self, prompt: str) -> str:
            return '{"ok": true}'

    assert parse_json_with_retries(client=_Ok(), prompt="p", max_retries=2) == {"ok": True}
    assert shorten_text("a b c") == "a b c"
