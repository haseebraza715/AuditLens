from __future__ import annotations

import logging
from typing import Any

from backend.layer2.state import AuditState
from backend.utils.config import SEVERITY_THRESHOLDS

logger = logging.getLogger("layer2")


def _build_summary(total_issues: int, task_type: str, stakes_level: str) -> str:
    return (
        f"Layer 2 analyzed {total_issues} issue(s) for a {task_type} task with "
        f"{stakes_level} stated stakes and generated task-aware mitigation guidance."
    )


def _fallback_interpretation(issue_id: str) -> dict[str, object]:
    return {
        "issue_id": issue_id,
        "why_harmful": "Task-aware interpretation was unavailable for this issue.",
        "at_risk_groups": [],
        "likely_model_impact": "Potential subgroup performance disparity should be reviewed manually.",
        "severity_delta": "equal",
        "severity_rationale": "Using statistical severity as fallback.",
    }


def report_node(state: AuditState) -> AuditState:
    if state.get("needs_clarification"):
        request_id = state.get("request_id", "")
        logger.info("layer2.report paused request_id=%s", request_id)
        return {}

    parsed_issues = list(state.get("parsed_issues", []))
    interpretations = list(state.get("interpretations", []))
    mitigations = list(state.get("mitigations", []))
    task_context = dict(state.get("task_context", {}))

    issue_entries: list[dict[str, Any]] = []
    for index, issue in enumerate(parsed_issues):
        interpretation = (
            interpretations[index]
            if index < len(interpretations)
            else _fallback_interpretation(str(issue.get("issue_id", "unknown_issue")))
        )
        issue_mitigations = mitigations[index] if index < len(mitigations) else []
        issue_entries.append(
            {
                "statistical_issue": issue,
                "interpretation": interpretation,
                "mitigations": issue_mitigations,
            }
        )

    final_report = {
        "task_description": state.get("task_description", ""),
        "task_context": task_context,
        "issues": issue_entries,
        "summary": _build_summary(
            total_issues=len(issue_entries),
            task_type=str(task_context.get("task_type", "unknown")),
            stakes_level=str(task_context.get("stakes_level", "unknown")),
        ),
        "disclaimer": (
            "This report was generated with LLM-assisted interpretation. "
            "Human review is strongly recommended before making deployment decisions."
        ),
        "reproducibility": {
            "generated_at_utc": "",
            "request_id": str(state.get("request_id", "")),
            "layer2_provider": str(state.get("layer2_provider", "unknown")),
            "layer2_model": str(state.get("layer2_model", "unknown")),
            "severity_thresholds": SEVERITY_THRESHOLDS,
        },
    }

    request_id = state.get("request_id", "")
    logger.info(
        "layer2.report completed request_id=%s issues=%s",
        request_id,
        len(issue_entries),
    )
    return {"final_report": final_report}
