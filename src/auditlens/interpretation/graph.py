from __future__ import annotations

from langgraph.graph import END, StateGraph

from auditlens.interpretation.nodes.analyze import analyze_node
from auditlens.interpretation.nodes.clarify import clarify_node
from auditlens.interpretation.nodes.interpret import interpret_node
from auditlens.interpretation.nodes.parse import parse_node
from auditlens.interpretation.nodes.recommend import recommend_node
from auditlens.interpretation.nodes.report import report_node
from auditlens.interpretation.state import AuditState


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
