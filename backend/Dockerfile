# syntax=docker/dockerfile:1.6
# ---------------------------------------------------------------------------
# Stage 1 — build the virtualenv with pinned deps.
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /build
COPY requirements.txt .
RUN pip install -r requirements.txt

# ---------------------------------------------------------------------------
# Stage 2 — runtime. Non-root, minimal deps, healthcheck.
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# curl is needed by HEALTHCHECK; everything else is in the venv.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Non-root runtime user. The compose file mounts uploads / backups / certs
# volumes which must be writable by uid 1000.
RUN groupadd --system --gid 1000 whis \
    && useradd --system --uid 1000 --gid 1000 --create-home whis

COPY --from=builder /opt/venv /opt/venv
WORKDIR /app
COPY --chown=whis:whis . .

USER whis

EXPOSE 27182

# Certs now come from a mounted volume (written by the frontend
# generate-certs.js flow in dev, or Caddy's ACME storage in prod).
# bootstrap.py checks they exist before handing off to uvicorn.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -kfsS https://localhost:27182/api/health || exit 1

CMD ["sh", "-c", "python scripts/bootstrap.py && exec uvicorn app.main:app --host 0.0.0.0 --port 27182 --ssl-keyfile certs/key.pem --ssl-certfile certs/cert.pem"]
