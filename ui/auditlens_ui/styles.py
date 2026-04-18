from __future__ import annotations

import streamlit as st

SEVERITY_COLORS = {
    "high": "#d32f2f",
    "medium": "#ed6c02",
    "low": "#455a64",
}


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

        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #f8fafc 0%, #eef3f9 100%);
            border-right: 1px solid rgba(16, 42, 67, 0.12);
        }

        [data-testid="stSidebar"] * {
            color: #102a43 !important;
        }

        html, body {
            font-family: 'Space Grotesk', sans-serif;
            color: #102a43;
        }

        .stApp [data-testid="stMarkdownContainer"] * {
            color: #102a43 !important;
        }

        .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6,
        .stApp p, .stApp li, .stApp label, .stApp .stCaption {
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
        </style>
        """,
        unsafe_allow_html=True,
    )
