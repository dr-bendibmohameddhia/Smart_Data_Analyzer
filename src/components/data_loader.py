"""
src/components/data_loader.py
─────────────────────────────
Handles all file ingestion logic for the Smart Data Analyzer.

Responsibilities
----------------
- Accept uploaded file objects from Streamlit's file_uploader widget.
- Detect file format and dispatch to the correct reader.
- Validate the resulting DataFrame (size limits, column sanity).
- Expose a lightweight metadata summary used by the UI layer.

Supported formats: CSV, TSV, Excel (.xlsx / .xls), Parquet.
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass, field
from typing import Optional

import pandas as pd
import streamlit as st

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────

MAX_FILE_SIZE_MB: int = 200
MAX_ROWS: int = 5_000_000
SUPPORTED_EXTENSIONS: tuple[str, ...] = (".csv", ".tsv", ".xlsx", ".xls", ".parquet")


# ── Data classes ─────────────────────────────────────────────────────────────


@dataclass
class LoadResult:
    """Value object returned by :class:`DataLoader.load`."""

    df: Optional[pd.DataFrame] = None
    filename: str = ""
    file_size_bytes: int = 0
    extension: str = ""
    success: bool = False
    error_message: str = ""
    warnings: list[str] = field(default_factory=list)

    # ── Derived convenience properties ───────────────────────────────────────

    @property
    def n_rows(self) -> int:
        return len(self.df) if self.df is not None else 0

    @property
    def n_cols(self) -> int:
        return len(self.df.columns) if self.df is not None else 0

    @property
    def file_size_mb(self) -> float:
        return round(self.file_size_bytes / (1024 ** 2), 2)

    @property
    def memory_usage_mb(self) -> float:
        if self.df is None:
            return 0.0
        return round(self.df.memory_usage(deep=True).sum() / (1024 ** 2), 2)


# ── Main class ────────────────────────────────────────────────────────────────


class DataLoader:
    """
    Stateless helper that converts an uploaded file into a validated
    :class:`pandas.DataFrame` wrapped in a :class:`LoadResult`.

    Usage
    -----
    >>> loader = DataLoader()
    >>> result = loader.load(uploaded_file)
    >>> if result.success:
    ...     df = result.df
    """

    # ── Public interface ──────────────────────────────────────────────────────

    def load(self, uploaded_file) -> LoadResult:
        """
        Entry point — validates and parses *uploaded_file*.

        Parameters
        ----------
        uploaded_file:
            A Streamlit ``UploadedFile`` object (duck-typed; any file-like
            object with ``.name`` and ``.size`` attributes works).

        Returns
        -------
        LoadResult
            Always returns a result; inspect ``.success`` before using ``.df``.
        """
        result = LoadResult(
            filename=uploaded_file.name,
            file_size_bytes=uploaded_file.size,
            extension=self._get_extension(uploaded_file.name),
        )

        # ── Step 1: pre-flight checks ─────────────────────────────────────
        error = self._validate_file_meta(result)
        if error:
            result.error_message = error
            return result

        # ── Step 2: parse ─────────────────────────────────────────────────
        try:
            df = self._parse(uploaded_file, result.extension)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to parse uploaded file '%s'", uploaded_file.name)
            result.error_message = (
                f"Could not parse the file: {exc}. "
                "Please verify the format and try again."
            )
            return result

        # ── Step 3: post-parse validation ─────────────────────────────────
        error = self._validate_dataframe(df, result)
        if error:
            result.error_message = error
            return result

        result.df = df
        result.success = True
        logger.info(
            "Loaded '%s' — %d rows × %d cols (%.1f MB in memory)",
            result.filename,
            result.n_rows,
            result.n_cols,
            result.memory_usage_mb,
        )
        return result

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _get_extension(filename: str) -> str:
        """Return the lower-case file extension including the dot."""
        parts = filename.rsplit(".", 1)
        return f".{parts[-1].lower()}" if len(parts) == 2 else ""

    def _validate_file_meta(self, result: LoadResult) -> str:
        """Return an error string if metadata checks fail, else empty string."""
        if result.extension not in SUPPORTED_EXTENSIONS:
            return (
                f"Unsupported file type '{result.extension}'. "
                f"Accepted formats: {', '.join(SUPPORTED_EXTENSIONS)}."
            )
        size_mb = result.file_size_bytes / (1024 ** 2)
        if size_mb > MAX_FILE_SIZE_MB:
            return (
                f"File is {size_mb:.1f} MB — exceeds the {MAX_FILE_SIZE_MB} MB limit. "
                "Consider splitting the dataset or using a Parquet file for better compression."
            )
        return ""

    def _parse(self, uploaded_file, extension: str) -> pd.DataFrame:
        """Dispatch to the appropriate pandas reader based on *extension*."""
        raw_bytes = uploaded_file.read()
        buffer = io.BytesIO(raw_bytes)

        if extension == ".csv":
            return self._read_csv(buffer)
        if extension == ".tsv":
            return pd.read_csv(buffer, sep="\t", encoding_errors="replace")
        if extension in (".xlsx", ".xls"):
            return pd.read_excel(buffer, engine="openpyxl" if extension == ".xlsx" else "xlrd")
        if extension == ".parquet":
            return pd.read_parquet(buffer)

        raise ValueError(f"No reader registered for extension '{extension}'.")

    @staticmethod
    def _read_csv(buffer: io.BytesIO) -> pd.DataFrame:
        """
        Attempt CSV parsing with automatic delimiter and encoding detection.
        Falls back gracefully on encoding issues.
        """
        # Try UTF-8 first, then latin-1 as a safe fallback
        for encoding in ("utf-8", "latin-1"):
            try:
                buffer.seek(0)
                return pd.read_csv(
                    buffer,
                    encoding=encoding,
                    sep=None,          # let the Python sniffer decide
                    engine="python",
                    on_bad_lines="warn",
                )
            except UnicodeDecodeError:
                continue
        raise ValueError("Unable to decode the CSV file with UTF-8 or Latin-1 encodings.")

    @staticmethod
    def _validate_dataframe(df: pd.DataFrame, result: LoadResult) -> str:
        """Return an error string if the DataFrame is unusable, else empty string."""
        if df.empty:
            return "The uploaded file is empty or contains no parseable data."
        if len(df) > MAX_ROWS:
            return (
                f"Dataset has {len(df):,} rows — exceeds the {MAX_ROWS:,}-row limit. "
                "Please upload a sampled or aggregated version."
            )
        # Warn about low column count (likely parse issue)
        if len(df.columns) == 1:
            result.warnings.append(
                "Only one column was detected. If your file uses a different "
                "delimiter, consider converting it to CSV with comma separators."
            )
        return ""


# ── Streamlit caching wrapper ─────────────────────────────────────────────────


@st.cache_data(show_spinner=False)
def load_dataframe(file_bytes: bytes, filename: str) -> LoadResult:
    """
    Cached entry point for Streamlit pages.

    Wraps :meth:`DataLoader.load` so that re-renders with the same file do
    not trigger re-parsing. The cache key is derived from the raw bytes and
    filename to detect content changes.

    Parameters
    ----------
    file_bytes:
        Raw content of the uploaded file.
    filename:
        Original filename (used for extension detection and display).
    """

    class _FakeUpload:
        """Minimal duck-type for the real Streamlit UploadedFile."""
        def __init__(self, name: str, data: bytes) -> None:
            self.name = name
            self.size = len(data)
            self._data = data

        def read(self) -> bytes:
            return self._data

    return DataLoader().load(_FakeUpload(filename, file_bytes))
