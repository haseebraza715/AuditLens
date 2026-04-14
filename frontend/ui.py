from __future__ import annotations

from typing import Any

import streamlit as st

from backend.layer3.visualizations import (
    build_class_distribution_chart,
    build_demographic_parity_chart,
    build_issue_type_chart,
    build_severity_summary_chart,
)
from frontend.api_client import ApiError, download_bytes
from frontend.constants import ASYNC_ROW_THRESHOLD
from frontend.state import reset_run_state
from frontend.workflow import (
    on_new_file,
    poll_async_job_if_needed,
    start_audit_run,
    submit_clarification_answers,
)


def apply_styles() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&family=Source+Serif+4:wght@500;700&display=swap');

        .stApp {
            background:
                radial-gradient(circle at 12% 18%, rgba(255, 183, 77, 0.24), transparent 38%),
                radial-gradient(circle at 88% 8%, rgba(3, 169, 244, 0.15), transparent 32%),
                linear-gradient(180deg, #f6f9fc 0%, #ecf4fb 100%);
        }

        html, body, [class*="css"] {
            font-family: 'Space Grotesk', sans-serif;
            color: #102a43;
        }

        h1, h2, h3 {
            font-family: 'Source Serif 4', serif !important;
            letter-spacing: 0.2px;
        }

        .hero {
            border: 1px solid rgba(16, 42, 67, 0.12);
            border-radius: 16px;
            padding: 1rem 1.1rem;
            background: rgba(255, 255, 255, 0.85);
            box-shadow: 0 8px 20px rgba(16, 42, 67, 0.06);
            margin-bottom: 1rem;
        }

        .issue-card {
            border-radius: 14px;
            background: #ffffff;
            box-shadow: 0 10px 24px rgba(16, 42, 67, 0.08);
            padding: 0.85rem 0.9rem;
            margin-bottom: 0.65rem;
        }

        .issue-head {
            display: flex;
            align-items: center;
            gap: 0.65rem;
            margin-bottom: 0.35rem;
            flex-wrap: wrap;
        }

        .severity-pill {
            color: #ffffff;
            border-radius: 999px;
            font-size: 0.74rem;
            font-weight: 700;
            letter-spacing: 0.5px;
            padding: 0.18rem 0.58rem;
        }

        .issue-title {
            font-weight: 700;
            font-size: 1.01rem;
            color: #102a43;
        }

        .issue-desc {
            color: #334e68;
            font-size: 0.95rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header() -> None:
    st.markdown(
        """
        <div class="hero">
            <h2 style="margin:0 0 0.35rem 0;">AuditLens Bias Auditor</h2>
            <p style="margin:0; color:#334e68;">
                Upload a CSV, define your prediction task, and generate a Layer 1-3 bias audit report.
                For large datasets, the app switches to async mode automatically.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar() -> None:
    st.sidebar.header("Configuration")
    st.sidebar.text_input("Backend API URL", key="api_base_url")

    uploaded_file = st.sidebar.file_uploader("Upload CSV", type=["csv"])
    if uploaded_file is not None:
        on_new_file(uploaded_file.name, uploaded_file.getvalue())

    if st.session_state.last_error:
        st.sidebar.error(st.session_state.last_error)

    preview_info = st.session_state.preview_info
    if not isinstance(preview_info, dict):
        return

    rows = int(preview_info.get("rows", 0) or 0)
    columns = int(preview_info.get("columns", 0) or 0)
    st.sidebar.caption(f"Detected {rows} rows and {columns} columns")

    column_names = list(preview_info.get("column_names", []))
    if not column_names:
        return

    target_default = st.session_state.target_column
    if target_default not in column_names:
        target_default = column_names[-1]

    target_idx = column_names.index(target_default)
    st.session_state.target_column = st.sidebar.selectbox(
        "Target column",
        options=column_names,
        index=target_idx,
    )

    sensitive_options = [c for c in column_names if c != st.session_state.target_column]
    current_sensitive = [c for c in st.session_state.sensitive_columns if c in sensitive_options]

    st.session_state.sensitive_columns = st.sidebar.multiselect(
        "Sensitive columns",
        options=sensitive_options,
        default=current_sensitive,
        help="Choose one or more protected attributes to audit.",
    )

    st.session_state.task_description = st.sidebar.text_area(
        "Task description",
        value=st.session_state.task_description,
        height=120,
        placeholder="e.g. predict whether a loan applicant will default",
    )

    auto_async = rows >= ASYNC_ROW_THRESHOLD
    st.sidebar.toggle(
        "Use async job mode",
        key="use_async_mode",
        value=auto_async,
        help="Auto-enabled for large datasets. Async mode polls /analyze-task-report-jobs.",
    )

    if st.sidebar.button("Run Audit", use_container_width=True, type="primary"):
        reset_run_state()
        start_audit_run()


def render_pre_run_view() -> None:
    st.markdown("### Before You Run")
    st.write("1. Upload a CSV in the sidebar.")
    st.write("2. Select target and sensitive columns.")
    st.write("3. Describe your ML task and click **Run Audit**.")


def render_dataset_preview() -> None:
    preview_info = st.session_state.preview_info
    if not isinstance(preview_info, dict):
        return

    rows = int(preview_info.get("rows", 0) or 0)
    columns = int(preview_info.get("columns", 0) or 0)
    st.caption(f"Preview: {rows} rows, {columns} columns")

    if st.session_state.df_preview is not None:
        st.dataframe(st.session_state.df_preview, use_container_width=True)


def render_clarification_section() -> None:
    questions = st.session_state.clarifying_questions
    if not questions:
        return

    st.warning("Task context is ambiguous. Please answer the questions below.")
    for question in questions:
        current_value = st.session_state.clarification_inputs.get(question, "")
        st.session_state.clarification_inputs[question] = st.text_input(
            question,
            value=current_value,
            key=f"clarify::{question}",
        )

    if st.button("Submit Answers", type="primary"):
        submit_clarification_answers()


def _severity_color(level: str) -> str:
    normalized = level.lower().strip()
    if normalized == "high":
        return "#d32f2f"
    if normalized == "medium":
        return "#ed6c02"
    return "#455a64"


def render_issue_cards(final_report: dict[str, Any]) -> None:
    issues = list(final_report.get("issues", []))
    if not issues:
        st.info("No issues returned in the final report.")
        return

    severity_rank = {"high": 0, "medium": 1, "low": 2}

    def _sort_key(item: dict[str, Any]) -> tuple[int, str]:
        statistical = item.get("statistical_issue", {})
        severity = str(statistical.get("severity", "low")).lower()
        issue_id = str(statistical.get("issue_id", ""))
        return (severity_rank.get(severity, 3), issue_id)

    sorted_issues = sorted(issues, key=_sort_key)

    st.subheader("Risk Findings")
    for entry in sorted_issues:
        statistical = entry.get("statistical_issue", {}) or {}
        interpretation = entry.get("interpretation", {}) or {}
        mitigations = list(entry.get("mitigations", []) or [])

        severity = str(statistical.get("severity", "low")).lower()
        color = _severity_color(severity)
        issue_type = str(statistical.get("type", "dataset_issue")).replace("_", " ").title()
        description = str(statistical.get("description", ""))

        st.markdown(
            f"""
            <div class=\"issue-card\" style=\"border-left: 8px solid {color};\">
                <div class=\"issue-head\">
                    <span class=\"severity-pill\" style=\"background:{color};\">{severity.upper()}</span>
                    <span class=\"issue-title\">{issue_type}</span>
                </div>
                <div class=\"issue-desc\">{description}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        why_harmful = str(interpretation.get("why_harmful", "")).strip()
        likely_impact = str(interpretation.get("likely_model_impact", "")).strip()
        severity_rationale = str(interpretation.get("severity_rationale", "")).strip()

        if why_harmful:
            st.markdown(f"**Why it matters:** {why_harmful}")
        if likely_impact:
            st.markdown(f"**Likely model impact:** {likely_impact}")
        if severity_rationale:
            st.markdown(f"**Rationale:** {severity_rationale}")

        if mitigations:
            st.markdown("**Recommended fixes:**")
            for mitigation in mitigations:
                title = str(mitigation.get("title", "Mitigation"))
                when_to_use = str(mitigation.get("when_to_use", "")).strip()
                tradeoffs = str(mitigation.get("tradeoffs", "")).strip()
                expected_impact = str(mitigation.get("expected_impact", "")).strip()
                st.markdown(f"- **{title}**")
                if when_to_use:
                    st.markdown(f"  Use when: {when_to_use}")
                if tradeoffs:
                    st.markdown(f"  Tradeoffs: {tradeoffs}")
                if expected_impact:
                    st.markdown(f"  Expected impact: {expected_impact}")
        st.divider()


def render_inline_charts(final_report: dict[str, Any], layer1_report: dict[str, Any] | None) -> None:
    if not layer1_report:
        st.caption("Layer 1 chart data is unavailable for inline visualization.")
        return

    st.subheader("Inline Charts")
    c1, c2 = st.columns(2)
    with c1:
        st.image(
            build_class_distribution_chart(layer1_report),
            caption="Class distribution",
            use_container_width=True,
        )
    with c2:
        st.image(
            build_severity_summary_chart(layer1_report),
            caption="Severity breakdown",
            use_container_width=True,
        )

    st.image(
        build_issue_type_chart(final_report),
        caption="Issue types",
        use_container_width=True,
    )

    has_subgroup_issue = any(
        (issue or {}).get("type") == "demographic_parity_gap"
        for issue in list(layer1_report.get("issues", []))
    )
    if has_subgroup_issue:
        st.image(
            build_demographic_parity_chart(layer1_report),
            caption="Subgroup outcome comparison",
            use_container_width=True,
        )


def render_downloads() -> None:
    st.subheader("Reports")
    c1, c2 = st.columns(2)

    with c1:
        if st.session_state.pdf_bytes:
            st.download_button(
                "Download PDF Report",
                data=st.session_state.pdf_bytes,
                file_name="auditlens_report.pdf",
                mime="application/pdf",
                use_container_width=True,
                type="primary",
            )
        else:
            st.button(
                "Download PDF Report",
                disabled=True,
                use_container_width=True,
                help="PDF not available for this run.",
            )

    with c2:
        markdown_content = st.session_state.markdown_text or ""
        st.download_button(
            "Download Markdown Report",
            data=markdown_content,
            file_name="auditlens_report.md",
            mime="text/markdown",
            use_container_width=True,
        )

    stored_artifact = st.session_state.stored_artifact
    if isinstance(stored_artifact, dict):
        artifact_id = str(stored_artifact.get("artifact_id", "")).strip()
        filename = str(stored_artifact.get("filename", "auditlens_report.bin"))
        media_type = str(stored_artifact.get("media_type", "application/octet-stream"))
        if artifact_id:
            try:
                stored_bytes = download_bytes(f"/reports/{artifact_id}/download")
                st.download_button(
                    "Download Stored Artifact (Server Copy)",
                    data=stored_bytes,
                    file_name=filename,
                    mime=media_type,
                    use_container_width=True,
                )
            except ApiError as exc:
                st.caption(f"Stored artifact unavailable: {exc}")


def render_final_report_section() -> None:
    final_report = st.session_state.final_report
    if not isinstance(final_report, dict):
        return

    issues = list(final_report.get("issues", []))
    dataset_name = st.session_state.file_name or "dataset"
    rows = int((st.session_state.preview_info or {}).get("rows", 0) or 0)

    st.success(f"Audit complete for {dataset_name}: {rows} rows, {len(issues)} issues found.")

    reproducibility = final_report.get("reproducibility", {}) or {}
    provider = str(reproducibility.get("layer2_provider", "unknown"))
    model = str(reproducibility.get("layer2_model", "unknown"))
    st.caption(f"Layer 2 provider: {provider} | Model: {model}")

    render_issue_cards(final_report)
    render_inline_charts(final_report, st.session_state.layer1_report)
    render_downloads()


def render_app() -> None:
    apply_styles()
    render_sidebar()
    render_header()
    render_dataset_preview()

    poll_async_job_if_needed()

    if st.session_state.pending_job_id:
        st.info("Audit job is running in the background. Results will appear automatically.")

    if st.session_state.clarifying_questions:
        render_clarification_section()

    if st.session_state.final_report:
        render_final_report_section()
    elif not st.session_state.clarifying_questions:
        render_pre_run_view()
