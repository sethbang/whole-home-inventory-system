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
from typing import List

from fastapi import HTTPException
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from ..settings import settings
from ..utctime import utcnow

logger = logging.getLogger(__name__)

# Thumbnail dimensions. 512×512 WebP at quality 82 hits the sweet spot
# between grid-view loading time (~20-40 KB per thumb) and visual quality
# on retina displays. Smaller thumbs look mushy in the gallery; bigger
# ones defeat the point of having a thumbnail.
THUMBNAIL_SIZE: tuple[int, int] = (512, 512)
THUMBNAIL_QUALITY = 82
THUMBNAIL_PREFIX = "thumb_"

# Pillow formats we accept on upload. Anything else is 400'd, both because
# our frontend doesn't render them and because we don't want to store obscure
# codecs that might be vectors for image-library CVEs down the line.
#
# MPO ("Multi Picture Object") is the container iPhones produce in HDR /
# Portrait / Live Photo modes — it's a stack of JPEGs concatenated with
# EXIF MPF metadata pointing at the secondary frames. Pillow opens MPO
# transparently and returns the primary frame for `size`/`convert`/etc.,
# and browsers reading the file as `.jpg` see the first JPEG and ignore
# the trailer. Vision callers should still pipe the bytes through
# ``normalize_for_llm`` before sending to providers — most documented
# vision APIs (OpenAI, Anthropic) accept JPEG/PNG/WEBP only.
ALLOWED_PIL_FORMATS = {"JPEG", "PNG", "WEBP", "HEIC", "HEIF", "MPO"}
EXT_BY_FORMAT = {
    "JPEG": ".jpg",
    "PNG": ".png",
    "WEBP": ".webp",
    "HEIC": ".heic",
    "HEIF": ".heif",
    # Primary frame is JPEG; trailing frames are ignored by browsers.
    "MPO": ".jpg",
}


def remove_image_files_from_disk(filename: str | None) -> None:
    """Best-effort removal of an upload's file plus its thumbnail companion.

    Centralizes the disk-cleanup half of ``ImageService.delete`` so that
    callers which delete ``ItemImage`` rows by other means (cascade from
    item delete, bulk delete) can keep the uploads directory in sync
    without re-implementing the path derivation. All filesystem errors
    are logged and swallowed.
    """
    if not filename:
        return
    upload_dir = str(settings.upload_path)
    on_disk = os.path.join(upload_dir, filename)
    if os.path.exists(on_disk):
        try:
            os.remove(on_disk)
        except OSError as exc:
            logger.warning("could not remove image file %s: %s", on_disk, exc)

    base_stem = os.path.splitext(filename)[0]
    if base_stem:
        thumb_on_disk = os.path.join(
            upload_dir, f"{THUMBNAIL_PREFIX}{base_stem}.webp"
        )
        if os.path.exists(thumb_on_disk):
            try:
                os.remove(thumb_on_disk)
            except OSError as exc:
                logger.warning(
                    "could not remove thumbnail file %s: %s", thumb_on_disk, exc
                )


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


def normalize_for_llm(data: bytes) -> bytes:
    """Return bytes safe to send to an LLM image-input API.

    MPO containers (iPhone HDR / Portrait / Live Photo exports) carry
    multiple JPEG frames; documented vision APIs only accept single-frame
    JPEG/PNG/WEBP, so we re-encode just the primary frame as a clean
    JPEG. Other accepted formats pass through untouched.

    Caller is responsible for having already run ``validate_image_bytes``
    against ``data``; this helper assumes the format is in
    ``ALLOWED_PIL_FORMATS``.
    """
    with Image.open(io.BytesIO(data)) as img:
        fmt = (img.format or "").upper()
        if fmt != "MPO":
            return data
        primary = img.convert("RGB")
        buf = io.BytesIO()
        primary.save(buf, format="JPEG", quality=92)
        return buf.getvalue()


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
        timestamp = utcnow().strftime("%Y%m%d_%H%M%S")
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

    def generate_thumbnail(self, image_id: uuid.UUID) -> bool:
        """Create a 512×512 WebP thumbnail alongside the original.

        Returns True on success, False when the source file is missing
        (e.g. was deleted between upload and this task firing). Writes
        the thumbnail to ``UPLOAD_DIR/thumb_<original_basename>.webp``
        and stamps the ItemImage row with ``thumbnail_path`` +
        ``thumbnail_generated_at``.

        Pure helper — no HTTPException, no ownership check. The caller
        (router enqueueing or the ARQ task) scopes the lookup. Safe to
        call on an image whose thumbnail already exists: the file is
        rewritten and the timestamp refreshed.
        """
        stmt = select(models.ItemImage).where(models.ItemImage.id == image_id)
        image = self.db.execute(stmt).scalar_one_or_none()
        if image is None:
            logger.warning(
                "thumbnail_generate called for missing image id=%s", image_id
            )
            return False

        upload_dir = str(settings.upload_path)
        source_path = os.path.join(upload_dir, image.filename)
        if not os.path.exists(source_path):
            logger.warning(
                "thumbnail source missing on disk: %s (image id=%s)",
                source_path,
                image_id,
            )
            return False

        # Derive the thumbnail filename — ``thumb_<basename>.webp``.
        base_stem = os.path.splitext(image.filename)[0]
        thumbnail_filename = f"{THUMBNAIL_PREFIX}{base_stem}.webp"
        thumbnail_on_disk = os.path.join(upload_dir, thumbnail_filename)

        try:
            with Image.open(source_path) as img:
                # Respect EXIF rotation — otherwise phone uploads come out
                # sideways because the pixels are stored rotated with an
                # orientation flag.
                oriented = ImageOps.exif_transpose(img)
                # Convert palette / alpha-only modes to RGB so WebP encoding
                # doesn't produce surprises.
                if oriented.mode not in ("RGB", "RGBA"):
                    oriented = oriented.convert("RGB")
                fitted = ImageOps.fit(
                    oriented, THUMBNAIL_SIZE, Image.Resampling.LANCZOS
                )
                fitted.save(
                    thumbnail_on_disk,
                    format="WEBP",
                    quality=THUMBNAIL_QUALITY,
                    method=4,
                )
        except (UnidentifiedImageError, OSError):
            logger.exception("thumbnail generation failed for image id=%s", image_id)
            return False

        image.thumbnail_path = os.path.join("uploads", thumbnail_filename)
        image.thumbnail_generated_at = utcnow()
        self.db.commit()
        return True

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

        filename = image.filename
        self.db.delete(image)
        self.db.commit()
        remove_image_files_from_disk(filename)
