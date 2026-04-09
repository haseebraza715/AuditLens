from __future__ import annotations

from typing import Any, TypedDict


class AuditState(TypedDict, total=False):
    request_id: str
    raw_json: dict[str, Any]
    task_description: str
    clarification_answers: dict[str, Any]

    parsed_issues: list[dict[str, Any]]
    task_context: dict[str, Any]
    task_context_partial: dict[str, Any]
    interpretations: list[dict[str, Any]]
    mitigations: list[list[dict[str, Any]]]

    needs_clarification: bool
    clarifying_questions: list[str]
    final_report: dict[str, Any]
