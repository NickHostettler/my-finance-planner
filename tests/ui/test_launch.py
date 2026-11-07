"""Tests for starting the dashboard and auto-opening the browser."""

import socket
import threading

import pytest

from personal_finance.dashboard import launch


@pytest.fixture
def opened(monkeypatch):
    urls = []
    monkeypatch.setattr(launch.webbrowser, "open_new_tab", urls.append)
    return urls


@pytest.fixture
def fake_server(monkeypatch):
    """Replace app.run so no real server starts; record the call."""
    calls = []
    monkeypatch.setattr(launch.app, "run", lambda **kwargs: calls.append(kwargs))
    return calls


@pytest.fixture
def started_threads(monkeypatch):
    targets = []

    class RecordingThread:
        def __init__(self, target, args=(), daemon=None):
            targets.append((target, args))

        def start(self):
            pass

    monkeypatch.setattr(launch.threading, "Thread", RecordingThread)
    return targets


def test_browser_opens_once_server_accepts_connections(opened):
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        port = listener.getsockname()[1]

        assert launch.open_browser_when_ready("127.0.0.1", port, timeout=2) is True

    assert opened == [f"http://127.0.0.1:{port}/"]


def test_browser_is_not_opened_when_server_never_starts(opened):
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        free_port = probe.getsockname()[1]

    assert launch.open_browser_when_ready("127.0.0.1", free_port, timeout=0.3) is False
    assert opened == []


def test_browser_waits_for_a_server_that_starts_late(opened):
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    port = listener.getsockname()[1]
    threading.Timer(0.4, listener.listen).start()
    try:
        assert launch.open_browser_when_ready("127.0.0.1", port, timeout=3) is True
    finally:
        listener.close()

    assert len(opened) == 1


def test_run_dashboard_starts_browser_thread_by_default(fake_server, started_threads, monkeypatch):
    monkeypatch.delenv("WERKZEUG_RUN_MAIN", raising=False)

    launch.run_dashboard(port=8123)

    assert started_threads == [(launch.open_browser_when_ready, ("127.0.0.1", 8123))]
    assert fake_server == [{"debug": False, "port": 8123, "host": "127.0.0.1"}]


def test_reloader_child_does_not_open_another_tab(fake_server, started_threads, monkeypatch):
    monkeypatch.setenv("WERKZEUG_RUN_MAIN", "true")

    launch.run_dashboard(debug=True)

    assert started_threads == []
    assert len(fake_server) == 1


def test_no_browser_flag_disables_opening(fake_server, started_threads, monkeypatch):
    monkeypatch.delenv("WERKZEUG_RUN_MAIN", raising=False)

    launch.main(["--no-browser", "--port", "9000"])

    assert started_threads == []
    assert fake_server == [{"debug": False, "port": 9000, "host": "127.0.0.1"}]


def test_cli_defaults():
    args = launch.parse_args([])

    assert (args.port, args.no_browser, args.debug) == (8050, False, False)
