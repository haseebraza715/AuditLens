from __future__ import annotations

from typing import Any

from backend.layer2.llm.factory import create_provider_client
from backend.layer2.state import AuditState
from backend.utils.config import Layer2ConfigurationError


def run_layer2_pipeline(
    *,
    layer1_report: dict[str, Any],
    task_description: str,
    clarification_answers: dict[str, Any] | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    """
    Phase 1 placeholder orchestrator.

    A provider client is created to validate runtime config now,
    while node logic is implemented in later phases.
    """
    try:
        _ = create_provider_client()
    except Exception as exc:
        if isinstance(exc, Layer2ConfigurationError):
            raise
        raise Layer2ConfigurationError(str(exc)) from exc

    _state: AuditState = {
        "request_id": request_id or "",
        "raw_json": layer1_report,
        "task_description": task_description,
        "clarification_answers": clarification_answers or {},
    }

    if not clarification_answers:
        return {
            "status": "needs_clarification",
            "clarifying_questions": [
                "What prediction target and positive outcome should the model optimize for?",
                "Who is most affected by false positives vs false negatives in this task?",
            ],
            "task_context_partial": {
                "task_type": "unknown",
                "stakes_level": "unknown",
                "confidence": 0.0,
                "assumptions": [],
            },
            "layer1_report": layer1_report,
        }

    issues: list[dict[str, Any]] = []
    for issue in layer1_report.get("issues", []):
        issues.append(
            {
                "statistical_issue": issue,
                "interpretation": {
                    "issue_id": issue.get("issue_id", "unknown_issue"),
                    "why_harmful": "Placeholder interpretation. Phase 3 will provide task-aware reasoning.",
                    "at_risk_groups": [],
                    "likely_model_impact": "Placeholder model impact summary.",
                    "severity_delta": "equal",
                    "severity_rationale": "Placeholder severity rationale.",
                },
                "mitigations": [
                    {
                        "title": "Collect more representative samples",
                        "category": "data_collection",
                        "when_to_use": "When subgroup representation is sparse.",
                        "tradeoffs": "Requires additional collection time and cost.",
                        "difficulty": "medium",
                        "expected_impact": "Improves subgroup coverage and fairness metrics.",
                        "code_snippet": "# placeholder: no direct code for data collection",
                    }
                ],
            }
        )

    return {
        "status": "complete",
        "final_report": {
            "task_description": task_description,
            "task_context": {
                "task_type": "unknown",
                "positive_class_meaning": "",
                "affected_population": "",
                "false_positive_consequence": "",
                "false_negative_consequence": "",
                "decision_impact": "",
                "stakes_level": "unknown",
                "confidence": 0.0,
                "assumptions": ["Placeholder output for phase 1 scaffolding."],
            },
            "issues": issues,
            "summary": "Placeholder Layer 2 summary. Task-aware reasoning is added in later phases.",
            "disclaimer": (
                "This report was generated with LLM assistance. "
                "Human review is recommended before making decisions."
            ),
        },
    }
