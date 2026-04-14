from __future__ import annotations

from typing import Any

import streamlit as st

from frontend.constants import DEFAULT_API_BASE_URL


def init_state() -> None:
    defaults: dict[str, Any] = {
        "api_base_url": DEFAULT_API_BASE_URL,
        "file_name": None,
        "file_bytes": None,
        "file_signature": None,
        "preview_info": None,
        "df_preview": None,
        "target_column": None,
        "sensitive_columns": [],
        "task_description": "",
        "layer1_report": None,
        "audit_response": None,
        "final_report": None,
        "report_artifact": None,
        "stored_artifact": None,
        "pdf_bytes": None,
        "markdown_text": None,
        "clarifying_questions": [],
        "clarification_inputs": {},
        "task_context_partial": {},
        "pending_job_id": None,
        "last_error": None,
        "use_async_mode": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_run_state() -> None:
    st.session_state.layer1_report = None
    st.session_state.audit_response = None
    st.session_state.final_report = None
    st.session_state.report_artifact = None
    st.session_state.stored_artifact = None
    st.session_state.pdf_bytes = None
    st.session_state.markdown_text = None
    st.session_state.clarifying_questions = []
    st.session_state.clarification_inputs = {}
    st.session_state.task_context_partial = {}
    st.session_state.pending_job_id = None
    st.session_state.last_error = None
