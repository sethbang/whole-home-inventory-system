"""ARQ worker boot configuration.

Run with ``arq app.jobs.worker.WorkerSettings`` (or via the
``whis-worker`` compose service which uses the same command).

Tasks are imported from :mod:`app.jobs.tasks` and registered in the
``functions`` tuple below. The Part C scaffold ships with an empty
registry; Parts D and E append real tasks.

Worker-side database access goes through a plain ``SessionLocal`` —
the worker doesn't use FastAPI's dependency-injection so we open/close
sessions explicitly inside each task.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from .client import _redis_settings_from_url
from ..logging_config import setup_logging
from ..settings import settings

logger = logging.getLogger(__name__)


async def _on_startup(ctx: Dict[str, Any]) -> None:
    """ARQ worker hook — runs once per worker process at boot."""
    setup_logging()
    logger.info("whis worker booting (redis=%s)", settings.REDIS_URL or "<unset>")


async def _on_shutdown(ctx: Dict[str, Any]) -> None:
    logger.info("whis worker shutting down")


def _redis_settings_or_default():
    """ARQ requires a ``RedisSettings`` even during import-time inspection.

    In normal operation ``REDIS_URL`` is set before the worker boots.
    When it isn't (e.g. test collection) we return a default pointing
    at localhost so the attribute lookup succeeds; the worker won't
    actually run without a real Redis connection.
    """
    if settings.REDIS_URL:
        return _redis_settings_from_url(settings.REDIS_URL)
    # Bare-minimum placeholder; never actually dialed since no pool.
    from arq.connections import RedisSettings

    return RedisSettings(host="localhost", port=6379)


class WorkerSettings:
    """ARQ WorkerSettings — discovered by the ``arq`` CLI."""

    # Filled in by Parts D + E. Keeping it as a list (not a tuple) so
    # later modules can append without rewriting this file.
    functions: list = []

    on_startup = _on_startup
    on_shutdown = _on_shutdown

    # Default per-task limits. 5 minutes is generous for the heaviest
    # task we plan to run in v3.0 (backup restore at ~45s) and still
    # well under ARQ's default job-retry-after window.
    job_timeout = 300

    # Keep finished-job state around long enough for the frontend to
    # poll for the result after dispatch. 1 hour is plenty.
    keep_result = 3600

    # Populated lazily by the ``arq`` CLI via this class-level property;
    # it calls ``WorkerSettings.redis_settings`` before binding.
    redis_settings = _redis_settings_or_default()
