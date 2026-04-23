"""ARQ task for price refresh (v3.1 Part F).

Background path for the pricing router's POST endpoints. The router
enqueues with either an ``item_id`` or a ``metadata`` dict; the
worker runs :class:`PricingService.estimate` with ``force_refresh``
so any cached value is overridden.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

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
        user = db.query(models.User).filter(models.User.id == user_id).one_or_none()
        if user is None:
            return {"ok": False, "error": "user_not_found"}
        service = PricingService(db=db, user=user)
        envelope = service.estimate(
            item_id=item_id,
            metadata=metadata,
            force_refresh=force_refresh,
        )
        return envelope.model_dump(mode="json")
    finally:
        db.close()
