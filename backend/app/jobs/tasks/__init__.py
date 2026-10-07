"""ARQ task functions.

Parts D (backup create/restore) and E (thumbnail generation) populate
this subpackage. Each module exports a coroutine with the ARQ calling
convention ``async def task(ctx, ...)`` and is imported + registered
in :mod:`app.jobs.worker`.
"""
