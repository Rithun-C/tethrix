# Backend image. Three results come out of this file:
#   dev      what Docker Compose runs on the laptop: all packages, hot reload
#   runtime  what ships to Lambda in B3: runtime packages and our code, nothing else
#   (base and deps are steps on the way)
#
# Build one of them: docker build --target runtime app/backend
#
# Images are pinned by digest (SR-80). Dependabot updates the lines below.

# uv, the Python package manager. Only its one binary is copied out of this image.
FROM ghcr.io/astral-sh/uv:0.13.7@sha256:96f40d3904aad8d0bd010539001d36c8e2188b981e1334471a90c4a1d93bb490 AS uv

# Official Python image, slim variant: Debian with Python and little else.
FROM python:3.15.0-slim-trixie@sha256:f5b92f2a669a4c347044f29367f31983280b648250ca94dea66f98c53bc87e58 AS python-base

# PYTHONDONTWRITEBYTECODE: no .pyc files; the file system is read-only when running.
# PYTHONUNBUFFERED: log lines appear at once instead of waiting in a buffer.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    PATH=/opt/venv/bin:$PATH

WORKDIR /app

# A fixed, non-root user. If the app is broken into, the attacker is not root inside
# the container. A fixed number (not only a name) lets Kubernetes check it is not 0.
RUN groupadd --gid 10001 app \
    && useradd --uid 10001 --gid 10001 --no-create-home --home-dir /tmp --shell /usr/sbin/nologin app

# Docker, Compose and Kubernetes use this to know the app answers. Lambda ignores it.
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/api/v1/health', timeout=2)"]

# ---- base: Python plus uv --------------------------------------------------
FROM python-base AS base

COPY --from=uv /uv /usr/local/bin/uv

# UV_PROJECT_ENVIRONMENT: packages go to /opt/venv, outside /app, so mounting the source
#   folder over /app on the laptop does not hide them.
# UV_PYTHON_DOWNLOADS=never: use the image's Python; never download another one.
# UV_LINK_MODE=copy: copy files out of the download cache instead of linking to them;
#   the cache is not part of the image (see the RUN lines below).
# UV_CONCURRENT_DOWNLOADS: fewer downloads at once; kinder to a poor connection.
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_DOWNLOADS=never \
    UV_LINK_MODE=copy \
    UV_CONCURRENT_DOWNLOADS=4

# ---- deps: the runtime packages, exactly as locked ---------------------------
FROM base AS deps

COPY pyproject.toml uv.lock ./

# --locked: fail if uv.lock does not match pyproject.toml, instead of quietly changing it.
# --no-dev: leave out pytest, ruff and the other development tools.
# --mount=type=cache: uv's download cache is kept by Docker between builds but is not
#   stored in the image. A build that is interrupted (for example by a bad connection)
#   continues where it stopped instead of downloading everything again.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

# ---- dev: for Docker Compose --------------------------------------------------
FROM deps AS dev

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked

# The source is not copied in. Compose mounts it from the laptop, so edits show at once.
USER 10001:10001
EXPOSE 8080
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8080", "--no-access-log", "--reload", "--reload-dir", "/app/src"]

# ---- runtime: what ships ------------------------------------------------------
# Starts again from the clean Python image: no uv, no lockfile, no development tools.
FROM python-base AS runtime

COPY --from=deps /opt/venv /opt/venv
COPY src ./src

USER 10001:10001
# 8080 is the port the Lambda Web Adapter expects (added in B3).
EXPOSE 8080
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8080", "--no-access-log"]
