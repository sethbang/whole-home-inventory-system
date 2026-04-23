"""Image router — thin HTTP shim over ``services.images.ImageService``.

The router is responsible only for binding FastAPI dependencies (DB session,
auth) and translating the ``UploadFile`` into raw bytes. All validation,
filesystem work, and DB mutation lives in the service layer.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, List

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from .. import database, models, schemas, security
from ..services.images import ImageService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["images"])


def _service(db: Session, user: models.User) -> ImageService:
    return ImageService(db=db, user=user)


@router.post("/items/{item_id}/images", response_model=schemas.ItemImage)
async def upload_item_image(
    request: Request,
    item_id: uuid.UUID,
    file: UploadFile = File(...),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_active_user),
) -> Any:
    contents = await file.read()
    if not contents:
        # Short-circuit before we even build a service; also exercises the
        # "empty upload" path in tests without needing Pillow to run.
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    service = _service(db, current_user)
    stored = service.store_for_item(item_id, contents)

    # v3.0: kick off thumbnail generation. With the worker profile
    # active it's a fire-and-forget enqueue (~1ms overhead on the
    # upload request); without it we run the helper inline so dev
    # behavior matches prod and the grid view still gets thumbnails.
    pool = getattr(request.app.state, "arq", None)
    if pool is not None:
        try:
            await pool.enqueue_job(
                "thumbnail_generate",
                user_id=str(current_user.id),
                image_id=str(stored.id),
            )
        except Exception:
            logger.exception(
                "thumbnail_generate enqueue failed for image %s; running inline",
                stored.id,
            )
            service.generate_thumbnail(stored.id)
            db.refresh(stored)
    else:
        service.generate_thumbnail(stored.id)
        db.refresh(stored)

    return stored


@router.get("/items/{item_id}/images", response_model=List[schemas.ItemImage])
def list_item_images(
    item_id: uuid.UUID,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_active_user),
) -> Any:
    return _service(db, current_user).list_for_item(item_id)


@router.delete("/images/{image_id}")
def delete_image(
    image_id: uuid.UUID,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_active_user),
) -> Any:
    _service(db, current_user).delete(image_id)
    return {"status": "success"}
