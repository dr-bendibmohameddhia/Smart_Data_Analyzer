"""
src/components/data_visualization.py
──────────────────────────────────────
Plotly-based charting layer for the Smart Data Analyzer.

All chart-builder methods return a ``plotly.graph_objects.Figure`` object so
the caller can render it with ``st.plotly_chart(fig, use_container_width=True)``
or export it programmatically without coupling to Streamlit.

Design principles
-----------------
- Single responsibility: this module *only* builds figures.
- Consistent colour palette and layout theme applied globally via
  :meth:`DataVisualizer._apply_theme`.
- Every method accepts plain Python / pandas arguments — no Streamlit types.
"""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.figure_factory as ff
import plotly.graph_objects as go
from plotly.subplots import make_subplots

logger = logging.getLogger(__name__)

# ── Brand palette ─────────────────────────────────────────────────────────────

PALETTE = {
    "primary":   "#4F8EF7",
    "secondary": "#F76B4F",
    "success":   "#4FBF75",
    "warning":   "#F7C84F",
    "muted":     "#8C9AB7",
    "bg":        "#0F1623",
    "surface":   "#161D2E",
    "border":    "#1E2A40",
    "text":      "#E8EDF5",
    "subtext":   "#8C9AB7",
}

SEQUENTIAL = px.colors.sequential.Blues
DIVERGING  = px.colors.diverging.RdBu
QUALITATIVE = px.colors.qualitative.Set2


# ── Main class ────────────────────────────────────────────────────────────────


