"""ARQ task for thumbnail generation (v3.0 Part E).

Runs outside the request thread so a big photo upload returns to the
user in <100ms while the 512×512 WebP thumbnail generates in the
background. When the worker isn't active, the upload endpoint
fallback runs the same helper inline — same behavior, just on the
request thread.

Takes ``user_id`` as a kwarg so the jobs router's ownership guard
can verify who owns each job.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict

from sqlalchemy import select

from ... import models
from ...database import SessionLocal
from ...services.images import ImageService

logger = logging.getLogger(__name__)


async def thumbnail_generate(
    ctx: Dict[str, Any], *, user_id: str, image_id: str
) -> Dict[str, Any]:
    """Generate the 512×512 WebP thumbnail for a freshly-uploaded image."""
    logger.info("thumbnail_generate task start (image=%s user=%s)", image_id, user_id)

    db = SessionLocal()
    try:
        user = db.execute(
            select(models.User).where(models.User.id == user_id)
        ).scalar_one_or_none()
        if user is None:
            # Stale task (user deleted between enqueue and run). Log but
            # don't raise — nothing the operator can fix downstream.
            logger.warning(
                "thumbnail_generate skipped: user %s no longer exists", user_id
            )
            return {"generated": False, "reason": "user_not_found"}

        service = ImageService(db=db, user=user)
        try:
            image_uuid = uuid.UUID(image_id)
        except ValueError:
            logger.warning("thumbnail_generate skipped: bad image id %r", image_id)
            return {"generated": False, "reason": "bad_image_id"}

        generated = service.generate_thumbnail(image_uuid)
        return {"generated": generated, "image_id": image_id}
    finally:
        db.close()
