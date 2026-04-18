from __future__ import annotations

import logging

from auditlens.interpretation.state import AuditState

logger = logging.getLogger("layer2")


def _build_questions(task_context: dict[str, object]) -> list[str]:
    questions: list[str] = []
    if task_context.get("task_type") == "unknown":
        questions.append(
            "What is the task type: binary classification, multiclass classification, or regression?"
        )
    if not task_context.get("affected_population"):
        questions.append("Who is affected by model decisions in this task?")
    if not task_context.get("decision_impact"):
        questions.append("What decisions will this model influence in production?")
    if float(task_context.get("confidence", 0.0)) < 0.6:
        questions.append("Please clarify the positive outcome and the cost of false positives/negatives.")
    if not questions:
        return []
    return questions[:2]


def clarify_node(state: AuditState) -> AuditState:
    task_context = state.get("task_context", {})
    clarifying_questions = _build_questions(task_context)
    needs_clarification = bool(clarifying_questions)

    request_id = state.get("request_id", "")
    logger.info(
        "layer2.clarify completed request_id=%s questions=%s",
        request_id,
        len(clarifying_questions),
    )

    return {
        "needs_clarification": needs_clarification,
        "clarifying_questions": clarifying_questions,
    }
