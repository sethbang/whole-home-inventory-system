"""Backup router — thin HTTP shim over ``services.backups.BackupService``.

All validation, filesystem work, and DB mutation lives in the service layer.
The router is responsible only for binding FastAPI dependencies, translating
between ``UploadFile`` / ``StreamingResponse`` and service calls, and
centralizing the unexpected-error scrub to keep Python exception strings out
of response bodies.

Note: we intentionally do NOT use ``from __future__ import annotations`` in
router modules — FastAPI + Pydantic rely on runtime-evaluated type hints for
body/query parameter resolution, and the combination with decorators like
``@limiter.limit`` that wrap the function makes the forward-reference
resolution fail at request time.
"""

import logging
import os
import shutil
from typing import Optional

from fastapi import (
    APIRouter,
    Body,
    Depends,
    File,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..rate_limit import limiter
from ..security import get_current_active_user
from ..services.backups import BackupService, _backup_dir

logger = logging.getLogger(__name__)

router = APIRouter()


def _service(db: Session, user: models.User) -> BackupService:
    return BackupService(db=db, user=user)


@router.post("/backups", response_model=schemas.Backup)
@limiter.limit("5/hour")
async def create_backup(
    request: Request,  # required by slowapi
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    try:
        return _service(db, current_user).create()
    except HTTPException:
        raise
    except Exception:
        logger.exception("backup creation failed")
        raise HTTPException(status_code=500, detail="Failed to create backup")


@router.get("/backups", response_model=schemas.BackupList)
async def list_backups(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    return {"backups": _service(db, current_user).list()}


@router.post("/backups/{backup_id}/restore", response_model=schemas.RestoreResponse)
@limiter.limit("3/hour")
async def restore_backup(
    request: Request,  # required by slowapi
    backup_id: str,
    dry_run: bool = Query(
        True,
        description=(
            "When true (the default), return a non-destructive preview describing "
            "what would be restored. When false the caller MUST supply "
            "confirm_item_count in the body, matching the server-side item count."
        ),
    ),
    body: Optional[schemas.RestoreRequest] = Body(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    svc = _service(db, current_user)
    try:
        if dry_run:
            return svc.preview_restore(backup_id)
        return svc.commit_restore(backup_id, body.confirm_item_count if body else None)
    except HTTPException:
        raise
    except Exception:
        logger.exception("error restoring backup %s", backup_id)
        raise HTTPException(status_code=500, detail="Restore failed; check server logs")


@router.post("/backups/upload")
async def upload_backup(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    # Stage the upload to disk before handing it to the service. The service
    # validates magic bytes and decompressed size — trusting the extension or
    # the content-type header would be unsafe.
    backup_dir = _backup_dir()
    staged_path = os.path.join(backup_dir, file.filename or "upload.zip")
    try:
        with open(staged_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except OSError:
        logger.exception("failed writing uploaded backup to disk")
        raise HTTPException(status_code=500, detail="Error processing backup file")

    try:
        return _service(db, current_user).upload(file.filename or "", staged_path)
    except HTTPException:
        raise
    except Exception:
        logger.exception("error processing uploaded backup")
        if os.path.exists(staged_path):
            try:
                os.remove(staged_path)
            except OSError:
                logger.warning("could not clean up staged upload")
        raise HTTPException(status_code=500, detail="Error processing backup file")


@router.delete("/backups/{backup_id}")
async def delete_backup(
    backup_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    _service(db, current_user).delete(backup_id)
    return {"message": "Backup deleted successfully"}


@router.get("/backups/{backup_id}/download")
async def download_backup(
    backup_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    backup, path = _service(db, current_user).get_download_path(backup_id)
    try:
        response = FileResponse(
            str(path),
            media_type="application/zip",
            filename=backup.filename,
        )
        response.headers["Content-Disposition"] = (
            f'attachment; filename="{backup.filename}"'
        )
        return response
    except Exception:
        logger.exception("error serving backup file")
        raise HTTPException(status_code=500, detail="Error serving backup file")
