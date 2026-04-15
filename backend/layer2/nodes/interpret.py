from __future__ import annotations

import json
import logging
from typing import Any

from backend.layer2.llm.factory import create_provider_client
from backend.layer2.nodes.common import parse_json_with_retries, shorten_text
from backend.layer2.prompts.interpret_prompt import INTERPRET_PROMPT_TEMPLATE
from backend.layer2.state import AuditState

logger = logging.getLogger("layer2")


def _fallback_interpretation(issue: dict[str, Any]) -> dict[str, Any]:
    severity = str(issue.get("severity", "low"))
    issue_type = str(issue.get("type", "dataset_issue")).replace("_", " ")
    return {
        "issue_id": issue.get("issue_id", "unknown_issue"),
        "why_harmful": (
            f"The detected {issue_type} pattern can bias model behavior for some subgroups."
        ),
        "at_risk_groups": [],
        "likely_model_impact": (
            "Model performance may degrade unevenly across sensitive groups if unresolved."
        ),
        "severity_delta": "equal",
        "severity_rationale": f"Task-adjusted severity defaults to the statistical level ({severity}).",
    }


def _normalize_interpretation(
    payload: dict[str, Any],
    issue: dict[str, Any],
) -> dict[str, Any]:
    interpretation = _fallback_interpretation(issue)
    interpretation.update(payload)

    interpretation["issue_id"] = str(interpretation.get("issue_id") or issue.get("issue_id", "unknown"))
    interpretation["why_harmful"] = shorten_text(
        str(interpretation.get("why_harmful") or _fallback_interpretation(issue)["why_harmful"]),
        limit=1500,
    )
    interpretation["likely_model_impact"] = shorten_text(
        str(
            interpretation.get("likely_model_impact")
            or _fallback_interpretation(issue)["likely_model_impact"]
        ),
        limit=1200,
    )
    interpretation["severity_rationale"] = shorten_text(
        str(
            interpretation.get("severity_rationale")
            or _fallback_interpretation(issue)["severity_rationale"]
        ),
        limit=600,
    )

    at_risk = interpretation.get("at_risk_groups", [])
    if not isinstance(at_risk, list):
        at_risk = [str(at_risk)]
    interpretation["at_risk_groups"] = [shorten_text(str(group), limit=150) for group in at_risk if str(group)]

    severity_delta = str(interpretation.get("severity_delta", "equal")).lower()
    if severity_delta not in {"higher", "equal", "lower"}:
        severity_delta = "equal"
    interpretation["severity_delta"] = severity_delta

    return interpretation


def interpret_node(state: AuditState) -> AuditState:
    if state.get("needs_clarification"):
        return {"interpretations": []}

    client = state.get("llm_client")
    if client is None:
        client = create_provider_client()
    max_retries = int(state.get("max_retries", 2))
    task_context = state.get("task_context", {})

    interpretations: list[dict[str, Any]] = []
    for issue in state.get("parsed_issues", []):
        prompt = (
            INTERPRET_PROMPT_TEMPLATE.replace(
                "{task_context}",
                json.dumps(task_context, ensure_ascii=True),
            ).replace(
                "{issue}",
                json.dumps(issue, ensure_ascii=True),
            )
        )
        try:
            payload = parse_json_with_retries(client=client, prompt=prompt, max_retries=max_retries)
            interpretations.append(_normalize_interpretation(payload, issue))
        except Exception:
            interpretations.append(_fallback_interpretation(issue))

    request_id = state.get("request_id", "")
    logger.info(
        "layer2.interpret completed request_id=%s issues=%s",
        request_id,
        len(interpretations),
    )

    return {"interpretations": interpretations}
