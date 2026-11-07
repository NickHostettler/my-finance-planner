# syntax=docker/dockerfile:1
#
# Production image: gunicorn serving the Dash app on $PORT (default 8050).
#   docker build -t my-finance-planner .
#   docker run --rm -p 8050:8050 my-finance-planner
#
# Python version matches .python-version; dependencies come from uv.lock.

ARG PYTHON_IMAGE=python:3.14-slim-trixie
ARG UV_VERSION=0.13.1

# --- uv binary ----------------------------------------------------------------------
FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

# --- build stage: install the app into /app/.venv -----------------------------------
FROM ${PYTHON_IMAGE} AS builder

COPY --from=uv /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv

WORKDIR /src

# 1) Dependencies only (cached until pyproject.toml/uv.lock change).
COPY pyproject.toml uv.lock .python-version README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-install-project

# 2) The app itself, installed non-editable so the runtime image needs no source tree.
COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-editable

# --- runtime stage ------------------------------------------------------------------
FROM ${PYTHON_IMAGE} AS runtime

# Unprivileged user; the app never needs to write anywhere (user data lives in the
# browser, see storage/browser_store.py), so the container can run read-only.
RUN groupadd --system --gid 10001 app \
 && useradd --system --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app

COPY --from=builder --chown=root:root /app/.venv /app/.venv

ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8050

USER app
WORKDIR /app
EXPOSE 8050

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD ["python", "-c", "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/health' % os.environ.get('PORT', '8050'), timeout=4)"]

CMD ["gunicorn", "-c", "python:personal_finance.gunicorn_conf", "personal_finance.wsgi:server"]
