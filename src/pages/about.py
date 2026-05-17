"""
src/pages/about.py
───────────────────
About page — project overview, tech stack, and contribution guidelines.
"""

from __future__ import annotations

import streamlit as st


def render() -> None:
    st.markdown("## About Smart Data Analyzer")

    st.markdown(
        """
        Smart Data Analyzer was built to bridge the gap between raw data and
        actionable insight for teams that don't have a dedicated data scientist
        on hand.  The goal was a tool that feels as fast as a spreadsheet but
        as thorough as a Python notebook — without requiring either.
        """
    )

    st.markdown("---")

    # ── Tech stack ────────────────────────────────────────────────────────────
    st.markdown("### Tech stack")
    cols = st.columns(3)

    _tech_card(cols[0], [
        ("🐍 Python 3.11+", "Core language"),
        ("⚡ Streamlit 1.35", "UI framework"),
        ("🐼 pandas 2.2", "Data manipulation"),
        ("🔢 NumPy 1.26", "Numerical operations"),
    ])
    _tech_card(cols[1], [
        ("📊 Plotly 5.22", "Interactive charts"),
        ("📐 SciPy 1.13", "Statistical functions"),
        ("🤖 scikit-learn 1.5", "ML utilities"),
        ("📦 pyarrow 16", "Parquet I/O"),
    ])
    _tech_card(cols[2], [
        ("📋 openpyxl 3.1", "Excel read/write"),
        ("🔍 python-dotenv", "Environment config"),
        ("🐕 watchdog 4.0", "Dev file-watching"),
        ("🧪 pytest (dev)", "Unit testing"),
    ])

    st.markdown("---")

    # ── Architecture notes ────────────────────────────────────────────────────
    st.markdown("### Architecture")
    st.markdown(
        """
        The project follows a layered architecture:

        | Layer | Location | Responsibility |
        |---|---|---|
        | **UI / Pages** | `src/pages/` | Streamlit rendering, user input, session state |
        | **Components** | `src/components/` | Pure logic — loading, processing, visualisation |
        | **Entry point** | `src/main.py` | Navigation, global config, page dispatch |

        Components are intentionally kept free of Streamlit imports so they
        can be unit-tested without launching a server, and potentially reused
        in a FastAPI backend or Jupyter notebook context.
        """
    )

    st.markdown("---")

    # ── Roadmap ───────────────────────────────────────────────────────────────
    st.markdown("### Roadmap")
    st.markdown(
        """
        Planned improvements for upcoming releases:

        - **AI-powered narrative** — auto-generated plain-English summary of
          the most interesting patterns in a dataset.
        - **Geospatial support** — detect lat/lng columns and render a
          Mapbox choropleth.
        - **Export to PDF report** — one-click professional summary with
          embedded charts.
        - **Database connectors** — direct query from PostgreSQL / BigQuery
          without CSV export.
        - **Scheduled refreshes** — periodically reload a dataset from a URL
          and push a Slack/email digest.
        - **Column-level lineage** — track cleaning operations and generate a
          reproducible pandas script.
        """
    )

    st.markdown("---")

    # ── Contributing ──────────────────────────────────────────────────────────
    st.markdown("### Contributing")
    st.markdown(
        """
        Contributions are welcome.  Please follow the standard fork → branch →
        pull-request workflow.  Before opening a PR:

        1. Run `pytest` and confirm all tests pass.
        2. Format code with `black` and lint with `ruff`.
        3. Keep commits atomic and write a descriptive commit message.

        For large features, open an issue first to align on scope.
        """
    )

    st.markdown("---")

    # ── Footer ────────────────────────────────────────────────────────────────
    st.markdown(
        """
        <div style="text-align: center; color: #8C9AB7; font-size: 0.82rem; padding-top: 1rem;">
            Smart Data Analyzer · MIT License · Built with Streamlit
        </div>
        """,
        unsafe_allow_html=True,
    )


def _tech_card(col, items: list[tuple[str, str]]) -> None:
    with col:
        md = "\n".join(f"- **{name}** — {desc}" for name, desc in items)
        st.markdown(md)
