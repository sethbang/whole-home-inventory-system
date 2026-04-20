import io
import logging
import os
import uuid
from datetime import datetime
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from PIL import Image, UnidentifiedImageError
from sqlalchemy import and_
from sqlalchemy.orm import Session

from .. import database, models, schemas, security
from ..settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["images"])

UPLOAD_DIR = str(settings.upload_path)
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_PIL_FORMATS = {"JPEG", "PNG", "WEBP", "HEIC", "HEIF"}
EXT_BY_FORMAT = {
    "JPEG": ".jpg",
    "PNG": ".png",
    "WEBP": ".webp",
    "HEIC": ".heic",
    "HEIF": ".heif",
}


def _validate_image_bytes(data: bytes) -> str:
    """Return the normalized Pillow format name, or raise HTTPException."""
    if len(data) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    if len(data) > settings.MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds maximum size of {settings.MAX_UPLOAD_BYTES} bytes",
        )
    try:
        with Image.open(io.BytesIO(data)) as img:
            img.verify()
        # verify() leaves the image unusable for further ops; reopen for dimension check.
        with Image.open(io.BytesIO(data)) as img:
            fmt = (img.format or "").upper()
            if fmt not in ALLOWED_PIL_FORMATS:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported image format: {fmt or 'unknown'}",
                )
            width, height = img.size
            if max(width, height) > settings.MAX_IMAGE_DIMENSION:
                raise HTTPException(
                    status_code=400,
                    detail=f"Image dimensions exceed {settings.MAX_IMAGE_DIMENSION}px",
                )
            return fmt
    except UnidentifiedImageError:
        raise HTTPException(status_code=400, detail="File is not a valid image")
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 - surface Pillow parse failures as 400
        logger.warning("image validation failed: %s", exc)
        raise HTTPException(status_code=400, detail="File is not a valid image")


@router.post("/items/{item_id}/images", response_model=schemas.ItemImage)
async def upload_item_image(
    item_id: uuid.UUID,
    file: UploadFile = File(...),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_active_user),
) -> Any:
    item = db.query(models.Item).filter(
        and_(models.Item.id == item_id, models.Item.owner_id == current_user.id)
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    contents = await file.read()
    pil_format = _validate_image_bytes(contents)

    extension = EXT_BY_FORMAT.get(pil_format, ".bin")
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{uuid.uuid4()}{extension}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    try:
        with open(file_path, "wb") as buffer:
            buffer.write(contents)
    except OSError as exc:
        logger.exception("failed writing upload to %s", file_path)
        raise HTTPException(status_code=500, detail="Could not persist upload") from exc

    try:
        db_image = models.ItemImage(
            item_id=item_id,
            filename=filename,
            file_path=os.path.join("uploads", filename),
        )
        db.add(db_image)
        db.commit()
        db.refresh(db_image)
        return db_image
    except Exception:
        logger.exception("failed creating image record for item %s", item_id)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                logger.warning("could not clean up orphan file at %s", file_path)
        raise HTTPException(status_code=500, detail="Could not create image record")


@router.get("/items/{item_id}/images", response_model=List[schemas.ItemImage])
def list_item_images(
    item_id: uuid.UUID,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_active_user),
) -> Any:
    item = db.query(models.Item).filter(
        and_(models.Item.id == item_id, models.Item.owner_id == current_user.id)
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item.images


@router.delete("/images/{image_id}")
def delete_image(
    image_id: uuid.UUID,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_active_user),
) -> Any:
    image = db.query(models.ItemImage).join(models.Item).filter(
        and_(models.ItemImage.id == image_id, models.Item.owner_id == current_user.id)
    ).first()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    on_disk = os.path.join(UPLOAD_DIR, image.filename)
    if os.path.exists(on_disk):
        try:
            os.remove(on_disk)
        except OSError as exc:
            logger.warning("could not remove image file %s: %s", on_disk, exc)

    db.delete(image)
    db.commit()
    return {"status": "success"}
