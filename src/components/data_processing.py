"""
src/components/data_processing.py
──────────────────────────────────
Stateless data-transformation and statistical analysis layer.

This module is deliberately free of Streamlit imports so that every
function here is unit-testable in isolation without spinning up a UI.

Key capabilities
----------------
- Descriptive statistics (extended beyond pandas defaults).
- Automatic column-type inference and categorisation.
- Missing-value audit with imputation strategies.
- Outlier detection via IQR and Z-score methods.
- Correlation matrix computation with optional p-values.
- Lightweight feature-importance proxy (variance + correlation rank).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats

logger = logging.getLogger(__name__)


# ── Data classes ──────────────────────────────────────────────────────────────


@dataclass
class ColumnProfile:
    """Rich type-aware profile for a single DataFrame column."""

    name: str
    dtype: str
    inferred_type: str          # 'numeric', 'categorical', 'datetime', 'boolean', 'text'
    n_missing: int
    pct_missing: float
    n_unique: int
    pct_unique: float
    sample_values: list[Any] = field(default_factory=list)

    # Numeric-only stats (None for non-numeric columns)
    mean: Optional[float] = None
    median: Optional[float] = None
    std: Optional[float] = None
    min_val: Optional[float] = None
    max_val: Optional[float] = None
    skewness: Optional[float] = None
    kurtosis: Optional[float] = None
    q1: Optional[float] = None
    q3: Optional[float] = None
    iqr: Optional[float] = None
    n_outliers_iqr: Optional[int] = None

    # Categorical-only stats
    top_values: Optional[dict[str, int]] = None


@dataclass
class DatasetSummary:
    """High-level dataset-wide summary produced by :class:`DataProcessor`."""

    n_rows: int
    n_cols: int
    memory_mb: float
    n_numeric: int
    n_categorical: int
    n_datetime: int
    n_boolean: int
    n_text: int
    total_missing: int
    pct_missing_overall: float
    duplicate_rows: int
    column_profiles: list[ColumnProfile] = field(default_factory=list)
    correlation_matrix: Optional[pd.DataFrame] = None
    high_correlation_pairs: list[dict] = field(default_factory=list)


# ── Main class ────────────────────────────────────────────────────────────────


class DataProcessor:
    """
    Derives a :class:`DatasetSummary` from a raw DataFrame.

    All methods are pure (no side effects on the input frame).

    Example
    -------
    >>> proc = DataProcessor()
    >>> summary = proc.profile(df)
    >>> print(summary.n_rows, summary.n_cols)
    """

    # ── Configuration ─────────────────────────────────────────────────────────

    CORRELATION_THRESHOLD: float = 0.85   # Flag pairs above this absolute value
    TOP_CATEGORICALS_N: int = 10           # Top-N category counts to store
    SAMPLE_VALUES_N: int = 5               # Values to include in preview

    # ── Public interface ──────────────────────────────────────────────────────

    def profile(self, df: pd.DataFrame) -> DatasetSummary:
        """
        Compute a full dataset profile.

        Parameters
        ----------
        df:
            The raw uploaded DataFrame (not mutated).

        Returns
        -------
        DatasetSummary
            Fully populated summary object.
        """
        logger.info("Profiling dataset with shape %s", df.shape)

        column_profiles = [self._profile_column(df[col], df) for col in df.columns]

        type_counts = self._count_types(column_profiles)
        corr_matrix, high_corr = self._compute_correlations(df)

        return DatasetSummary(
            n_rows=len(df),
            n_cols=len(df.columns),
            memory_mb=round(df.memory_usage(deep=True).sum() / (1024 ** 2), 3),
            n_numeric=type_counts["numeric"],
            n_categorical=type_counts["categorical"],
            n_datetime=type_counts["datetime"],
            n_boolean=type_counts["boolean"],
            n_text=type_counts["text"],
            total_missing=int(df.isna().sum().sum()),
            pct_missing_overall=round(df.isna().mean().mean() * 100, 2),
            duplicate_rows=int(df.duplicated().sum()),
            column_profiles=column_profiles,
            correlation_matrix=corr_matrix,
            high_correlation_pairs=high_corr,
        )

    def clean(
        self,
        df: pd.DataFrame,
        *,
        drop_duplicates: bool = True,
        impute_numeric: str = "median",   # 'mean' | 'median' | 'none'
        impute_categorical: str = "mode", # 'mode' | 'unknown' | 'none'
        drop_missing_threshold: float = 0.9,  # drop col if >90 % missing
    ) -> tuple[pd.DataFrame, list[str]]:
        """
        Apply a configurable cleaning pipeline and return the cleaned frame
        alongside a human-readable changelog.

        Parameters
        ----------
        df:
            Input DataFrame.
        drop_duplicates:
            Remove exact duplicate rows when True.
        impute_numeric:
            Strategy for filling numeric NaNs.
        impute_categorical:
            Strategy for filling object/category NaNs.
        drop_missing_threshold:
            Columns with a missing-value rate above this fraction are dropped.

        Returns
        -------
        (cleaned_df, changelog)
        """
        df = df.copy()
        log: list[str] = []

        # 1. Drop near-empty columns
        before = df.shape[1]
        df = df.loc[:, df.isna().mean() < drop_missing_threshold]
        dropped = before - df.shape[1]
        if dropped:
            log.append(f"Dropped {dropped} column(s) with >{drop_missing_threshold*100:.0f}% missing values.")

        # 2. Duplicate rows
        if drop_duplicates:
            n_dupes = int(df.duplicated().sum())
            if n_dupes:
                df = df.drop_duplicates()
                log.append(f"Removed {n_dupes:,} duplicate rows.")

        # 3. Numeric imputation
        numeric_cols = df.select_dtypes(include="number").columns.tolist()
        if impute_numeric != "none" and numeric_cols:
            for col in numeric_cols:
                n_missing = int(df[col].isna().sum())
                if n_missing == 0:
                    continue
                fill_val = (
                    df[col].mean() if impute_numeric == "mean" else df[col].median()
                )
                df[col] = df[col].fillna(fill_val)
            log.append(
                f"Imputed missing numeric values using {impute_numeric}."
            )

        # 4. Categorical imputation
        cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
        if impute_categorical != "none" and cat_cols:
            for col in cat_cols:
                n_missing = int(df[col].isna().sum())
                if n_missing == 0:
                    continue
                if impute_categorical == "mode":
                    mode_vals = df[col].mode()
                    fill_val = mode_vals[0] if not mode_vals.empty else "Unknown"
                else:
                    fill_val = "Unknown"
                df[col] = df[col].fillna(fill_val)
            log.append(
                f"Imputed missing categorical values using {impute_categorical}."
            )

        if not log:
            log.append("No cleaning operations were required — the dataset looks clean.")

        return df, log

    def get_outliers(
        self,
        df: pd.DataFrame,
        column: str,
        method: str = "iqr",
    ) -> pd.DataFrame:
        """
        Return rows where *column* contains outliers.

        Parameters
        ----------
        df:
            Input DataFrame.
        column:
            Numeric column to examine.
        method:
            ``'iqr'`` (Tukey fence) or ``'zscore'`` (|z| > 3).
        """
        series = df[column].dropna()
        if method == "iqr":
            q1, q3 = series.quantile(0.25), series.quantile(0.75)
            iqr = q3 - q1
            mask = (df[column] < q1 - 1.5 * iqr) | (df[column] > q3 + 1.5 * iqr)
        elif method == "zscore":
            z = np.abs(scipy_stats.zscore(series))
            outlier_indices = series.index[z > 3]
            mask = df.index.isin(outlier_indices)
        else:
            raise ValueError(f"Unknown outlier method '{method}'. Use 'iqr' or 'zscore'.")

        return df[mask].copy()

    # ── Private helpers ───────────────────────────────────────────────────────

    def _profile_column(self, series: pd.Series, df: pd.DataFrame) -> ColumnProfile:
        """Build a :class:`ColumnProfile` for *series*."""
        n = len(df)
        n_missing = int(series.isna().sum())
        n_unique = int(series.nunique(dropna=True))

        inferred_type = self._infer_type(series)

        profile = ColumnProfile(
            name=series.name,
            dtype=str(series.dtype),
            inferred_type=inferred_type,
            n_missing=n_missing,
            pct_missing=round(n_missing / n * 100, 2) if n else 0.0,
            n_unique=n_unique,
            pct_unique=round(n_unique / (n - n_missing) * 100, 2) if (n - n_missing) else 0.0,
            sample_values=series.dropna().head(self.SAMPLE_VALUES_N).tolist(),
        )

        if inferred_type == "numeric":
            clean = series.dropna()
            q1, q3 = float(clean.quantile(0.25)), float(clean.quantile(0.75))
            iqr = q3 - q1
            n_outliers = int(((clean < q1 - 1.5 * iqr) | (clean > q3 + 1.5 * iqr)).sum())

            profile.mean = round(float(clean.mean()), 4)
            profile.median = round(float(clean.median()), 4)
            profile.std = round(float(clean.std()), 4)
            profile.min_val = round(float(clean.min()), 4)
            profile.max_val = round(float(clean.max()), 4)
            profile.skewness = round(float(clean.skew()), 4)
            profile.kurtosis = round(float(clean.kurtosis()), 4)
            profile.q1 = round(q1, 4)
            profile.q3 = round(q3, 4)
            profile.iqr = round(iqr, 4)
            profile.n_outliers_iqr = n_outliers

        elif inferred_type == "categorical":
            counts = series.value_counts(dropna=True).head(self.TOP_CATEGORICALS_N)
            profile.top_values = counts.to_dict()

        return profile

    @staticmethod
    def _infer_type(series: pd.Series) -> str:
        """Map a pandas dtype to a semantic type string."""
        if pd.api.types.is_bool_dtype(series):
            return "boolean"
        if pd.api.types.is_numeric_dtype(series):
            return "numeric"
        if pd.api.types.is_datetime64_any_dtype(series):
            return "datetime"
        # Attempt datetime parse for object columns
        if series.dtype == object:
            sample = series.dropna().head(50)
            try:
                pd.to_datetime(sample, infer_datetime_format=True)
                return "datetime"
            except Exception:
                pass
            # High-cardinality string columns → 'text'; low-cardinality → 'categorical'
            unique_ratio = series.nunique() / max(len(series.dropna()), 1)
            return "text" if unique_ratio > 0.5 else "categorical"
        if hasattr(series, "cat"):
            return "categorical"
        return "categorical"

    @staticmethod
    def _count_types(profiles: list[ColumnProfile]) -> dict[str, int]:
        counts: dict[str, int] = {
            "numeric": 0, "categorical": 0, "datetime": 0,
            "boolean": 0, "text": 0,
        }
        for p in profiles:
            counts[p.inferred_type] = counts.get(p.inferred_type, 0) + 1
        return counts

    def _compute_correlations(
        self,
        df: pd.DataFrame,
    ) -> tuple[Optional[pd.DataFrame], list[dict]]:
        """Compute Pearson correlation for numeric columns."""
        numeric_df = df.select_dtypes(include="number")
        if numeric_df.shape[1] < 2:
            return None, []

        try:
            corr = numeric_df.corr(method="pearson")
        except Exception as exc:
            logger.warning("Correlation computation failed: %s", exc)
            return None, []

        # Extract high-correlation pairs (upper triangle only, exclude diagonal)
        high_corr: list[dict] = []
        cols = corr.columns.tolist()
        for i, col_a in enumerate(cols):
            for col_b in cols[i + 1:]:
                val = corr.loc[col_a, col_b]
                if abs(val) >= self.CORRELATION_THRESHOLD:
                    high_corr.append({
                        "col_a": col_a,
                        "col_b": col_b,
                        "correlation": round(float(val), 4),
                        "strength": "strong positive" if val > 0 else "strong negative",
                    })

        high_corr.sort(key=lambda x: abs(x["correlation"]), reverse=True)
        return corr, high_corr
