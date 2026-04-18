from __future__ import annotations

import logging
from typing import Any

from backend.layer2.state import AuditState
from backend.utils.config import SEVERITY_ORDER

logger = logging.getLogger("layer2")


def _sort_issues(issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        issues,
        key=lambda issue: (
            SEVERITY_ORDER.get(str(issue.get("severity", "low")), SEVERITY_ORDER["low"]),
            str(issue.get("issue_id", "")),
        ),
    )


def parse_node(state: AuditState) -> AuditState:
    raw_json = state.get("raw_json", {})
    dataset_info = raw_json.get("dataset_info", {})
    sorted_issues = _sort_issues(list(raw_json.get("issues", [])))

    request_id = state.get("request_id", "")
    logger.info(
        "layer2.parse completed request_id=%s issues=%s",
        request_id,
        len(sorted_issues),
    )

    return {
        "parsed_issues": sorted_issues,
        "task_context_partial": {
            "task_type": "unknown",
            "stakes_level": "unknown",
            "confidence": 0.0,
            "assumptions": [],
            "dataset_rows": dataset_info.get("rows", 0),
            "target_column": dataset_info.get("target_column", ""),
            "sensitive_columns": dataset_info.get("sensitive_columns", []),
        },
    }
