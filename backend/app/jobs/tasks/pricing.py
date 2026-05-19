"""ARQ task for price refresh (v3.1 Part F).

Background path for the pricing router's POST endpoints. The router
enqueues with either an ``item_id`` or a ``metadata`` dict; the
worker runs :class:`PricingService.estimate` with ``force_refresh``
so any cached value is overridden.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import HTTPException
from sqlalchemy import select

from ... import models
from ...database import SessionLocal
from ...pricing import PricingService

logger = logging.getLogger(__name__)


async def pricing_refresh(
    ctx: Dict[str, Any],
    *,
    user_id: str,
    item_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    force_refresh: bool = True,
) -> Dict[str, Any]:
    """Run PricingService.estimate inside the worker process."""
    logger.info(
        "pricing_refresh start (user=%s item=%s force=%s)",
        user_id,
        item_id,
        force_refresh,
    )
    db = SessionLocal()
    try:
        user = db.execute(
            select(models.User).where(models.User.id == user_id)
        ).scalar_one_or_none()
        if user is None:
            return {"ok": False, "error": "user_not_found", "status_code": 404}
        service = PricingService(db=db, user=user)
        try:
            # See jobs/tasks/vision.py — await the async variant directly
            # since the ARQ worker runs inside an active asyncio loop.
            envelope = await service.estimate_async(
                item_id=item_id,
                metadata=metadata,
                force_refresh=force_refresh,
            )
        except HTTPException as exc:
            # See jobs/tasks/vision.py for the rationale — Starlette's
            # HTTPException doesn't survive the ARQ pickle round-trip, so
            # convert to a serializable shape the jobs router knows to
            # surface as a failed JobDetail.
            return {
                "ok": False,
                "error": str(exc.detail),
                "status_code": exc.status_code,
            }
        return envelope.model_dump(mode="json")
    finally:
        db.close()
