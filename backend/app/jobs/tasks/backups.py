"""ARQ tasks for backup create + restore (v3.0 Part D).

Each task opens its own SQLAlchemy session (the FastAPI dependency
injection layer isn't available inside the worker process) and runs
the existing ``BackupService`` methods. The task return value becomes
the ``result`` field on the job detail endpoint.

Tasks take ``user_id`` as a kwarg so the ``jobs`` router's ownership
guard can verify who owns each job.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import HTTPException
from sqlalchemy import select

from ... import models
from ...database import SessionLocal
from ...services.backups import BackupService

logger = logging.getLogger(__name__)


def _open_service(user_id: str) -> tuple[BackupService, Any]:
    """Open a new session + resolve the user into a BackupService.

    Returns ``(service, session)`` — the caller must close the session
    (in a ``finally``) so the connection returns to the pool.
    """
    db = SessionLocal()
    user = db.execute(
        select(models.User).where(models.User.id == user_id)
    ).scalar_one_or_none()
    if user is None:
        db.close()
        raise RuntimeError(f"user {user_id!r} not found when rehydrating task")
    return BackupService(db=db, user=user), db


async def backup_create(ctx: Dict[str, Any], *, user_id: str) -> Dict[str, Any]:
    """Run the blocking backup pipeline inside the worker."""
    logger.info("backup_create task start (user=%s)", user_id)
    service, db = _open_service(user_id)
    try:
        try:
            backup = service.create()
        except HTTPException as exc:
            # Starlette HTTPException doesn't pickle through ARQ — convert
            # to a serializable error dict the jobs router can surface.
            return {
                "ok": False,
                "error": str(exc.detail),
                "status_code": exc.status_code,
            }
        return {
            "backup_id": str(backup.id),
            "filename": backup.filename,
            "size_bytes": backup.size_bytes,
            "item_count": backup.item_count,
            "image_count": backup.image_count,
            "status": backup.status,
        }
    finally:
        db.close()


async def backup_restore(
    ctx: Dict[str, Any],
    *,
    user_id: str,
    backup_id: str,
    confirm_item_count: Optional[int],
) -> Dict[str, Any]:
    """Run the blocking restore pipeline inside the worker."""
    logger.info(
        "backup_restore task start (user=%s backup=%s)", user_id, backup_id
    )
    service, db = _open_service(user_id)
    try:
        try:
            # commit_restore returns a dict shaped like RestoreResponse —
            # already JSON-serializable for ARQ to stash on the job row.
            return service.commit_restore(backup_id, confirm_item_count)
        except HTTPException as exc:
            # See backup_create above — same pickle-safety conversion.
            return {
                "ok": False,
                "error": str(exc.detail),
                "status_code": exc.status_code,
            }
    finally:
        db.close()
