from __future__ import annotations

import streamlit as st


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


def render_step_tracker(current_step: int) -> None:
    labels = ["Upload", "Configure", "Analyze", "Results"]
    cols = st.columns(4)
    for idx, (col, label) in enumerate(zip(cols, labels)):
        if idx < current_step:
            col.markdown(f"**{idx + 1}. {label}**  \n`✓ Complete`")
        elif idx == current_step:
            col.markdown(f"**{idx + 1}. {label}**  \n`→ Current`")
        else:
            col.markdown(f"**{idx + 1}. {label}**  \n:gray[Pending]")