class DataVisualizer:
    """
    Factory for all application charts.

    Instantiate once and call the relevant builder method for each chart type.
    """

    # ── Theme & layout helpers ────────────────────────────────────────────────

    def _apply_theme(self, fig: go.Figure, title: str = "") -> go.Figure:
        """Apply the global dark theme and typography to *fig*."""
        fig.update_layout(
            title=dict(text=title, font=dict(size=16, color=PALETTE["text"]), x=0.01),
            paper_bgcolor=PALETTE["surface"],
            plot_bgcolor=PALETTE["surface"],
            font=dict(family="'Inter', sans-serif", size=12, color=PALETTE["text"]),
            margin=dict(l=40, r=20, t=50, b=40),
            legend=dict(
                bgcolor=PALETTE["bg"],
                bordercolor=PALETTE["border"],
                borderwidth=1,
                font=dict(size=11),
            ),
            hoverlabel=dict(
                bgcolor=PALETTE["bg"],
                bordercolor=PALETTE["border"],
                font_size=12,
                font_color=PALETTE["text"],
            ),
        )
        fig.update_xaxes(
            gridcolor=PALETTE["border"],
            zerolinecolor=PALETTE["border"],
            tickfont=dict(color=PALETTE["subtext"]),
        )
        fig.update_yaxes(
            gridcolor=PALETTE["border"],
            zerolinecolor=PALETTE["border"],
            tickfont=dict(color=PALETTE["subtext"]),
        )
        return fig

    # ── Distribution charts ───────────────────────────────────────────────────

    def histogram(
        self,
        df: pd.DataFrame,
        column: str,
        bins: int = 30,
        show_kde: bool = True,
    ) -> go.Figure:
        """Histogram with optional KDE overlay for a numeric column."""
        series = df[column].dropna()
        fig = go.Figure()

        fig.add_trace(
            go.Histogram(
                x=series,
                nbinsx=bins,
                name="Frequency",
                marker_color=PALETTE["primary"],
                opacity=0.75,
            )
        )

        if show_kde and len(series) > 1:
            try:
                from scipy.stats import gaussian_kde  # noqa: PLC0415
                kde = gaussian_kde(series)
                x_range = np.linspace(series.min(), series.max(), 300)
                # Scale KDE to histogram height
                bin_width = (series.max() - series.min()) / bins
                kde_y = kde(x_range) * len(series) * bin_width
                fig.add_trace(
                    go.Scatter(
                        x=x_range,
                        y=kde_y,
                        mode="lines",
                        name="KDE",
                        line=dict(color=PALETTE["secondary"], width=2),
                    )
                )
            except Exception as exc:
                logger.debug("KDE computation skipped: %s", exc)

        self._apply_theme(fig, f"Distribution of {column}")
        fig.update_layout(barmode="overlay", showlegend=show_kde)
        return fig

    def box_plot(
        self,
        df: pd.DataFrame,
        column: str,
        group_by: Optional[str] = None,
    ) -> go.Figure:
        """Box / whisker plot, optionally grouped by a categorical column."""
        if group_by and group_by in df.columns:
            fig = px.box(
                df,
                x=group_by,
                y=column,
                color=group_by,
                color_discrete_sequence=QUALITATIVE,
                points="outliers",
            )
        else:
            fig = px.box(df, y=column, color_discrete_sequence=[PALETTE["primary"]], points="outliers")

        self._apply_theme(fig, f"Box Plot — {column}")
        return fig

    def violin_plot(self, df: pd.DataFrame, column: str, group_by: Optional[str] = None) -> go.Figure:
        """Violin plot showing full distribution shape."""
        if group_by and group_by in df.columns:
            fig = px.violin(
                df, x=group_by, y=column, color=group_by,
                color_discrete_sequence=QUALITATIVE,
                box=True, points="outliers",
            )
        else:
            fig = px.violin(
                df, y=column,
                color_discrete_sequence=[PALETTE["primary"]],
                box=True, points="outliers",
            )
        self._apply_theme(fig, f"Violin Plot — {column}")
        return fig

    # ── Relationship charts ───────────────────────────────────────────────────

    def scatter(
        self,
        df: pd.DataFrame,
        x_col: str,
        y_col: str,
        color_col: Optional[str] = None,
        size_col: Optional[str] = None,
        trendline: bool = True,
    ) -> go.Figure:
        """Scatter plot with optional colour encoding and OLS trendline."""
        kwargs: dict = dict(x=x_col, y=y_col)
        if color_col:
            kwargs["color"] = color_col
        if size_col:
            kwargs["size"] = size_col
            kwargs["size_max"] = 20
        if trendline:
            kwargs["trendline"] = "ols"

        fig = px.scatter(
            df,
            **kwargs,
            color_discrete_sequence=QUALITATIVE,
            opacity=0.7,
        )
        self._apply_theme(fig, f"{x_col} vs {y_col}")
        return fig

    def correlation_heatmap(self, corr_matrix: pd.DataFrame) -> go.Figure:
        """Annotated correlation heat-map from a pre-computed correlation matrix."""
        z = corr_matrix.values
        labels = corr_matrix.columns.tolist()

        text = [[f"{val:.2f}" for val in row] for row in z]

        fig = go.Figure(
            go.Heatmap(
                z=z,
                x=labels,
                y=labels,
                text=text,
                texttemplate="%{text}",
                textfont=dict(size=10, color=PALETTE["text"]),
                colorscale=DIVERGING,
                zmid=0,
                zmin=-1,
                zmax=1,
                colorbar=dict(
                    thickness=14,
                    tickfont=dict(color=PALETTE["subtext"]),
                    title=dict(text="r", font=dict(color=PALETTE["subtext"])),
                ),
            )
        )
        self._apply_theme(fig, "Correlation Matrix")
        fig.update_xaxes(tickangle=-45)
        return fig

    def pair_plot(self, df: pd.DataFrame, columns: list[str], color_col: Optional[str] = None) -> go.Figure:
        """Scatter matrix for exploring pairwise relationships."""
        kwargs: dict = dict(dimensions=columns, color_discrete_sequence=QUALITATIVE)
        if color_col:
            kwargs["color"] = color_col
        fig = px.scatter_matrix(df, **kwargs, opacity=0.5)
        fig.update_traces(diagonal_visible=False, marker=dict(size=3))
        self._apply_theme(fig, "Pair Plot")
        fig.update_layout(height=600)
        return fig

    # ── Categorical charts ────────────────────────────────────────────────────

    def bar_chart(
        self,
        df: pd.DataFrame,
        column: str,
        top_n: int = 20,
        horizontal: bool = True,
    ) -> go.Figure:
        """Frequency bar chart for a categorical column."""
        counts = df[column].value_counts(dropna=True).head(top_n).reset_index()
        counts.columns = ["value", "count"]

        if horizontal:
            # Sort ascending so highest bar appears at the top
            counts = counts.sort_values("count")
            fig = px.bar(
                counts, x="count", y="value", orientation="h",
                color="count",
                color_continuous_scale=SEQUENTIAL,
            )
        else:
            fig = px.bar(
                counts, x="value", y="count",
                color="count",
                color_continuous_scale=SEQUENTIAL,
            )

        self._apply_theme(fig, f"Top {top_n} Values — {column}")
        fig.update_coloraxes(showscale=False)
        return fig

    def pie_chart(self, df: pd.DataFrame, column: str, top_n: int = 8) -> go.Figure:
        """Pie / donut chart for category share."""
        counts = df[column].value_counts(dropna=True)
        if len(counts) > top_n:
            other = counts.iloc[top_n:].sum()
            counts = counts.iloc[:top_n]
            counts["Other"] = other

        fig = go.Figure(
            go.Pie(
                labels=counts.index.tolist(),
                values=counts.values.tolist(),
                hole=0.45,
                marker=dict(colors=QUALITATIVE, line=dict(color=PALETTE["bg"], width=2)),
                textfont=dict(size=11, color=PALETTE["text"]),
            )
        )
        self._apply_theme(fig, f"Composition — {column}")
        return fig

    # ── Time-series charts ────────────────────────────────────────────────────

    def time_series(
        self,
        df: pd.DataFrame,
        date_col: str,
        value_col: str,
        resample_rule: Optional[str] = None,
    ) -> go.Figure:
        """
        Line chart for a numeric column over time.

        Parameters
        ----------
        resample_rule:
            Pandas offset alias (e.g. ``'M'``, ``'W'``, ``'D'``) to
            aggregate before plotting. ``None`` → plot raw rows.
        """
        ts = df[[date_col, value_col]].copy()
        ts[date_col] = pd.to_datetime(ts[date_col], errors="coerce")
        ts = ts.dropna().set_index(date_col).sort_index()

        if resample_rule:
            ts = ts[value_col].resample(resample_rule).mean().reset_index()
        else:
            ts = ts.reset_index()

        fig = go.Figure(
            go.Scatter(
                x=ts[date_col],
                y=ts[value_col],
                mode="lines",
                line=dict(color=PALETTE["primary"], width=2),
                fill="tozeroy",
                fillcolor=f"rgba(79,142,247,0.15)",
            )
        )
        self._apply_theme(fig, f"{value_col} over Time")
        return fig

    # ── Dataset-overview charts ───────────────────────────────────────────────

    def missing_values_chart(self, df: pd.DataFrame) -> go.Figure:
        """Horizontal bar chart showing % missing per column."""
        missing_pct = (df.isna().mean() * 100).sort_values(ascending=True)
        missing_pct = missing_pct[missing_pct > 0]

        if missing_pct.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="✓ No missing values detected",
                xref="paper", yref="paper",
                x=0.5, y=0.5,
                showarrow=False,
                font=dict(size=16, color=PALETTE["success"]),
            )
            self._apply_theme(fig, "Missing Values")
            return fig

        colors = [
            PALETTE["success"] if v < 5
            else PALETTE["warning"] if v < 20
            else PALETTE["secondary"]
            for v in missing_pct.values
        ]

        fig = go.Figure(
            go.Bar(
                x=missing_pct.values,
                y=missing_pct.index.tolist(),
                orientation="h",
                marker_color=colors,
                text=[f"{v:.1f}%" for v in missing_pct.values],
                textposition="outside",
                textfont=dict(size=10, color=PALETTE["subtext"]),
            )
        )
        self._apply_theme(fig, "Missing Values by Column (%)")
        fig.update_xaxes(title_text="% Missing", range=[0, 105])
        fig.update_layout(height=max(300, 30 * len(missing_pct) + 80))
        return fig

    def data_types_donut(self, type_counts: dict[str, int]) -> go.Figure:
        """Small donut chart showing the proportion of column types."""
        type_colors = {
            "numeric": PALETTE["primary"],
            "categorical": PALETTE["secondary"],
            "datetime": PALETTE["success"],
            "boolean": PALETTE["warning"],
            "text": PALETTE["muted"],
        }
        labels = [k for k, v in type_counts.items() if v > 0]
        values = [type_counts[k] for k in labels]
        colors = [type_colors.get(k, PALETTE["muted"]) for k in labels]

        fig = go.Figure(
            go.Pie(
                labels=labels,
                values=values,
                hole=0.55,
                marker=dict(colors=colors, line=dict(color=PALETTE["bg"], width=2)),
                textfont=dict(size=11, color=PALETTE["text"]),
            )
        )
        self._apply_theme(fig, "Column Types")
        fig.update_layout(height=300, showlegend=True)
        return fig

    def outlier_strip_chart(
        self,
        df: pd.DataFrame,
        column: str,
        outlier_indices: pd.Index,
    ) -> go.Figure:
        """Strip chart highlighting outlier rows in a different colour."""
        is_outlier = df.index.isin(outlier_indices)

        fig = go.Figure()
        for flag, label, color in [
            (False, "Normal", PALETTE["primary"]),
            (True, "Outlier", PALETTE["secondary"]),
        ]:
            subset = df.loc[is_outlier == flag, column].dropna()
            fig.add_trace(
                go.Box(
                    y=subset,
                    name=label,
                    marker_color=color,
                    boxpoints="all",
                    jitter=0.4,
                    pointpos=0,
                    marker=dict(size=4, opacity=0.6),
                )
            )
        self._apply_theme(fig, f"Outlier Analysis — {column}")
        return fig
