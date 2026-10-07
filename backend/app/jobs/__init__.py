"""ARQ job queue scaffolding (v3.0).

Public entry points:

* :func:`get_arq_pool` — lazily creates (or returns the cached) ARQ
  Redis pool. Returns ``None`` when ``settings.REDIS_URL`` is unset so
  the app degrades gracefully to synchronous fallback paths.
* :class:`WorkerSettings` — the ARQ worker config. Boot with
  ``arq app.jobs.worker.WorkerSettings``.

Task functions themselves live under :mod:`app.jobs.tasks` and are
registered in :mod:`app.jobs.worker`. Parts D (backup create/restore)
and E (thumbnail generation) land the first real tasks.
"""

from .client import get_arq_pool

__all__ = ["get_arq_pool"]
