"""Start the dashboard server and open it in the default browser."""

import argparse
import os
import socket
import threading
import time
import webbrowser
from typing import Optional, Sequence

from personal_finance.dashboard.app import app

HOST = "127.0.0.1"
DEFAULT_PORT = 8050


def _wait_for_server(host: str, port: int, timeout: float) -> bool:
    """Return True as soon as ``host:port`` accepts connections, False after ``timeout``."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.2)
    return False


def open_browser_when_ready(host: str, port: int, timeout: float = 15.0) -> bool:
    """Open the dashboard in the default browser once the server is reachable."""
    if not _wait_for_server(host, port, timeout):
        return False
    webbrowser.open_new_tab(f"http://{host}:{port}/")
    return True


def _is_reloader_child() -> bool:
    # With debug=True, Werkzeug re-runs the app in a child process (and again on every
    # code change). Only the original process should open the browser.
    return os.environ.get("WERKZEUG_RUN_MAIN") == "true"


def run_dashboard(
    debug: bool = False, port: int = DEFAULT_PORT, open_browser: bool = True
) -> None:
    """Run the dashboard on localhost and, by default, open it in the browser."""
    if open_browser and not _is_reloader_child():
        threading.Thread(
            target=open_browser_when_ready, args=(HOST, port), daemon=True
        ).start()
    app.run(debug=debug, port=port, host=HOST)


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="swiss-finance-dashboard",
        description="Startet das Finanzplan-Dashboard.",
    )
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Port (Standard: 8050)")
    parser.add_argument(
        "--no-browser", action="store_true", help="Browser nicht automatisch öffnen"
    )
    parser.add_argument(
        "--debug", action="store_true", help="Debug-Modus mit Auto-Reload bei Codeänderungen"
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> None:
    """Console entry point: ``swiss-finance-dashboard [--port N] [--no-browser] [--debug]``."""
    args = parse_args(argv)
    run_dashboard(debug=args.debug, port=args.port, open_browser=not args.no_browser)
