"""
src/pages/analyze_data.py
──────────────────────────
Core analysis page — the heart of the Smart Data Analyzer.

Tab layout
──────────
1. Overview       — dataset-wide KPIs, type breakdown, missing-value audit
2. Distributions  — per-column histogram / box / violin
3. Relationships  — scatter matrix, correlation heat-map, pair highlight
4. Outliers       — IQR / Z-score outlier explorer per column
5. Clean & Export — guided cleaning pipeline + CSV download
"""

from __future__ import annotations

import io
import logging

import pandas as pd
import streamlit as st

from src.components.data_processing import DataProcessor
from src.components.data_visualization import DataVisualizer
from src.components.utils import (
    categorical_columns,
    datetime_columns,
    humanize_number,
    numeric_columns,
    pluralise,
    safe_sample,
)

logger = logging.getLogger(__name__)

_processor = DataProcessor()
_viz = DataVisualizer()


# ── Page guard ────────────────────────────────────────────────────────────────


def _require_data() -> pd.DataFrame | None:
    """Return the active DataFrame or render an upload prompt and return None."""
    df = st.session_state.get("df")
    if df is None:
        st.info(
            "No dataset loaded yet. Go to the **Home** page and upload a file first.",
            icon="📂",
        )
    return df


# ── Entry point ───────────────────────────────────────────────────────────────


def render() -> None:
    df = _require_data()
    if df is None:
        return

    st.markdown("## Analysis")
    st.caption(
        f"Working with **{st.session_state['load_result'].filename}** — "
        f"{len(df):,} rows × {len(df.columns)} columns"
    )

    # Profile is expensive — cache it per-dataframe identity
    if "summary" not in st.session_state:
        with st.spinner("Profiling dataset…"):
            st.session_state["summary"] = _processor.profile(df)

    summary = st.session_state["summary"]

    tab_overview, tab_dist, tab_rel, tab_outlier, tab_clean = st.tabs([
        "📋 Overview",
        "📊 Distributions",
        "🔗 Relationships",
        "🔍 Outliers",
        "🧹 Clean & Export",
    ])

    with tab_overview:
        _render_overview(df, summary)

    with tab_dist:
        _render_distributions(df, summary)

    with tab_rel:
        _render_relationships(df, summary)

    with tab_outlier:
        _render_outliers(df)

    with tab_clean:
        _render_clean_export(df)


# ── Tab: Overview ─────────────────────────────────────────────────────────────


