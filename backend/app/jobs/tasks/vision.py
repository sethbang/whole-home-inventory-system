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

from fastapi import HTTPException
from sqlalchemy import select

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
        user = db.execute(
            select(models.User).where(models.User.id == user_id)
        ).scalar_one_or_none()
        if user is None:
            return {"ok": False, "error": "user_not_found", "status_code": 404}
        image_bytes = [base64.b64decode(b) for b in images_b64]
        service = VisionService(db=db, user=user)
        try:
            # The ARQ worker runs tasks in an active asyncio loop, so we
            # await the async entry point directly. Calling service.identify
            # here would wrap the coroutine in asyncio.run() and raise
            # "asyncio.run() cannot be called from a running event loop".
            result = await service.identify_async(image_bytes, hints=hints)
        except HTTPException as exc:
            # Starlette's HTTPException doesn't pickle cleanly through ARQ
            # (kwargs-only init), so re-raising poisons the result blob and
            # GET /api/jobs/{id} fails with DeserializationError. Catch it
            # here and translate into a serializable dict; the jobs router
            # detects this shape and surfaces it as a failed JobDetail.
            return {
                "ok": False,
                "error": str(exc.detail),
                "status_code": exc.status_code,
            }
        return result.model_dump(mode="json")
    finally:
        db.close()
