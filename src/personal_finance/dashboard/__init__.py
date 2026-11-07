"""Interactive Dash dashboard.

Importing this package builds the layout and registers all callbacks on ``app``.
"""

from personal_finance.dashboard.app import app
from personal_finance.dashboard.layout import layout
from personal_finance.dashboard import callbacks  # noqa: F401  (registers callbacks)
from personal_finance.dashboard.launch import main, run_dashboard

app.layout = layout

__all__ = ["app", "main", "run_dashboard"]
