"""gunicorn settings, configured through environment variables.

Usage: ``gunicorn -c python:personal_finance.gunicorn_conf personal_finance.wsgi:server``

Defaults suit a small free-tier instance (about 512 MB RAM, very low traffic).

Environment variables:
    PORT              Port to listen on (set by hosting platforms). Default 8050.
    HOST              Interface to bind. Default 0.0.0.0 (all interfaces, as needed in
                      a container).
    WEB_CONCURRENCY   Worker processes. Default 2.
    GUNICORN_THREADS  Threads per worker. Default 4.
    LOG_LEVEL         gunicorn log level. Default info.
"""

import os


def _int_from_env(name: str, default: int, minimum: int, maximum: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        raise ValueError(f"{name} must be an integer, got {raw!r}") from None
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}, got {value}")
    return value


bind = f"{os.environ.get('HOST', '0.0.0.0')}:{_int_from_env('PORT', 8050, 1, 65535)}"

# Each worker holds its own copy of Dash/Plotly (~80-100 MB). The app is stateless
# (user data lives in the browser, see storage/browser_store.py), so any worker can
# serve any request.
workers = _int_from_env("WEB_CONCURRENCY", 2, 1, 16)
worker_class = "gthread"
threads = _int_from_env("GUNICORN_THREADS", 4, 1, 32)
preload_app = True

timeout = 60
graceful_timeout = 30
keepalive = 5
# Recycle workers now and then to keep memory flat on a small instance.
max_requests = 1000
max_requests_jitter = 100

# The platform's proxy terminates HTTPS and sets X-Forwarded-* headers. The container
# is only reachable through that proxy.
forwarded_allow_ips = "*"

# Logs go to stdout/stderr for the platform's log viewer. Privacy: Dash sends all user
# input in POST bodies, which are never logged; the access log format also leaves out
# client IP addresses and user agents.
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("LOG_LEVEL", "info")
access_log_format = '"%(r)s" %(s)s %(b)s %(M)sms'
