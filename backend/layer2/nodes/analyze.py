from __future__ import annotations

import logging
from typing import Any

from backend.layer2.llm.factory import create_provider_client
from backend.layer2.nodes.common import parse_json_with_retries, shorten_text
from backend.layer2.prompts.analyze_prompt import ANALYZE_PROMPT_TEMPLATE
from backend.layer2.state import AuditState

logger = logging.getLogger("layer2")


_VALID_TASK_TYPES = {
    "binary_classification",
    "multiclass_classification",
    "regression",
}
_VALID_STAKES = {"low", "medium", "high"}


def _to_context(payload: dict[str, Any], clarification_answers: dict[str, Any]) -> dict[str, Any]:
    merged = dict(payload)
    merged.update(clarification_answers)

    task_type = str(merged.get("task_type", "unknown")).strip().lower()
    if task_type not in _VALID_TASK_TYPES:
        task_type = "unknown"

    stakes = str(merged.get("stakes_level", "unknown")).strip().lower()
    if stakes not in _VALID_STAKES:
        stakes = "unknown"

    confidence = merged.get("confidence", 0.0)
    try:
        confidence_float = float(confidence)
    except (TypeError, ValueError):
        confidence_float = 0.0
    confidence_float = max(0.0, min(confidence_float, 1.0))

    assumptions_value = merged.get("assumptions", [])
    if not isinstance(assumptions_value, list):
        assumptions_value = [str(assumptions_value)]

    return {
        "task_type": task_type,
        "positive_class_meaning": shorten_text(str(merged.get("positive_class_meaning", ""))),
        "affected_population": shorten_text(str(merged.get("affected_population", ""))),
        "false_positive_consequence": shorten_text(
            str(merged.get("false_positive_consequence", ""))
        ),
        "false_negative_consequence": shorten_text(
            str(merged.get("false_negative_consequence", ""))
        ),
        "decision_impact": shorten_text(str(merged.get("decision_impact", ""))),
        "stakes_level": stakes,
        "confidence": confidence_float,
        "assumptions": [shorten_text(str(item), limit=200) for item in assumptions_value if str(item)],
    }


def _needs_clarification(task_context: dict[str, Any]) -> bool:
    if task_context["task_type"] == "unknown":
        return True
    if not task_context["affected_population"]:
        return True
    if not task_context["decision_impact"]:
        return True
    if task_context["confidence"] < 0.6:
        return True
    return False


def analyze_node(state: AuditState) -> AuditState:
    task_description = state.get("task_description", "")
    prompt = ANALYZE_PROMPT_TEMPLATE.replace("{task_description}", str(task_description))
    clarification_answers = state.get("clarification_answers", {}) or {}

    client = state.get("llm_client")
    if client is None:
        client = create_provider_client()

    max_retries = int(state.get("max_retries", 2))
    llm_payload = parse_json_with_retries(client=client, prompt=prompt, max_retries=max_retries)
    task_context = _to_context(llm_payload, clarification_answers)
    needs_clarification = _needs_clarification(task_context)

    request_id = state.get("request_id", "")
    logger.info(
        "layer2.analyze completed request_id=%s task_type=%s needs_clarification=%s",
        request_id,
        task_context["task_type"],
        needs_clarification,
    )

    return {
        "task_context": task_context,
        "task_context_partial": task_context,
        "needs_clarification": needs_clarification,
        "clarifying_questions": [],
    }
