"""ARQ Redis pool creation + caching.

The FastAPI lifespan in :mod:`app.main` calls :func:`get_arq_pool` once
at startup and stores the result on ``app.state.arq``. When
``REDIS_URL`` is unset the function returns ``None``, and every
enqueuer in the service layer is expected to notice and fall back to
its synchronous path. This lets the default ``docker compose up`` (no
Redis, no worker) keep working exactly as it did pre-v3.0.
"""

from __future__ import annotations

import logging
from typing import Optional
from urllib.parse import urlparse

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from ..settings import settings

logger = logging.getLogger(__name__)


def _redis_settings_from_url(url: str) -> RedisSettings:
    """Parse a redis://... URL into an ARQ ``RedisSettings`` struct.

    ARQ doesn't accept a URL string directly — it wants the individual
    host/port/db/password fields. ``urlparse`` is good enough for the
    redis URLs we expect (no unusual encoding on passwords in our
    deploy targets).
    """
    parsed = urlparse(url)
    if parsed.scheme not in {"redis", "rediss"}:
        raise ValueError(
            f"REDIS_URL must use the 'redis://' or 'rediss://' scheme; got {parsed.scheme!r}"
        )
    db_path = (parsed.path or "/0").lstrip("/")
    try:
        database = int(db_path) if db_path else 0
    except ValueError as exc:
        raise ValueError(
            f"REDIS_URL path must be an integer database index; got {db_path!r}"
        ) from exc

    return RedisSettings(
        host=parsed.hostname or "localhost",
        port=parsed.port or 6379,
        database=database,
        password=parsed.password,
        ssl=parsed.scheme == "rediss",
    )


async def get_arq_pool() -> Optional[ArqRedis]:
    """Return a pooled ARQ Redis client, or ``None`` when unconfigured.

    Callers in the service layer check the return value to decide
    between enqueueing a job and running the operation synchronously
    in-request. The pool is cheap to create once per process; the
    FastAPI lifespan caches it on ``app.state.arq``.
    """
    if not settings.REDIS_URL:
        return None
    try:
        return await create_pool(_redis_settings_from_url(settings.REDIS_URL))
    except Exception:
        # Log but don't crash the app — without a pool, enqueuers fall
        # back to synchronous execution. The operator gets a warning;
        # the request path still works.
        logger.exception(
            "failed to create ARQ Redis pool at %s — synchronous fallback active",
            settings.REDIS_URL,
        )
        return None
