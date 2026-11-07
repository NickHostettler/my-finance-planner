"""WSGI entry point for production servers.

    gunicorn -c python:personal_finance.gunicorn_conf personal_finance.wsgi:server

Importing the dashboard package builds the layout and registers all callbacks; ``server``
is the underlying Flask app. Debug mode is never enabled here.
"""

from personal_finance.dashboard import app

server = app.server

__all__ = ["server"]
