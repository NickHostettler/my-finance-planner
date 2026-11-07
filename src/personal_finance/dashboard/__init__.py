"""Interactive Dash dashboard.

Importing this package builds the layout and registers all callbacks on ``app``.
"""

from personal_finance.dashboard.app import app
from personal_finance.dashboard.layout import layout
from personal_finance.dashboard import auth
from personal_finance.dashboard import callbacks  # noqa: F401  (registers callbacks)
from personal_finance.dashboard.launch import main, run_dashboard

app.layout = layout
# Shared-password login when APP_PASSWORD is set (see dashboard/auth.py).
auth.configure_from_env(app.server)

__all__ = ["app", "main", "run_dashboard"]
