from __future__ import annotations

from typing import Any

import streamlit as st

from backend.layer3.visualizations import build_fairness_overview_chart
from frontend.charts import render_inline_charts
from frontend.downloads import render_downloads
from frontend.styles import SEVERITY_COLORS


def _severity_rank(severity: str, high_first: bool = True) -> int:
    order = {"high": 0, "medium": 1, "low": 2}
    reverse_order = {"low": 0, "medium": 1, "high": 2}
    return (order if high_first else reverse_order).get(severity, 3)


def _render_task_context(final_report: dict[str, Any]) -> None:
    task_context = final_report.get("task_context", {}) or {}
    st.table(
        {
            "Field": ["Task Type", "Stakes", "Affected Population", "Decision Impact"],
            "Value": [
                str(task_context.get("task_type", "unknown")),
                str(task_context.get("stakes_level", "unknown")),
                str(task_context.get("affected_population", "unknown")),
                str(task_context.get("decision_impact", "unknown")),
            ],
        }
    )


def render_issue_cards(final_report: dict[str, Any]) -> None:
    issues = list(final_report.get("issues", []))
    if not issues:
        st.info("No issues returned in the final report.")
        return

    selected_severities = st.multiselect(
        "Filter by severity",
        ["HIGH", "MEDIUM", "LOW"],
        default=["HIGH", "MEDIUM", "LOW"],
    )
    sort_option = st.selectbox(
        "Sort by",
        ["Severity (High first)", "Severity (Low first)", "Issue type"],
    )

    filtered = []
    for item in issues:
        severity = str((item.get("statistical_issue", {}) or {}).get("severity", "low")).upper()
        if severity in selected_severities:
            filtered.append(item)

    if sort_option == "Severity (High first)":
        filtered = sorted(
            filtered,
            key=lambda item: _severity_rank(
                str((item.get("statistical_issue", {}) or {}).get("severity", "low")).lower(),
                high_first=True,
            ),
        )
    elif sort_option == "Severity (Low first)":
        filtered = sorted(
            filtered,
            key=lambda item: _severity_rank(
                str((item.get("statistical_issue", {}) or {}).get("severity", "low")).lower(),
                high_first=False,
            ),
        )
    else:
        filtered = sorted(
            filtered,
            key=lambda item: str((item.get("statistical_issue", {}) or {}).get("type", "zzz")),
        )

    st.caption(f"Showing {len(filtered)} of {len(issues)} findings")

    for entry in filtered:
        statistical = entry.get("statistical_issue", {}) or {}
        interpretation = entry.get("interpretation", {}) or {}
        mitigations = list(entry.get("mitigations", []) or [])

        severity = str(statistical.get("severity", "low")).lower()
        issue_type = str(statistical.get("type", "dataset_issue")).replace("_", " ").title()
        header = f"[{severity.upper()}] {issue_type}"
        border_color = SEVERITY_COLORS.get(severity, SEVERITY_COLORS["low"])

        with st.expander(header, expanded=severity == "high"):
            description = str(statistical.get("description", "")).strip()
            st.markdown(
                f"""
                <div style="border-left:6px solid {border_color}; padding:0.5rem 0.7rem; background:#ffffff; border-radius:8px;">
                    {description}
                </div>
                """,
                unsafe_allow_html=True,
            )

            why_harmful = str(interpretation.get("why_harmful", "")).strip()
            at_risk_groups = list(interpretation.get("at_risk_groups", []) or [])
            likely_impact = str(interpretation.get("likely_model_impact", "")).strip()
            severity_rationale = str(interpretation.get("severity_rationale", "")).strip()

            if why_harmful:
                st.markdown(f"**Why it matters:** {why_harmful}")
            if at_risk_groups:
                st.markdown(f"**At-risk groups:** {', '.join(str(group) for group in at_risk_groups)}")
            if likely_impact:
                st.markdown(f"**Likely model impact:** {likely_impact}")
            if severity_rationale:
                st.caption(f"Severity rationale: {severity_rationale}")

            with st.expander(f"Recommended fixes ({len(mitigations)})", expanded=False):
                for mitigation in mitigations:
                    title = str(mitigation.get("title", "Mitigation"))
                    category = str(mitigation.get("category", "general")).replace("_", " ")
                    difficulty = str(mitigation.get("difficulty", "medium"))
                    when_to_use = str(mitigation.get("when_to_use", "")).strip()
                    tradeoffs = str(mitigation.get("tradeoffs", "")).strip()
                    expected_impact = str(mitigation.get("expected_impact", "")).strip()
                    code_snippet = str(mitigation.get("code_snippet", "")).strip()

                    st.markdown(f"##### {title}")
                    st.caption(f"{difficulty.title()} · {category.title()}")
                    if when_to_use:
                        st.markdown(f"**When to use:** {when_to_use}")
                    if tradeoffs:
                        st.markdown(f"**Tradeoffs:** {tradeoffs}")
                    if expected_impact:
                        st.markdown(f"**Expected impact:** {expected_impact}")
                    if code_snippet:
                        st.code(code_snippet, language="python")
                    st.divider()


def render_final_report_section() -> None:
    final_report = st.session_state.final_report
    if not isinstance(final_report, dict):
        return

    issues = list(final_report.get("issues", []))
    dataset_name = st.session_state.file_name or "dataset"
    rows = int((st.session_state.preview_info or {}).get("rows", 0) or 0)
    layer1_report = st.session_state.layer1_report

    st.success(f"Audit complete for {dataset_name}: {rows:,} rows, {len(issues)} issues found.")
    reproducibility = final_report.get("reproducibility", {}) or {}
    st.caption(
        "Layer 2 provider: "
        f"{str(reproducibility.get('layer2_provider', 'unknown'))} | "
        f"Model: {str(reproducibility.get('layer2_model', 'unknown'))}"
    )

    tab_overview, tab_findings, tab_charts, tab_report = st.tabs(
        ["Overview", "Risk Findings", "Charts", "Report"]
    )

    with tab_overview:
        high = sum(
            1 for entry in issues if str((entry.get("statistical_issue", {}) or {}).get("severity", "")).lower() == "high"
        )
        medium = sum(
            1
            for entry in issues
            if str((entry.get("statistical_issue", {}) or {}).get("severity", "")).lower() == "medium"
        )
        low = sum(
            1 for entry in issues if str((entry.get("statistical_issue", {}) or {}).get("severity", "")).lower() == "low"
        )
        c1, c2, c3 = st.columns(3)
        c1.metric("HIGH", high)
        c2.metric("MEDIUM", medium)
        c3.metric("LOW", low)
        _render_task_context(final_report)
        if isinstance(layer1_report, dict):
            dataset_info = layer1_report.get("dataset_info", {}) or {}
            st.caption(
                f"Dataset: {dataset_info.get('rows', 0):,} rows · {dataset_info.get('columns', 0)} columns · "
                f"target: {dataset_info.get('target_column', 'unknown')}"
            )
            st.image(
                build_fairness_overview_chart(layer1_report),
                caption="Fairness overview across parity gaps and correlations",
                use_container_width=True,
            )

    with tab_findings:
        render_issue_cards(final_report)

    with tab_charts:
        render_inline_charts(final_report, layer1_report)

    with tab_report:
        render_downloads()
