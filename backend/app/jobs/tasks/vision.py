"""ARQ task for vision identification (v3.1 Part C).

The request handler enqueues a ``vision_identify`` job with the raw
image bytes base64-encoded and a user_id. The worker rehydrates the
session, runs :class:`VisionService`, and returns the serialized
result so ``GET /api/jobs/{id}`` can surface it to the frontend.
"""

from __future__ import annotations

import base64
import logging
from typing import Any, Dict, List, Optional

from ... import models
from ...database import SessionLocal
from ...vision import VisionService

logger = logging.getLogger(__name__)


async def vision_identify(
    ctx: Dict[str, Any],
    *,
    user_id: str,
    images_b64: List[str],
    hints: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Run VisionService.identify inside the worker process."""
    logger.info(
        "vision_identify start (user=%s images=%d)", user_id, len(images_b64)
    )
    db = SessionLocal()
    try:
        user = db.query(models.User).filter(models.User.id == user_id).one_or_none()
        if user is None:
            return {"ok": False, "error": "user_not_found"}
        image_bytes = [base64.b64decode(b) for b in images_b64]
        service = VisionService(db=db, user=user)
        result = service.identify(image_bytes, hints=hints)
        return result.model_dump(mode="json")
    finally:
        db.close()
