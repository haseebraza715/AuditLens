from __future__ import annotations

import streamlit as st

from auditlens_ui.clarification import render_clarification_section
from auditlens_ui.header import render_header, render_step_tracker
from auditlens_ui.risk_findings import render_final_report_section
from auditlens_ui.sidebar import render_sidebar
from auditlens_ui.styles import apply_styles
from auditlens_ui.workflow import poll_async_job_if_needed


def _compute_step() -> int:
    has_file = bool(st.session_state.file_bytes)
    configured = bool(st.session_state.target_column) and bool(st.session_state.sensitive_columns)
    running_or_clarifying = bool(st.session_state.pending_job_id) or bool(st.session_state.clarifying_questions)
    complete = isinstance(st.session_state.final_report, dict)

    if complete:
        return 3
    if running_or_clarifying:
        return 2
    if has_file and configured:
        return 1
    return 0


def _render_empty_state() -> None:
    st.markdown(
        """
        <div style="max-width:760px; margin:2rem auto; text-align:center; background:#ffffffcc; border:1px solid #dfe7ef; border-radius:14px; padding:1.2rem 1.4rem;">
            <h3 style="margin-top:0;">Start Your Bias Audit</h3>
            <p style="margin-bottom:0.4rem;">1. Upload a CSV in the sidebar.</p>
            <p style="margin-bottom:0.4rem;">2. Select target and sensitive columns.</p>
            <p style="margin-bottom:0;">3. Describe the decision task and run the audit.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_app() -> None:
    apply_styles()
    render_sidebar()
    render_header()
    render_step_tracker(_compute_step())

    poll_async_job_if_needed()
    if st.session_state.pending_job_id:
        st.info("Audit job running. Results will appear automatically.")
    elif st.session_state.clarifying_questions:
        render_clarification_section()
    elif st.session_state.final_report:
        render_final_report_section()
    else:
        _render_empty_state()
