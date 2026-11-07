"""Issue #5: production WSGI entry point, health endpoint and gunicorn settings."""

import importlib
import socket
import subprocess
import sys
import time
import urllib.request

import pytest
from flask import Flask

import personal_finance.gunicorn_conf as gunicorn_conf
from personal_finance.wsgi import server

GUNICORN_ENV_VARS = ("PORT", "HOST", "WEB_CONCURRENCY", "GUNICORN_THREADS", "LOG_LEVEL")


# --- health endpoint ---------------------------------------------------------------


def test_health_endpoint_reports_ok_without_details():
    response = server.test_client().get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}
    assert response.headers["Cache-Control"] == "no-store"


# --- WSGI entry point --------------------------------------------------------------


def test_wsgi_server_is_the_fully_wired_dashboard():
    client = server.test_client()

    assert isinstance(server, Flask)
    assert client.get("/").status_code == 200
    assert client.get("/_dash-layout").status_code == 200
    assert client.get("/_dash-dependencies").get_json()  # callbacks are registered


def test_wsgi_server_never_runs_in_debug_mode():
    assert server.debug is False


# --- gunicorn configuration --------------------------------------------------------


@pytest.fixture
def load_conf(monkeypatch):
    """Reload gunicorn_conf with a given environment."""

    def _load(**env):
        for name in GUNICORN_ENV_VARS:
            monkeypatch.delenv(name, raising=False)
        for name, value in env.items():
            monkeypatch.setenv(name, value)
        return importlib.reload(gunicorn_conf)

    yield _load
    for name in GUNICORN_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    importlib.reload(gunicorn_conf)


def test_gunicorn_defaults_fit_a_small_instance(load_conf):
    conf = load_conf()

    assert conf.bind == "0.0.0.0:8050"
    assert (conf.workers, conf.threads, conf.worker_class) == (2, 4, "gthread")
    assert conf.preload_app is True


def test_gunicorn_uses_platform_port_and_overrides(load_conf):
    conf = load_conf(PORT="10000", HOST="127.0.0.1", WEB_CONCURRENCY="1", GUNICORN_THREADS="8")

    assert conf.bind == "127.0.0.1:10000"
    assert (conf.workers, conf.threads) == (1, 8)


@pytest.mark.parametrize(
    ("name", "value"),
    [("PORT", "abc"), ("PORT", "0"), ("PORT", "70000"), ("WEB_CONCURRENCY", "0")],
)
def test_gunicorn_rejects_invalid_settings(load_conf, name, value):
    with pytest.raises(ValueError, match=name):
        load_conf(**{name: value})


def test_access_log_contains_no_client_ip_or_user_agent(load_conf):
    conf = load_conf()

    assert "%(h)s" not in conf.access_log_format
    assert "%(a)s" not in conf.access_log_format
    assert "%({x-forwarded-for}i)s" not in conf.access_log_format


# --- real gunicorn run (Linux only: CI and Docker) ---------------------------------


def _free_port():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


@pytest.mark.skipif(sys.platform == "win32", reason="gunicorn runs on Linux/macOS only")
def test_gunicorn_serves_dashboard_and_health(tmp_path):
    port = _free_port()
    process = subprocess.Popen(
        [
            sys.executable, "-m", "gunicorn",
            "-c", "python:personal_finance.gunicorn_conf",
            "personal_finance.wsgi:server",
        ],
        env={"PATH": "", "PORT": str(port), "HOST": "127.0.0.1", "WEB_CONCURRENCY": "1"},
        cwd=tmp_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    try:
        base = f"http://127.0.0.1:{port}"
        for _ in range(60):
            try:
                with urllib.request.urlopen(f"{base}/health", timeout=1) as response:
                    assert response.status == 200
                    break
            except OSError:
                if process.poll() is not None:
                    pytest.fail(process.stdout.read().decode())
                time.sleep(0.5)
        else:
            pytest.fail("gunicorn did not become healthy")

        with urllib.request.urlopen(f"{base}/", timeout=5) as response:
            assert response.status == 200
            assert b"Finanzplan" in response.read()
    finally:
        process.terminate()
        process.wait(timeout=10)
