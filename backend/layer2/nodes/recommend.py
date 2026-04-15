from __future__ import annotations

import json
import logging
from typing import Any

from backend.layer2.llm.factory import create_provider_client
from backend.layer2.nodes.common import parse_json_with_retries, shorten_text
from backend.layer2.prompts.recommend_prompt import RECOMMEND_PROMPT_TEMPLATE
from backend.layer2.state import AuditState

logger = logging.getLogger("layer2")

_CATEGORY_PRIORITY = {
    "reweighting": 0,
    "resampling": 1,
    "data_collection": 2,
    "feature_engineering": 3,
    "algorithmic": 4,
    "post_processing": 5,
}


def _fallback_mitigations(issue_type: str) -> list[dict[str, str]]:
    default = [
        {
            "title": "Apply sample reweighting",
            "category": "reweighting",
            "when_to_use": "When group representation or outcomes are uneven.",
            "tradeoffs": "May slightly reduce global accuracy while improving subgroup fairness.",
            "difficulty": "medium",
            "expected_impact": "Reduces subgroup disparity in training signal.",
            "code_snippet": (
                "group_weights = df.groupby(['sex']).size().rdiv(1.0)\n"
                "sample_weight = df['sex'].map(group_weights)\n"
                "model.fit(X_train, y_train, sample_weight=sample_weight)"
            ),
        },
        {
            "title": "Collect more data for underrepresented groups",
            "category": "data_collection",
            "when_to_use": "When subgroup sample sizes are too small for stable modeling.",
            "tradeoffs": "Requires data acquisition effort and longer timeline.",
            "difficulty": "hard",
            "expected_impact": "Improves representation and reduces sampling bias.",
            "code_snippet": "# No direct training code. Define data collection targets per subgroup.",
        },
    ]
    if "missing" in issue_type:
        default[0]["title"] = "Impute carefully and audit subgroup missingness"
        default[0]["category"] = "feature_engineering"
    return default


def _normalize_mitigation(item: dict[str, Any]) -> dict[str, str]:
    difficulty = str(item.get("difficulty", "medium")).lower()
    if difficulty not in {"easy", "medium", "hard"}:
        difficulty = "medium"

    category = str(item.get("category", "reweighting")).strip().lower().replace(" ", "_")
    if category not in _CATEGORY_PRIORITY:
        category = "reweighting"

    return {
        "title": shorten_text(str(item.get("title", "Mitigation option")), limit=120),
        "category": category,
        "when_to_use": shorten_text(str(item.get("when_to_use", "")), limit=500),
        "tradeoffs": shorten_text(str(item.get("tradeoffs", "")), limit=500),
        "difficulty": difficulty,
        "expected_impact": shorten_text(str(item.get("expected_impact", "")), limit=500),
        "code_snippet": str(item.get("code_snippet", "")).strip(),
    }


def _sort_and_dedupe(items: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[tuple[str, str]] = set()
    deduped: list[dict[str, str]] = []
    for item in items:
        key = (item["title"].lower(), item["category"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return sorted(
        deduped,
        key=lambda item: (
            _CATEGORY_PRIORITY.get(item["category"], 99),
            {"easy": 0, "medium": 1, "hard": 2}.get(item["difficulty"], 1),
            item["title"],
        ),
    )


def recommend_node(state: AuditState) -> AuditState:
    if state.get("needs_clarification"):
        return {"mitigations": []}

    client = state.get("llm_client")
    if client is None:
        client = create_provider_client()

    task_context = state.get("task_context", {})
    max_retries = int(state.get("max_retries", 2))

    recommendations_by_issue: list[list[dict[str, str]]] = []
    interpretations = list(state.get("interpretations", []))
    parsed_issues = list(state.get("parsed_issues", []))

    for issue, interpretation in zip(parsed_issues, interpretations):
        prompt = (
            RECOMMEND_PROMPT_TEMPLATE.replace(
                "{task_context}",
                json.dumps(task_context, ensure_ascii=True),
            ).replace(
                "{interpretation}",
                json.dumps(interpretation, ensure_ascii=True),
            )
        )
        normalized: list[dict[str, str]] = []
        try:
            payload = parse_json_with_retries(client=client, prompt=prompt, max_retries=max_retries)
            mitigations = payload.get("mitigations", [])
            if not isinstance(mitigations, list):
                mitigations = []
            normalized = [_normalize_mitigation(item) for item in mitigations if isinstance(item, dict)]
        except Exception:
            normalized = []

        if not normalized:
            normalized = _fallback_mitigations(str(issue.get("type", "")))
        recommendations_by_issue.append(_sort_and_dedupe(normalized))

    request_id = state.get("request_id", "")
    logger.info(
        "layer2.recommend completed request_id=%s issues=%s",
        request_id,
        len(recommendations_by_issue),
    )

    return {"mitigations": recommendations_by_issue}
