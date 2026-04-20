"""Image service — owns Pillow validation, disk write, and ItemImage rows.

Extracted from ``routers/images.py`` in v2.2. The router now delegates to this
service so the same logic is reusable from other entrypoints (the v3.1 vision
feature will feed image bytes into ``validate_bytes`` server-side, for
example), and so the business rules are unit-testable without spinning up a
TestClient.

Services raise ``HTTPException`` directly. This is a pragmatic choice: the
codebase is small enough that defining a parallel hierarchy of domain
exceptions and mapping them in routers would be pure ceremony. If/when we
introduce a non-HTTP entrypoint (CLI, worker job) we'll revisit.
"""

from __future__ import annotations

import io
import logging
import os
import uuid
from datetime import datetime
from typing import List

from fastapi import HTTPException
from PIL import Image, UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from ..settings import settings

logger = logging.getLogger(__name__)

# Pillow formats we accept on upload. Anything else is 400'd, both because
# our frontend doesn't render them and because we don't want to store obscure
# codecs that might be vectors for image-library CVEs down the line.
ALLOWED_PIL_FORMATS = {"JPEG", "PNG", "WEBP", "HEIC", "HEIF"}
EXT_BY_FORMAT = {
    "JPEG": ".jpg",
    "PNG": ".png",
    "WEBP": ".webp",
    "HEIC": ".heic",
    "HEIF": ".heif",
}


def validate_image_bytes(data: bytes) -> str:
    """Validate raw bytes and return the normalized Pillow format name.

    Raises ``HTTPException`` with 400/413 on any rejection. Kept as a module-
    level function (not a method) so callers that don't have a DB session
    handy — e.g. the vision upload path in v3.1 — can still reuse it.
    """
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
        # verify() consumes the stream; reopen for the dimension + format check.
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
    except Exception as exc:
        # Pillow raises a variety of exceptions on malformed inputs; surface
        # them all as 400s rather than letting them bubble up to 500.
        logger.warning("image validation failed: %s", exc)
        raise HTTPException(status_code=400, detail="File is not a valid image")


class ImageService:
    """DB-bound operations on ``ItemImage`` scoped to a single user.

    Instances are cheap and short-lived — one per request is the intended
    pattern. The ``user`` argument is used to enforce ownership on every
    method; there is no escape hatch.
    """

    def __init__(self, db: Session, user: models.User):
        self.db = db
        self.user = user

    # -- internal helpers ---------------------------------------------------

    def _owned_item(self, item_id: uuid.UUID) -> models.Item:
        stmt = select(models.Item).where(
            models.Item.id == item_id,
            models.Item.owner_id == self.user.id,
        )
        item = self.db.execute(stmt).scalar_one_or_none()
        if item is None:
            raise HTTPException(status_code=404, detail="Item not found")
        return item

    # -- public API ---------------------------------------------------------

    def store_for_item(self, item_id: uuid.UUID, data: bytes) -> models.ItemImage:
        """Validate + persist to disk + create the ItemImage row.

        Returns the fresh ``ItemImage`` (refreshed from the DB) on success.
        On any failure after the disk write we attempt to clean up the
        orphaned file so the uploads directory doesn't drift out of sync
        with the DB.
        """
        self._owned_item(item_id)  # 404s if missing or cross-user

        pil_format = validate_image_bytes(data)
        extension = EXT_BY_FORMAT.get(pil_format, ".bin")
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{uuid.uuid4()}{extension}"

        upload_dir = str(settings.upload_path)
        os.makedirs(upload_dir, exist_ok=True)
        on_disk_path = os.path.join(upload_dir, filename)

        try:
            with open(on_disk_path, "wb") as buffer:
                buffer.write(data)
        except OSError as exc:
            logger.exception("failed writing upload to %s", on_disk_path)
            raise HTTPException(
                status_code=500, detail="Could not persist upload"
            ) from exc

        try:
            db_image = models.ItemImage(
                item_id=item_id,
                filename=filename,
                file_path=os.path.join("uploads", filename),
            )
            self.db.add(db_image)
            self.db.commit()
            self.db.refresh(db_image)
            return db_image
        except Exception:
            logger.exception("failed creating image record for item %s", item_id)
            # Clean up the orphaned file so the FS doesn't drift from the DB.
            if os.path.exists(on_disk_path):
                try:
                    os.remove(on_disk_path)
                except OSError:
                    logger.warning(
                        "could not clean up orphan upload at %s", on_disk_path
                    )
            raise HTTPException(status_code=500, detail="Could not create image record")

    def list_for_item(self, item_id: uuid.UUID) -> List[models.ItemImage]:
        item = self._owned_item(item_id)
        return list(item.images)

    def delete(self, image_id: uuid.UUID) -> None:
        stmt = (
            select(models.ItemImage)
            .join(models.Item)
            .where(
                models.ItemImage.id == image_id,
                models.Item.owner_id == self.user.id,
            )
        )
        image = self.db.execute(stmt).scalar_one_or_none()
        if image is None:
            raise HTTPException(status_code=404, detail="Image not found")

        upload_dir = str(settings.upload_path)
        on_disk = os.path.join(upload_dir, image.filename)
        if os.path.exists(on_disk):
            try:
                os.remove(on_disk)
            except OSError as exc:
                # File-removal failures are noisy but non-fatal — we still
                # want the DB row gone so the user doesn't see a ghost image.
                logger.warning("could not remove image file %s: %s", on_disk, exc)

        self.db.delete(image)
        self.db.commit()
