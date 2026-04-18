from __future__ import annotations

from typing import Any

__all__ = ["build_layer2_graph", "run_layer2_pipeline"]


def __getattr__(name: str) -> Any:
    """Lazy exports so importing `auditlens.interpretation.schema` does not load LangGraph."""
    if name == "build_layer2_graph":
        from auditlens.interpretation.graph import build_layer2_graph as _build_layer2_graph

        return _build_layer2_graph
    if name == "run_layer2_pipeline":
        from auditlens.interpretation.pipeline import run_layer2_pipeline as _run_layer2_pipeline

        return _run_layer2_pipeline
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