def _render_overview(df: pd.DataFrame, summary) -> None:
    # ── KPI row ───────────────────────────────────────────────────────────────
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Rows", humanize_number(summary.n_rows))
    k2.metric("Columns", summary.n_cols)
    k3.metric("Memory", f"{summary.memory_mb} MB")
    k4.metric("Missing values", f"{summary.pct_missing_overall:.1f}%")
    k5.metric("Duplicate rows", humanize_number(summary.duplicate_rows))

    st.markdown("---")

    # ── Column type breakdown ─────────────────────────────────────────────────
    left, right = st.columns([1, 2])

    with left:
        st.markdown("#### Column types")
        type_counts = {
            "numeric":     summary.n_numeric,
            "categorical": summary.n_categorical,
            "datetime":    summary.n_datetime,
            "boolean":     summary.n_boolean,
            "text":        summary.n_text,
        }
        st.plotly_chart(
            _viz.data_types_donut(type_counts),
            use_container_width=True,
            config={"displayModeBar": False},
        )

    with right:
        st.markdown("#### Missing values by column")
        st.plotly_chart(
            _viz.missing_values_chart(df),
            use_container_width=True,
            config={"displayModeBar": False},
        )

    # ── Descriptive statistics table ──────────────────────────────────────────
    st.markdown("#### Descriptive statistics")

    num_cols = numeric_columns(df)
    if num_cols:
        desc = df[num_cols].describe(percentiles=[0.05, 0.25, 0.5, 0.75, 0.95]).T
        desc.index.name = "Column"
        st.dataframe(desc.style.format("{:.4f}"), use_container_width=True)
    else:
        st.info("No numeric columns found.")

    # ── High-level column profile table ──────────────────────────────────────
    with st.expander("Column-level detail", expanded=False):
        rows = []
        for p in summary.column_profiles:
            rows.append({
                "Column":         p.name,
                "Type":           p.inferred_type,
                "dtype":          p.dtype,
                "Missing":        f"{p.pct_missing:.1f}%",
                "Unique values":  f"{p.n_unique:,}",
                "Mean/Top value": (
                    str(round(p.mean, 3)) if p.mean is not None
                    else (next(iter(p.top_values)) if p.top_values else "—")
                ),
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # ── High-correlation alert ────────────────────────────────────────────────
    if summary.high_correlation_pairs:
        st.markdown("#### ⚠️ High-correlation column pairs")
        st.caption(
            f"Pairs with |r| ≥ {DataProcessor.CORRELATION_THRESHOLD} — "
            "consider whether both columns are needed in downstream models."
        )
        st.dataframe(
            pd.DataFrame(summary.high_correlation_pairs),
            use_container_width=True,
            hide_index=True,
        )


# ── Tab: Distributions ────────────────────────────────────────────────────────


def _render_distributions(df: pd.DataFrame, summary) -> None:
    num_cols  = numeric_columns(df)
    cat_cols  = categorical_columns(df)
    date_cols = datetime_columns(df)

    # ── Numeric distributions ─────────────────────────────────────────────────
    if num_cols:
        st.markdown("#### Numeric distributions")
        col_sel = st.selectbox("Select column", num_cols, key="dist_num_col")
        chart_type = st.radio(
            "Chart type", ["Histogram", "Box plot", "Violin"], horizontal=True, key="dist_chart_type"
        )
        group_col = st.selectbox(
            "Group by (optional)", ["— none —"] + cat_cols, key="dist_group"
        )
        group = None if group_col == "— none —" else group_col

        if chart_type == "Histogram":
            bins = st.slider("Bins", 10, 100, 30, key="hist_bins")
            fig = _viz.histogram(df, col_sel, bins=bins)
        elif chart_type == "Box plot":
            fig = _viz.box_plot(df, col_sel, group_by=group)
        else:
            fig = _viz.violin_plot(df, col_sel, group_by=group)

        st.plotly_chart(fig, use_container_width=True)

        # Mini stats for the selected column ─────────────────────────────────
        profile = next((p for p in summary.column_profiles if p.name == col_sel), None)
        if profile and profile.mean is not None:
            c1, c2, c3, c4, c5, c6 = st.columns(6)
            c1.metric("Mean",     f"{profile.mean:,.4f}")
            c2.metric("Median",   f"{profile.median:,.4f}")
            c3.metric("Std dev",  f"{profile.std:,.4f}")
            c4.metric("Skewness", f"{profile.skewness:,.3f}")
            c5.metric("Kurtosis", f"{profile.kurtosis:,.3f}")
            c6.metric("IQR outliers", profile.n_outliers_iqr)

    st.markdown("---")

    # ── Categorical distributions ─────────────────────────────────────────────
    if cat_cols:
        st.markdown("#### Categorical distributions")
        cat_sel   = st.selectbox("Select column", cat_cols, key="dist_cat_col")
        cat_chart = st.radio("Chart type", ["Bar", "Pie / Donut"], horizontal=True, key="cat_chart_type")
        top_n     = st.slider("Top N categories", 5, 30, 15, key="cat_topn")

        if cat_chart == "Bar":
            st.plotly_chart(_viz.bar_chart(df, cat_sel, top_n=top_n), use_container_width=True)
        else:
            st.plotly_chart(_viz.pie_chart(df, cat_sel, top_n=top_n), use_container_width=True)

    # ── Time-series ────────────────────────────────────────────────────────────
    if date_cols and num_cols:
        st.markdown("---")
        st.markdown("#### Time-series")
        date_col  = st.selectbox("Date column", date_cols, key="ts_date")
        value_col = st.selectbox("Value column", num_cols, key="ts_value")
        resample  = st.selectbox(
            "Resample", ["None", "D (daily)", "W (weekly)", "M (monthly)", "Q (quarterly)"],
            key="ts_resample"
        )
        rule = None if resample == "None" else resample.split()[0]
        try:
            st.plotly_chart(
                _viz.time_series(df, date_col, value_col, resample_rule=rule),
                use_container_width=True,
            )
        except Exception as exc:
            st.error(f"Could not render time-series: {exc}")


# ── Tab: Relationships ────────────────────────────────────────────────────────


def _render_relationships(df: pd.DataFrame, summary) -> None:
    num_cols = numeric_columns(df)
    cat_cols = categorical_columns(df)

    if len(num_cols) < 2:
        st.info("At least two numeric columns are required for relationship analysis.")
        return

    # ── Correlation heat-map ──────────────────────────────────────────────────
    if summary.correlation_matrix is not None:
        st.markdown("#### Correlation matrix (Pearson r)")
        st.plotly_chart(
            _viz.correlation_heatmap(summary.correlation_matrix),
            use_container_width=True,
        )

    st.markdown("---")

    # ── Scatter plot ──────────────────────────────────────────────────────────
    st.markdown("#### Scatter plot")
    left, right = st.columns(2)
    x_col = left.selectbox("X axis", num_cols, key="scatter_x")
    y_col = right.selectbox("Y axis", num_cols, index=min(1, len(num_cols) - 1), key="scatter_y")

    color_opts = ["— none —"] + cat_cols + num_cols
    size_opts  = ["— none —"] + num_cols
    color_col  = st.selectbox("Color by", color_opts, key="scatter_color")
    size_col   = st.selectbox("Size by",  size_opts,  key="scatter_size")
    trendline  = st.checkbox("Show OLS trendline", value=True, key="scatter_trend")

    plot_df = safe_sample(df, n=5_000)
    st.plotly_chart(
        _viz.scatter(
            plot_df, x_col, y_col,
            color_col=None if color_col == "— none —" else color_col,
            size_col=None  if size_col  == "— none —" else size_col,
            trendline=trendline,
        ),
        use_container_width=True,
    )

    # ── Pair plot ─────────────────────────────────────────────────────────────
    if len(num_cols) >= 2:
        st.markdown("---")
        st.markdown("#### Pair plot")
        default_cols = num_cols[:min(5, len(num_cols))]
        pair_cols = st.multiselect(
            "Select columns (2–6 recommended)",
            num_cols,
            default=default_cols,
            key="pair_cols",
        )
        pair_color = st.selectbox("Color by", ["— none —"] + cat_cols, key="pair_color")
        if len(pair_cols) >= 2:
            plot_df2 = safe_sample(df, n=2_000)
            st.plotly_chart(
                _viz.pair_plot(
                    plot_df2, pair_cols,
                    color_col=None if pair_color == "— none —" else pair_color,
                ),
                use_container_width=True,
            )
        else:
            st.info("Select at least two columns to render the pair plot.")


# ── Tab: Outliers ─────────────────────────────────────────────────────────────


def _render_outliers(df: pd.DataFrame) -> None:
    num_cols = numeric_columns(df)
    if not num_cols:
        st.info("No numeric columns available for outlier detection.")
        return

    st.markdown("#### Outlier detection")
    col_sel = st.selectbox("Column", num_cols, key="outlier_col")
    method  = st.radio("Method", ["IQR (Tukey fence)", "Z-score (|z| > 3)"], horizontal=True, key="outlier_method")
    method_key = "iqr" if "IQR" in method else "zscore"

    try:
        outlier_df = _processor.get_outliers(df, col_sel, method=method_key)
    except Exception as exc:
        st.error(f"Outlier detection failed: {exc}")
        return

    n_outliers = len(outlier_df)
    pct = n_outliers / len(df) * 100 if len(df) else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("Total rows",    f"{len(df):,}")
    c2.metric("Outliers found", f"{n_outliers:,}")
    c3.metric("Outlier rate",  f"{pct:.2f}%")

    st.plotly_chart(
        _viz.outlier_strip_chart(df, col_sel, outlier_df.index),
        use_container_width=True,
    )

    if n_outliers > 0:
        with st.expander(f"View {pluralise(n_outliers, 'outlier row')}", expanded=False):
            st.dataframe(outlier_df, use_container_width=True)

            csv = outlier_df.to_csv(index=False).encode()
            st.download_button(
                "Download outlier rows as CSV",
                data=csv,
                file_name=f"outliers_{col_sel}.csv",
                mime="text/csv",
            )


# ── Tab: Clean & Export ───────────────────────────────────────────────────────


def _render_clean_export(df: pd.DataFrame) -> None:
    st.markdown("#### Cleaning pipeline")
    st.caption("Configure the operations below, then click **Run cleaning**.")

    with st.form("cleaning_form"):
        drop_dupes = st.checkbox("Drop duplicate rows", value=True)
        drop_thresh = st.slider(
            "Drop columns with more than X% missing",
            min_value=50, max_value=100, value=90, step=5,
            format="%d%%",
        )
        impute_num = st.selectbox(
            "Numeric imputation strategy",
            ["median", "mean", "none"],
        )
        impute_cat = st.selectbox(
            "Categorical imputation strategy",
            ["mode", "unknown", "none"],
        )
        submitted = st.form_submit_button("▶ Run cleaning", type="primary")

    if submitted:
        with st.spinner("Applying cleaning operations…"):
            clean_df, changelog = _processor.clean(
                df,
                drop_duplicates=drop_dupes,
                impute_numeric=impute_num,
                impute_categorical=impute_cat,
                drop_missing_threshold=drop_thresh / 100,
            )

        st.success("Cleaning complete.")

        # Show changelog ──────────────────────────────────────────────────────
        st.markdown("**Changelog**")
        for entry in changelog:
            st.markdown(f"- {entry}")

        # Before / after comparison ───────────────────────────────────────────
        b1, b2, b3, b4 = st.columns(4)
        b1.metric("Rows before",   f"{len(df):,}")
        b2.metric("Rows after",    f"{len(clean_df):,}", delta=f"{len(clean_df) - len(df):,}")
        b3.metric("Columns before", len(df.columns))
        b4.metric("Columns after",  len(clean_df.columns), delta=len(clean_df.columns) - len(df.columns))

        st.markdown("**Preview (first 10 rows)**")
        st.dataframe(clean_df.head(10), use_container_width=True)

        # Download button ─────────────────────────────────────────────────────
        csv_bytes = clean_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇ Download cleaned dataset (CSV)",
            data=csv_bytes,
            file_name="cleaned_data.csv",
            mime="text/csv",
        )

        # Persist cleaned frame in session state ──────────────────────────────
        if st.button("Use cleaned dataset for further analysis"):
            st.session_state["df"] = clean_df
            st.session_state.pop("summary", None)   # force re-profile
            st.success("Dataset updated. Re-open the Overview tab to see refreshed stats.")
