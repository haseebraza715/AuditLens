from __future__ import annotations

from typing import Any

import streamlit as st

from backend.layer3.visualizations import (
    build_class_distribution_chart,
    build_correlation_heatmap,
    build_demographic_parity_chart,
    build_fairness_overview_chart,
    build_issue_type_chart,
    build_missingness_heatmap,
    build_severity_summary_chart,
)


def render_inline_charts(final_report: dict[str, Any], layer1_report: dict[str, Any] | None) -> None:
    if not layer1_report:
        st.caption("Layer 1 chart data is unavailable for inline visualization.")
        return

    c1, c2 = st.columns(2)
    with c1:
        st.image(
            build_class_distribution_chart(layer1_report),
            caption="Class distribution",
            use_container_width=True,
        )
        st.image(
            build_severity_summary_chart(layer1_report),
            caption="Severity breakdown",
            use_container_width=True,
        )
    with c2:
        st.image(
            build_issue_type_chart(final_report),
            caption="Issue types",
            use_container_width=True,
        )
        st.image(
            build_fairness_overview_chart(layer1_report),
            caption="Fairness overview",
            use_container_width=True,
        )

    st.image(
        build_demographic_parity_chart(layer1_report),
        caption="Subgroup outcome comparison",
        use_container_width=True,
    )

    c3, c4 = st.columns(2)
    with c3:
        st.image(
            build_correlation_heatmap(layer1_report),
            caption="Sensitive correlation heatmap",
            use_container_width=True,
        )
    with c4:
        st.image(
            build_missingness_heatmap(layer1_report),
            caption="Differential missingness heatmap",
            use_container_width=True,
        )
