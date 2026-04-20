"""Image router — thin HTTP shim over ``services.images.ImageService``.

The router is responsible only for binding FastAPI dependencies (DB session,
auth) and translating the ``UploadFile`` into raw bytes. All validation,
filesystem work, and DB mutation lives in the service layer.
"""

from __future__ import annotations

import uuid
from typing import Any, List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from .. import database, models, schemas, security
from ..services.images import ImageService

router = APIRouter(tags=["images"])


def _service(db: Session, user: models.User) -> ImageService:
    return ImageService(db=db, user=user)


@router.post("/items/{item_id}/images", response_model=schemas.ItemImage)
async def upload_item_image(
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
    return _service(db, current_user).store_for_item(item_id, contents)


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
