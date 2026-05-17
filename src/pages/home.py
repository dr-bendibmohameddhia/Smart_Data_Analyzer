"""
src/pages/home.py
──────────────────
Landing page — file upload, format guidance, and first-load preview.

The page purposely keeps the analysis light: it validates the upload,
shows a raw preview, and hands the user off to the Analyze page.
All heavy processing is deferred to avoid blocking the initial render.
"""

from __future__ import annotations

import streamlit as st

from src.components.data_loader import load_dataframe
from src.components.utils import format_bytes, pluralise


def render() -> None:
    """Entry point called by main.py when the Home page is active."""

    # ── Hero section ──────────────────────────────────────────────────────────
    st.markdown(
        """
        <div style="
            padding: 2.5rem 2rem 1.5rem;
            background: linear-gradient(135deg, #0F1623 0%, #161D2E 100%);
            border: 1px solid #1E2A40;
            border-radius: 12px;
            margin-bottom: 1.5rem;
        ">
            <h1 style="
                font-family: 'Georgia', serif;
                font-size: 2.4rem;
                font-weight: 700;
                color: #E8EDF5;
                margin: 0 0 0.5rem;
                letter-spacing: -0.5px;
            ">Smart Data Analyzer</h1>
            <p style="
                font-size: 1.05rem;
                color: #8C9AB7;
                margin: 0;
                max-width: 560px;
                line-height: 1.6;
            ">
                Upload a structured dataset and get instant statistical profiles,
                interactive charts, correlation analysis, and outlier detection —
                no code required.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Feature highlights ────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    _feature_card(col1, "📊", "Statistical Profiles", "Mean, median, std, skew, kurtosis per column")
    _feature_card(col2, "📈", "Interactive Charts", "Histograms, box plots, scatter, heatmaps")
    _feature_card(col3, "🔍", "Outlier Detection", "IQR and Z-score based flagging")
    _feature_card(col4, "🧹", "Data Cleaning", "Missing value imputation & duplicate removal")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Upload widget ─────────────────────────────────────────────────────────
    st.markdown("### Upload your dataset")
    st.caption("Supported formats: CSV, TSV, Excel (.xlsx / .xls), Parquet · Max size: 200 MB")

    uploaded_file = st.file_uploader(
        label="Drop a file here or click to browse",
        type=["csv", "tsv", "xlsx", "xls", "parquet"],
        key="home_uploader",
        label_visibility="collapsed",
    )

    if uploaded_file is None:
        _show_sample_hint()
        return

    # ── Load & validate ───────────────────────────────────────────────────────
    with st.spinner("Reading file…"):
        file_bytes = uploaded_file.read()
        result = load_dataframe(file_bytes, uploaded_file.name)

    if not result.success:
        st.error(f"**Upload failed:** {result.error_message}")
        return

    # Surface any non-fatal warnings
    for warning in result.warnings:
        st.warning(warning)

    # Persist the result in session state so other pages can access it
    st.session_state["load_result"] = result
    st.session_state["df"] = result.df

    # ── Success banner ────────────────────────────────────────────────────────
    st.success(
        f"✓ **{result.filename}** loaded — "
        f"{pluralise(result.n_rows, 'row')}, "
        f"{pluralise(result.n_cols, 'column')}, "
        f"{format_bytes(result.file_size_bytes)} on disk, "
        f"{result.memory_usage_mb:.1f} MB in memory."
    )

    # ── Data preview ─────────────────────────────────────────────────────────
    st.markdown("### Preview")
    preview_rows = st.slider("Rows to preview", min_value=5, max_value=50, value=10, step=5)
    st.dataframe(result.df.head(preview_rows), use_container_width=True)

    # ── Column schema ─────────────────────────────────────────────────────────
    with st.expander("Column schema", expanded=False):
        schema = result.df.dtypes.reset_index()
        schema.columns = ["Column", "dtype"]
        schema["Non-null count"] = result.df.notnull().sum().values
        schema["Null count"] = result.df.isnull().sum().values
        schema["Null %"] = (result.df.isnull().mean() * 100).round(1).values
        st.dataframe(schema, use_container_width=True, hide_index=True)

    # ── CTA ───────────────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    st.info("👆 Head to the **Analyze** page in the sidebar to run the full analysis.", icon="ℹ️")


# ── Private helpers ───────────────────────────────────────────────────────────


def _feature_card(col, icon: str, title: str, description: str) -> None:
    with col:
        st.markdown(
            f"""
            <div style="
                background: #161D2E;
                border: 1px solid #1E2A40;
                border-radius: 10px;
                padding: 1rem;
                height: 100%;
                text-align: center;
            ">
                <div style="font-size: 1.8rem; margin-bottom: 0.4rem;">{icon}</div>
                <div style="font-weight: 600; color: #E8EDF5; font-size: 0.9rem;
                            margin-bottom: 0.3rem;">{title}</div>
                <div style="color: #8C9AB7; font-size: 0.78rem; line-height: 1.4;">
                    {description}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _show_sample_hint() -> None:
    """Encourage the user with an example workflow when no file is loaded."""
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("💡 Don't have a dataset handy? Try these public sources", expanded=False):
        st.markdown(
            """
            | Dataset | Source | Notes |
            |---------|--------|-------|
            | Titanic passenger list | [Kaggle](https://www.kaggle.com/c/titanic) | Mix of numeric & categorical |
            | Iris flower measurements | [UCI ML Repo](https://archive.ics.uci.edu/ml/datasets/iris) | Classic classification dataset |
            | NYC Taxi trips (sample) | [NYC Open Data](https://opendata.cityofnewyork.us/) | Time-series + geo columns |
            | World happiness report | [Kaggle](https://www.kaggle.com/datasets/unsdsn/world-happiness) | Clean, small, no missing values |
            """
        )
