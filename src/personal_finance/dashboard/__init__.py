"""Interactive Dash dashboard.

Importing this package builds the layout and registers all callbacks on ``app``.
"""

from personal_finance.dashboard.app import app
from personal_finance.dashboard.layout import layout
from personal_finance.dashboard import callbacks  # noqa: F401  (registers callbacks)

app.layout = layout


def run_dashboard(debug: bool = False, port: int = 8050) -> None:
    """Run the dashboard on localhost."""
    app.run(debug=debug, port=port, host="127.0.0.1")


__all__ = ["app", "run_dashboard"]
