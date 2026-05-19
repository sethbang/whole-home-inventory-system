"""Item-value pricing router (v3.1 Part F).

Three endpoints:

* ``POST /api/pricing/estimate`` — body carries either ``item_id`` or
  ``metadata``. Returns the cached envelope (sync) or 202 +
  :class:`JobReference` when the ARQ worker is active.
* ``POST /api/pricing/refresh/{item_id}`` — force a fresh lookup,
  bypassing the cache. Rate-limited 5/min/user by slowapi to keep
  us from DOSing eBay or burning LLM quota.
* ``GET  /api/pricing/estimate/{item_id}`` — read-only variant that
  uses the cache; enqueues a refresh only when no cached value
  exists.

Note: this module intentionally does NOT use ``from __future__
import annotations`` — FastAPI + Pydantic need runtime-evaluated
type hints for body parameter resolution on the discriminated-union
response model.
"""

import logging
from typing import Any, Dict, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import database, models, schemas
from ..pricing import PricingService
from ..rate_limit import limiter
from ..security import get_current_active_user
from ..services import llm_config as llm_config_service
from ..settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pricing", tags=["pricing"])


class EstimateRequest(BaseModel):
    """Body for ``POST /api/pricing/estimate``.

    Exactly one of ``item_id`` or ``metadata`` must be set. Passing
    both produces 422. Metadata is the shape the normalizer expects
    — brand, model_number, name, condition, year.
    """

    item_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description=(
            "Free-form item metadata for anonymous lookups "
            "(e.g. 'what would this be worth before I buy it?'). "
            "Must include at least a brand or model_number."
        ),
    )


@router.post(
    "/estimate",
    response_model=Union[schemas.JobReference, schemas.PriceEstimateEnvelope],
)
async def estimate_price(
    request: Request,
    body: EstimateRequest,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    _guard_enabled(db)
    _guard_one_of_inputs(body)
    return await _enqueue_or_run(
        request=request,
        db=db,
        user=current_user,
        item_id=body.item_id,
        metadata=body.metadata,
        force_refresh=False,
    )


@router.post(
    "/refresh/{item_id}",
    response_model=Union[schemas.JobReference, schemas.PriceEstimateEnvelope],
)
@limiter.limit("5/minute")
async def refresh_price(
    request: Request,  # required by slowapi
    item_id: str,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    _guard_enabled(db)
    return await _enqueue_or_run(
        request=request,
        db=db,
        user=current_user,
        item_id=item_id,
        metadata=None,
        force_refresh=True,
    )


@router.get(
    "/estimate/{item_id}",
    response_model=Union[schemas.JobReference, schemas.PriceEstimateEnvelope],
)
async def get_cached_estimate(
    request: Request,
    item_id: str,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    _guard_enabled(db)
    return await _enqueue_or_run(
        request=request,
        db=db,
        user=current_user,
        item_id=item_id,
        metadata=None,
        force_refresh=False,
    )


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _guard_enabled(db: Session) -> None:
    eff = llm_config_service.get_effective_for_db(db)
    if not eff.pricing_enabled:
        raise HTTPException(
            status_code=503,
            detail="Item-value pricing is disabled on this deployment.",
        )


def _guard_one_of_inputs(body: EstimateRequest) -> None:
    if body.item_id is None and body.metadata is None:
        raise HTTPException(
            status_code=400,
            detail="Provide either item_id or metadata.",
        )
    if body.item_id is not None and body.metadata is not None:
        raise HTTPException(
            status_code=400,
            detail="Provide only one of item_id or metadata, not both.",
        )


async def _enqueue_or_run(
    *,
    request: Request,
    db: Session,
    user: models.User,
    item_id: Optional[str],
    metadata: Optional[Dict[str, Any]],
    force_refresh: bool,
):
    """Serve from cache synchronously; enqueue a job for cache misses."""
    service = PricingService(db=db, user=user)

    # Short-circuit: if the cache already has a fresh hit for any
    # configured provider and we're not force-refreshing, return the
    # cached envelope inline. This is the cheap path the UI lands on
    # most of the time.
    if not force_refresh:
        for provider_name in settings.PRICING_PROVIDERS:
            if item_id is not None:
                identity_source: Any = _resolve_item_or_404(db, user, item_id)
            else:
                identity_source = metadata or {}
            from ..pricing import normalize_identity  # local import to avoid cycle

            identity = normalize_identity(identity_source)
            hit = service._cache.get_fresh(identity.hash, provider_name)
            if hit is not None:
                from ..pricing.service import _envelope_from_cache  # noqa: WPS433

                envelope = _envelope_from_cache(hit, cache_hit=True)
                if isinstance(identity_source, models.Item):
                    service._stamp_item(identity_source, envelope)
                return envelope

    pool = getattr(request.app.state, "arq", None)
    if pool is not None:
        try:
            job = await pool.enqueue_job(
                "pricing_refresh",
                user_id=str(user.id),
                item_id=item_id,
                metadata=metadata,
                force_refresh=force_refresh,
            )
        except Exception:
            logger.exception(
                "pricing_refresh enqueue failed; falling back to sync"
            )
        else:
            if job is not None:
                return schemas.JobReference(job_id=job.job_id)

    # Sync-code-path fallback (no worker pool). Use the async variant
    # directly since `_enqueue_or_run` itself is an async handler —
    # service.estimate() wraps the coroutine in asyncio.run() which
    # would crash inside the already-running event loop.
    return await service.estimate_async(
        item_id=item_id, metadata=metadata, force_refresh=force_refresh
    )


def _resolve_item_or_404(
    db: Session, user: models.User, item_id: str
) -> models.Item:
    item = db.execute(
        select(models.Item).where(
            models.Item.id == item_id, models.Item.owner_id == user.id
        )
    ).scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return item
