from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph

from backend.layer2.errors import Layer2ConfigurationError, Layer2InvalidResponseError, Layer2ProviderError
from backend.layer2.llm.base import BaseLLMClient
from backend.layer2.llm.factory import create_provider_client
from backend.layer2.nodes.analyze import analyze_node
from backend.layer2.nodes.clarify import clarify_node
from backend.layer2.nodes.interpret import interpret_node
from backend.layer2.nodes.parse import parse_node
from backend.layer2.nodes.recommend import recommend_node
from backend.layer2.nodes.report import report_node
from backend.layer2.state import AuditState
from backend.utils.config import Layer2ConfigurationError as ConfigError
from backend.utils.config import get_layer2_settings


def _after_analyze(state: AuditState) -> str:
    if state.get("needs_clarification"):
        return "clarify"
    return "interpret"


def build_layer2_graph():
    workflow = StateGraph(AuditState)
    workflow.add_node("parse", parse_node)
    workflow.add_node("analyze", analyze_node)
    workflow.add_node("clarify", clarify_node)
    workflow.add_node("interpret", interpret_node)
    workflow.add_node("recommend", recommend_node)
    workflow.add_node("report", report_node)

    workflow.set_entry_point("parse")
    workflow.add_edge("parse", "analyze")
    workflow.add_conditional_edges(
        "analyze",
        _after_analyze,
        {
            "clarify": "clarify",
            "interpret": "interpret",
        },
    )
    workflow.add_edge("clarify", "report")
    workflow.add_edge("interpret", "recommend")
    workflow.add_edge("recommend", "report")
    workflow.add_edge("report", END)

    return workflow.compile()


def run_layer2_pipeline(
    *,
    layer1_report: dict[str, Any],
    task_description: str,
    clarification_answers: dict[str, Any] | None = None,
    request_id: str | None = None,
    llm_client: BaseLLMClient | None = None,
) -> dict[str, Any]:
    try:
        settings = get_layer2_settings()
    except ConfigError as exc:
        raise Layer2ConfigurationError(str(exc)) from exc

    if llm_client is None:
        llm_client = create_provider_client()

    initial_state: AuditState = {
        "request_id": request_id or "",
        "raw_json": layer1_report,
        "task_description": task_description,
        "clarification_answers": clarification_answers or {},
        "llm_client": llm_client,
        "max_retries": settings.max_retries,
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
        return {
            "status": "needs_clarification",
            "clarifying_questions": list(output.get("clarifying_questions", []))[:2],
            "task_context_partial": dict(output.get("task_context_partial", {})),
            "layer1_report": layer1_report,
        }

    return {
        "status": "complete",
        "final_report": output.get("final_report", {}),
    }
