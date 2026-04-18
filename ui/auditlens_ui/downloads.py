from __future__ import annotations

import streamlit as st

from frontend.api_client import ApiError, download_bytes


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
