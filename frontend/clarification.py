from __future__ import annotations

import streamlit as st

from frontend.workflow import submit_clarification_answers


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
