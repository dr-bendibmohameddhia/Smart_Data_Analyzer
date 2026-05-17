# src/pages/__init__.py
# Makes 'pages' a proper package and exposes each page renderer.

from .home import render as render_home
from .analyze_data import render as render_analyze
from .about import render as render_about

__all__ = ["render_home", "render_analyze", "render_about"]
