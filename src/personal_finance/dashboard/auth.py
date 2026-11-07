"""Shared-password protection (HTTP Basic Auth) for the deployed dashboard.

Configured through environment variables:

    APP_PASSWORD   Enables the login when set (at least 12 characters).
    APP_USERNAME   Login name. Default ``kamerad``.
    REQUIRE_AUTH   ``1`` = refuse to start without APP_PASSWORD (set in the Docker image,
                   so a deployment can never go online unprotected by accident).

The password only keeps strangers out; it does not separate users from each other.
That separation comes from storing user data in each browser (storage/browser_store.py).
"""

import base64
import binascii
import hmac
import os
from typing import Iterable, Mapping, Optional, Tuple

from flask import Flask, Response, request

DEFAULT_USERNAME = "kamerad"
MIN_PASSWORD_LENGTH = 12
PUBLIC_PATHS = frozenset({"/health", "/robots.txt"})
REALM = "Finanzplan"


class AuthConfigError(RuntimeError):
    """Raised at startup when the auth settings are missing or too weak."""


def credentials_from_env(environ: Mapping[str, str]) -> Optional[Tuple[str, str]]:
    """Return ``(username, password)``, ``None`` if auth is off, or raise on bad config."""
    password = environ.get("APP_PASSWORD", "")
    required = environ.get("REQUIRE_AUTH", "").strip().lower() in {"1", "true", "yes"}
    if not password:
        if required:
            raise AuthConfigError(
                "REQUIRE_AUTH is set but APP_PASSWORD is empty: refusing to start "
                "without password protection."
            )
        return None
    if len(password) < MIN_PASSWORD_LENGTH:
        raise AuthConfigError(
            f"APP_PASSWORD must be at least {MIN_PASSWORD_LENGTH} characters long."
        )
    username = environ.get("APP_USERNAME", "").strip() or DEFAULT_USERNAME
    if ":" in username:
        raise AuthConfigError("APP_USERNAME must not contain ':'.")
    return username, password


def _parse_basic_auth(header: str) -> Optional[Tuple[str, str]]:
    scheme, _, encoded = header.partition(" ")
    if scheme.lower() != "basic" or not encoded:
        return None
    try:
        decoded = base64.b64decode(encoded.strip(), validate=True).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError):
        return None
    username, separator, password = decoded.partition(":")
    return (username, password) if separator else None


def _matches(given: str, expected: str) -> bool:
    return hmac.compare_digest(given.encode("utf-8"), expected.encode("utf-8"))


def _unauthorized() -> Response:
    return Response(
        "Anmeldung erforderlich.\n",
        status=401,
        mimetype="text/plain",
        headers={
            "WWW-Authenticate": f'Basic realm="{REALM}", charset="UTF-8"',
            "Cache-Control": "no-store",
        },
    )


def install_basic_auth(
    server: Flask,
    username: str,
    password: str,
    public_paths: Iterable[str] = PUBLIC_PATHS,
) -> None:
    """Require the shared login for every request except ``public_paths``."""
    public = frozenset(public_paths)

    @server.before_request
    def _require_login():
        if request.path in public:
            return None
        given = _parse_basic_auth(request.headers.get("Authorization", ""))
        # Compare both parts every time (no early exit) to avoid timing hints.
        user_ok = _matches(given[0], username) if given else _matches("", username)
        password_ok = _matches(given[1], password) if given else _matches("", password)
        if given and user_ok and password_ok:
            return None
        return _unauthorized()


def install_privacy_headers(server: Flask) -> None:
    """Public routes and headers that keep the app out of search engines."""

    @server.get("/robots.txt")
    def _robots():
        return Response("User-agent: *\nDisallow: /\n", mimetype="text/plain")

    @server.after_request
    def _no_index(response: Response) -> Response:
        response.headers.setdefault("X-Robots-Tag", "noindex, nofollow")
        return response


def configure_from_env(server: Flask, environ: Optional[Mapping[str, str]] = None) -> bool:
    """Install auth if configured. Returns whether the login is active."""
    install_privacy_headers(server)
    credentials = credentials_from_env(os.environ if environ is None else environ)
    if credentials is None:
        return False
    install_basic_auth(server, *credentials)
    return True
