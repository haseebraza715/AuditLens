from __future__ import annotations

from typing import Any

from auditlens.config import get_layer2_settings
from auditlens.exceptions import Layer2InvalidResponseError, Layer2ProviderError
from auditlens.interpretation.graph import build_layer2_graph
from auditlens.interpretation.llm.base import BaseLLMClient
from auditlens.interpretation.llm.factory import create_provider_client
from auditlens.interpretation.state import AuditState


def run_layer2_pipeline(
    *,
    layer1_report: dict[str, Any],
    task_description: str,
    clarification_answers: dict[str, Any] | None = None,
    request_id: str | None = None,
    llm_client: BaseLLMClient | None = None,
    layer2_provider: str | None = None,
    layer2_model: str | None = None,
    max_retries: int | None = None,
) -> dict[str, Any]:
    if llm_client is None:
        settings = get_layer2_settings()
        resolved_client = create_provider_client()
        provider = settings.provider
        model = settings.model
        retries = settings.max_retries
    else:
        resolved_client = llm_client
        provider = layer2_provider or "custom"
        model = layer2_model or "custom"
        retries = 2 if max_retries is None else max_retries

    initial_state: AuditState = {
        "request_id": request_id or "",
        "raw_json": layer1_report,
        "task_description": task_description,
        "clarification_answers": clarification_answers or {},
        "layer2_provider": provider,
        "layer2_model": model,
        "llm_client": resolved_client,
        "max_retries": retries,
    }

    graph = build_layer2_graph()
    try:
        output = graph.invoke(initial_state)
    except Layer2ProviderError:
        raise
    except Layer2InvalidResponseError:
        raise
    except Exception as exc:
        raise Layer2ProviderError("Layer 2 pipeline execution failed") from exc

    if output.get("needs_clarification"):
        layer1_public = {k: v for k, v in layer1_report.items() if k != "severity_thresholds"}
        return {
            "status": "needs_clarification",
            "clarifying_questions": list(output.get("clarifying_questions", []))[:2],
            "task_context_partial": dict(output.get("task_context_partial", {})),
            "layer1_report": layer1_public,
        }

    return {
        "status": "complete",
        "final_report": output.get("final_report", {}),
    }
