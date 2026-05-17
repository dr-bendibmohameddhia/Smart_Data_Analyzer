"""
src/main.py
────────────
Application entry point for the Smart Data Analyzer.

Run with:
    python -m streamlit run src/main.py

Responsibilities
----------------
- Configure global Streamlit page settings.
- Set up Python logging for the whole application.
- Render the sidebar navigation.
- Dispatch to the appropriate page renderer.
- Guard against stale session state (e.g. file removed between renders).
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import streamlit as st

# ── Path setup ────────────────────────────────────────────────────────────────
# Ensure the project root is on sys.path when the file is run directly,
# so relative imports inside src/ resolve correctly.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ── Logging configuration ─────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── Page imports (deferred to after path setup) ───────────────────────────────
from src.pages.home         import render as render_home       # noqa: E402
from src.pages.analyze_data import render as render_analyze    # noqa: E402
from src.pages.about        import render as render_about      # noqa: E402

# ── Streamlit global config ───────────────────────────────────────────────────
st.set_page_config(
    page_title="Smart Data Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": "https://github.com/your-org/smart-data-analyzer/discussions",
        "Report a bug": "https://github.com/your-org/smart-data-analyzer/issues",
        "About": "Smart Data Analyzer — instant insight from any CSV or Excel file.",
    },
)

# ── Global CSS injections ─────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    /* ── Typography ── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Georgia&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background: #0F1623;
        border-right: 1px solid #1E2A40;
    }

    /* ── Main content area ── */
    .main .block-container {
        padding-top: 1.5rem;
        max-width: 1200px;
    }

    /* ── Tab strip ── */
    [data-testid="stTabs"] button {
        font-weight: 500;
        font-size: 0.88rem;
    }

    /* ── Metric cards ── */
    [data-testid="metric-container"] {
        background: #161D2E;
        border: 1px solid #1E2A40;
        border-radius: 10px;
        padding: 0.75rem 1rem;
    }

    /* ── Scrollbar ── */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: #0F1623; }
    ::-webkit-scrollbar-thumb { background: #1E2A40; border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: #4F8EF7; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Navigation ────────────────────────────────────────────────────────────────

_PAGES: dict[str, str] = {
    "🏠  Home":         "Home",
    "📊  Analyze":      "Analyze",
    "ℹ️  About":        "About",
}

with st.sidebar:
    # Logo / wordmark
    st.markdown(
        """
        <div style="padding: 1rem 0 1.5rem;">
            <span style="
                font-family: 'Georgia', serif;
                font-size: 1.25rem;
                font-weight: 700;
                color: #E8EDF5;
                letter-spacing: -0.3px;
            ">Smart Data Analyzer</span>
            <br>
            <span style="font-size: 0.72rem; color: #4F8EF7; letter-spacing: 0.5px;">
                v1.0.0
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    selected_label = st.radio(
        "Navigation",
        options=list(_PAGES.keys()),
        label_visibility="collapsed",
        key="nav_radio",
    )
    selected_page = _PAGES[selected_label]

    # Active dataset indicator ─────────────────────────────────────────────────
    st.markdown("---")
    load_result = st.session_state.get("load_result")
    if load_result:
        st.markdown(
            f"""
            <div style="
                background: #161D2E;
                border: 1px solid #1E2A40;
                border-radius: 8px;
                padding: 0.75rem;
                font-size: 0.78rem;
                color: #8C9AB7;
            ">
                <div style="color: #4FBF75; font-weight: 600; margin-bottom: 0.3rem;">
                    ✓ Dataset loaded
                </div>
                <div style="color: #E8EDF5; word-break: break-all;">
                    {load_result.filename}
                </div>
                <div style="margin-top: 0.3rem;">
                    {load_result.n_rows:,} rows · {load_result.n_cols} cols
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Clear dataset", use_container_width=True):
            for key in ["df", "load_result", "summary"]:
                st.session_state.pop(key, None)
            st.rerun()
    else:
        st.caption("No dataset loaded yet.")

    st.markdown("---")
    st.caption("Built with Streamlit · MIT License" 
               "Project developed by Bendib Mohamed Dhia")


# ── Page dispatch ─────────────────────────────────────────────────────────────

logger.info("Rendering page: %s", selected_page)

if selected_page == "Home":
    render_home()
elif selected_page == "Analyze":
    render_analyze()
elif selected_page == "About":
    render_about()
else:
    st.error(f"Unknown page: '{selected_page}'")
