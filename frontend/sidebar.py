from __future__ import annotations

import streamlit as st

from frontend.constants import ASYNC_ROW_THRESHOLD
from frontend.state import reset_run_state
from frontend.workflow import on_new_file, start_audit_run


def _configured_columns() -> bool:
    return bool(st.session_state.target_column) and bool(st.session_state.sensitive_columns)


def render_sidebar() -> None:
    st.sidebar.header("Configuration")

    with st.sidebar.expander(
        "Connection Settings",
        expanded=not bool(st.session_state.api_base_url.strip()),
    ):
        st.text_input("Backend API URL", key="api_base_url")

    preview_info = st.session_state.preview_info if isinstance(st.session_state.preview_info, dict) else None
    file_uploaded = bool(st.session_state.file_bytes)

    with st.sidebar.expander("Data Upload", expanded=not file_uploaded):
        uploaded_file = st.file_uploader("Upload CSV", type=["csv"])
        if uploaded_file is not None:
            on_new_file(uploaded_file.name, uploaded_file.getvalue())

        if st.session_state.last_error:
            st.error(st.session_state.last_error)

        if preview_info:
            rows = int(preview_info.get("rows", 0) or 0)
            cols = int(preview_info.get("columns", 0) or 0)
            st.caption(f"{rows:,} rows · {cols} columns")

    if not preview_info:
        return

    column_names = list(preview_info.get("column_names", []))
    if not column_names:
        return

    with st.sidebar.expander("Column Configuration", expanded=not _configured_columns()):
        target_default = st.session_state.target_column
        if target_default not in column_names:
            target_default = column_names[-1]
        target_idx = column_names.index(target_default)
        st.session_state.target_column = st.selectbox(
            "Target column",
            options=column_names,
            index=target_idx,
        )

        sensitive_options = [c for c in column_names if c != st.session_state.target_column]
        current_sensitive = [c for c in st.session_state.sensitive_columns if c in sensitive_options]
        st.session_state.sensitive_columns = st.multiselect(
            "Sensitive columns",
            options=sensitive_options,
            default=current_sensitive,
            help="Choose one or more protected attributes to audit.",
        )

    needs_task = not bool(str(st.session_state.task_description).strip())
    with st.sidebar.expander("Run Options", expanded=_configured_columns() and needs_task):
        st.text_area(
            "Task description",
            key="task_description",
            height=120,
            placeholder="e.g. predict whether a loan applicant will default",
        )

        rows = int(preview_info.get("rows", 0) or 0)
        auto_async = rows >= ASYNC_ROW_THRESHOLD
        st.toggle(
            "Run as asynchronous background job",
            key="use_async_mode",
            value=auto_async,
            help="Recommended for large datasets. The app will poll job status automatically.",
        )

    if st.sidebar.button("Run Audit", type="primary", use_container_width=True):
        reset_run_state()
        start_audit_run()
