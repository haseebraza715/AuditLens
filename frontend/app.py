from __future__ import annotations

import streamlit as st

from frontend.state import init_state
from frontend.ui import render_app


def main() -> None:
    st.set_page_config(
        page_title="AuditLens UI",
        page_icon="AI",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    init_state()
    render_app()


if __name__ == "__main__":
    main()
