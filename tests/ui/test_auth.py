"""Issue #10: shared-password protection (HTTP Basic Auth)."""

import base64
import subprocess
import sys

import pytest
from flask import Flask

from personal_finance.dashboard import auth

PASSWORD = "richtig-langes-passwort"


def basic(username, password):
    token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
    return {"Authorization": f"Basic {token}"}


@pytest.fixture
def client():
    """A small Flask app with the same kinds of routes as the dashboard."""
    server = Flask(__name__)

    @server.get("/")
    def index():
        return "Dashboard"

    @server.post("/_dash-update-component")
    def dash_update():
        return {"ok": True}

    @server.get("/health")
    def health():
        return {"status": "ok"}

    auth.install_privacy_headers(server)
    auth.install_basic_auth(server, "kamerad", PASSWORD)
    return server.test_client()


# --- access control ------------------------------------------------------------------


def test_without_login_everything_is_locked(client):
    for response in (client.get("/"), client.post("/_dash-update-component")):
        assert response.status_code == 401
        assert response.headers["WWW-Authenticate"].startswith('Basic realm="Finanzplan"')
        assert b"Dashboard" not in response.data


def test_correct_login_opens_page_and_callbacks(client):
    assert client.get("/", headers=basic("kamerad", PASSWORD)).status_code == 200
    response = client.post("/_dash-update-component", headers=basic("kamerad", PASSWORD))
    assert response.status_code == 200


@pytest.mark.parametrize(
    ("username", "password"),
    [
        ("kamerad", "falsch"),
        ("kamerad", PASSWORD + "x"),
        ("kamerad", PASSWORD[:-1]),
        ("fremder", PASSWORD),
        ("", ""),
        ("KAMERAD", PASSWORD),
    ],
)
def test_wrong_credentials_are_rejected(client, username, password):
    assert client.get("/", headers=basic(username, password)).status_code == 401


@pytest.mark.parametrize(
    "header",
    ["Bearer abc", "Basic", "Basic !!!kein-base64!!!", "Basic " + base64.b64encode(b"ohne-doppelpunkt").decode()],
)
def test_malformed_headers_are_rejected(client, header):
    assert client.get("/", headers={"Authorization": header}).status_code == 401


def test_health_and_robots_stay_public(client):
    assert client.get("/health").status_code == 200
    robots = client.get("/robots.txt")
    assert robots.status_code == 200
    assert "Disallow: /" in robots.get_data(as_text=True)


def test_all_responses_ask_search_engines_not_to_index(client):
    for response in (client.get("/health"), client.get("/"), client.get("/", headers=basic("kamerad", PASSWORD))):
        assert response.headers["X-Robots-Tag"] == "noindex, nofollow"


def test_password_with_umlauts_and_colon_works():
    server = Flask(__name__)
    server.get("/")(lambda: "ok")
    auth.install_basic_auth(server, "kamerad", "Grüezi:mitenand-2026")
    client = server.test_client()

    assert client.get("/", headers=basic("kamerad", "Grüezi:mitenand-2026")).status_code == 200


# --- configuration from environment --------------------------------------------------


def test_auth_is_off_without_password():
    assert auth.credentials_from_env({}) is None


def test_default_username():
    assert auth.credentials_from_env({"APP_PASSWORD": PASSWORD}) == ("kamerad", PASSWORD)


def test_custom_username():
    env = {"APP_PASSWORD": PASSWORD, "APP_USERNAME": " team "}
    assert auth.credentials_from_env(env) == ("team", PASSWORD)


@pytest.mark.parametrize("required", ["1", "true", "YES"])
def test_required_auth_without_password_refuses_to_start(required):
    with pytest.raises(auth.AuthConfigError, match="refusing to start"):
        auth.credentials_from_env({"REQUIRE_AUTH": required})


def test_too_short_password_is_rejected():
    with pytest.raises(auth.AuthConfigError, match="12"):
        auth.credentials_from_env({"APP_PASSWORD": "kurz"})


def test_username_with_colon_is_rejected():
    with pytest.raises(auth.AuthConfigError, match=":"):
        auth.credentials_from_env({"APP_PASSWORD": PASSWORD, "APP_USERNAME": "a:b"})


# --- the real app, wired through environment variables ------------------------------

_PROBE = """
import base64, sys
from personal_finance.wsgi import server
client = server.test_client()
token = base64.b64encode(b"kamerad:%s").decode()
print(client.get("/").status_code,
      client.get("/", headers={"Authorization": "Basic " + token}).status_code,
      client.get("/health").status_code)
"""


def _run_app(env):
    import os

    full_env = {k: v for k, v in os.environ.items() if k not in {"APP_PASSWORD", "REQUIRE_AUTH"}}
    full_env.update(env)
    return subprocess.run(
        [sys.executable, "-c", _PROBE % PASSWORD.encode().decode()],
        env=full_env,
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_real_app_requires_login_when_password_is_set():
    result = _run_app({"APP_PASSWORD": PASSWORD, "REQUIRE_AUTH": "1"})

    assert result.returncode == 0, result.stderr
    assert result.stdout.split() == ["401", "200", "200"]


def test_real_app_is_open_locally_without_password():
    result = _run_app({})

    assert result.returncode == 0, result.stderr
    assert result.stdout.split() == ["200", "200", "200"]


def test_real_app_refuses_to_start_when_required_but_no_password():
    result = _run_app({"REQUIRE_AUTH": "1"})

    assert result.returncode != 0
    assert "refusing to start" in result.stderr
