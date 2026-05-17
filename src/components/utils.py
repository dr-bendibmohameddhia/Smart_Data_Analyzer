"""
src/components/utils.py
────────────────────────
Lightweight utility functions shared across the application.

Kept intentionally small and pure — no external dependencies beyond
the standard library and pandas.
"""

from __future__ import annotations

import contextlib
import time
import logging
from typing import Generator

import pandas as pd

logger = logging.getLogger(__name__)


# ── Formatting helpers ────────────────────────────────────────────────────────


def format_bytes(n_bytes: int) -> str:
    """
    Return a human-readable file-size string.

    >>> format_bytes(1_048_576)
    '1.0 MB'
    >>> format_bytes(500)
    '500 B'
    """
    if n_bytes < 1024:
        return f"{n_bytes} B"
    if n_bytes < 1024 ** 2:
        return f"{n_bytes / 1024:.1f} KB"
    if n_bytes < 1024 ** 3:
        return f"{n_bytes / 1024 ** 2:.1f} MB"
    return f"{n_bytes / 1024 ** 3:.1f} GB"


def humanize_number(value: float | int) -> str:
    """
    Abbreviate large numbers for display.

    >>> humanize_number(1_500_000)
    '1.5M'
    >>> humanize_number(23_400)
    '23.4K'
    """
    abs_val = abs(value)
    sign = "-" if value < 0 else ""
    if abs_val >= 1_000_000_000:
        return f"{sign}{abs_val / 1_000_000_000:.1f}B"
    if abs_val >= 1_000_000:
        return f"{sign}{abs_val / 1_000_000:.1f}M"
    if abs_val >= 1_000:
        return f"{sign}{abs_val / 1_000:.1f}K"
    return f"{sign}{value:g}"


def truncate_string(text: str, max_len: int = 40) -> str:
    """Truncate *text* to *max_len* characters with an ellipsis."""
    return text if len(text) <= max_len else f"{text[:max_len - 1]}…"


# ── Timing / profiling ────────────────────────────────────────────────────────


@contextlib.contextmanager
def timer(label: str = "operation") -> Generator[None, None, None]:
    """
    Context manager that logs the elapsed time for a block.

    Usage
    -----
    >>> with timer("data load"):
    ...     df = pd.read_csv("big_file.csv")
    """
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        logger.debug("'%s' completed in %.3f s", label, elapsed)


# ── DataFrame helpers ─────────────────────────────────────────────────────────


def safe_sample(df: pd.DataFrame, n: int = 5_000, random_state: int = 42) -> pd.DataFrame:
    """
    Return at most *n* rows from *df*, sampling without replacement when
    the frame is larger.  Useful for feeding large datasets to charting
    functions that don't scale to millions of points.
    """
    if len(df) <= n:
        return df
    return df.sample(n=n, random_state=random_state)


def numeric_columns(df: pd.DataFrame) -> list[str]:
    """Return all numeric column names."""
    return df.select_dtypes(include="number").columns.tolist()


def categorical_columns(df: pd.DataFrame) -> list[str]:
    """Return all object / category column names."""
    return df.select_dtypes(include=["object", "category"]).columns.tolist()


def datetime_columns(df: pd.DataFrame) -> list[str]:
    """Return all datetime column names (already parsed or parseable)."""
    parsed = df.select_dtypes(include=["datetime64"]).columns.tolist()
    # Also probe object columns
    for col in df.select_dtypes(include="object").columns:
        try:
            pd.to_datetime(df[col].dropna().head(20), infer_datetime_format=True)
            parsed.append(col)
        except Exception:
            pass
    return list(dict.fromkeys(parsed))  # deduplicate while preserving order


def infer_target_column(df: pd.DataFrame) -> str | None:
    """
    Heuristically guess which column is most likely a prediction target.

    Rules (in order):
    1. Any numeric column whose name contains 'target', 'label', 'y', 'output'.
    2. The last numeric column in the frame.
    3. None if no numeric columns exist.
    """
    num_cols = numeric_columns(df)
    if not num_cols:
        return None

    keywords = {"target", "label", "y", "output", "class", "outcome"}
    for col in num_cols:
        if any(kw in col.lower() for kw in keywords):
            return col

    return num_cols[-1]


# ── Streamlit UI helpers ──────────────────────────────────────────────────────


def metric_delta_color(value: float, positive_is_good: bool = True) -> str:
    """
    Return ``'normal'``, ``'inverse'``, or ``'off'`` for
    ``st.metric``'s ``delta_color`` parameter based on the sign of *value*.
    """
    if value == 0:
        return "off"
    return "normal" if positive_is_good else "inverse"


def pluralise(n: int, singular: str, plural: str | None = None) -> str:
    """
    Return the correctly inflected noun phrase.

    >>> pluralise(1, "row")
    '1 row'
    >>> pluralise(5, "row")
    '5 rows'
    """
    if plural is None:
        plural = f"{singular}s"
    word = singular if n == 1 else plural
    return f"{n:,} {word}"
