"""PricingService — orchestrates cache + providers + item update.

Exposes both sync and async entry points. The async variants
(``estimate_async`` / ``_run_provider_async``) are the canonical
ones and are awaited directly by the async request handlers and
the ARQ worker task. The sync variants wrap them in
:func:`asyncio.run` for tests and any future non-async callers;
they must NOT be used from within a running event loop.

High-level flow:

1. Build a canonical :class:`ItemIdentity` from the item or metadata.
2. Look up a fresh cache entry for each configured provider (priority
   order). Return the first hit.
3. Walk providers in order:
   * Success → cache + return.
   * PriceProviderRateLimited / PriceProviderUnavailable → try the
     next provider. Stash the stale-fallback candidate from the
     cache so we can serve it if every provider fails.
   * PriceProviderError / PriceProviderNoResult → log + next.
4. If no provider succeeded but we have a stale cache entry, return
   it with a ``stale=True`` flag (confidence already decayed by
   :class:`PriceCache`). Otherwise raise HTTPException(502).
5. On success with an ``item_id`` input, stamp the item's
   ``estimated_value_low/median/high/price_last_checked/price_provider``
   columns so the UI can sort/filter by value without re-fetching.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, Optional, Sequence, Tuple

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from ..llm import DailyBudgetGuard
from ..schemas_llm import (
    PROMPT_VERSION,
    PriceEstimate,
    PriceEstimateEnvelope,
)
from ..services import llm_config as llm_config_service
from ..settings import settings
from .cache import CacheLookupResult, PriceCache
from .normalizer import ItemIdentity, normalize_identity
from .provider_base import (
    PriceProvider,
    PriceProviderError,
    PriceProviderNoResult,
    PriceProviderRateLimited,
    PriceProviderUnavailable,
)
from .provider_ebay_browse import EbayBrowseProvider
from .provider_llm import LLMPricingProvider

logger = logging.getLogger(__name__)


class PricingService:
    def __init__(
        self,
        db: Session,
        user: models.User,
        *,
        providers: Optional[Sequence[PriceProvider]] = None,
    ) -> None:
        self.db = db
        self.user = user
        self._cache = PriceCache(db)
        self._providers_override = providers

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def estimate(
        self,
        *,
        item_id: Optional[str] = None,
        metadata: Optional[Mapping[str, Any]] = None,
        force_refresh: bool = False,
    ) -> PriceEstimateEnvelope:
        """Synchronous entry point. Wraps :meth:`estimate_async`."""
        return asyncio.run(
            self.estimate_async(
                item_id=item_id,
                metadata=metadata,
                force_refresh=force_refresh,
            )
        )

    async def estimate_async(
        self,
        *,
        item_id: Optional[str] = None,
        metadata: Optional[Mapping[str, Any]] = None,
        force_refresh: bool = False,
    ) -> PriceEstimateEnvelope:
        """Resolve an estimate (async). Caller handles enqueue logic.

        The router chooses between awaiting this directly (sync
        fallback) and enqueueing a ``pricing_refresh`` ARQ task that
        eventually awaits this same method from the worker process.
        """
        eff = llm_config_service.get_effective_for_db(self.db)
        if not eff.pricing_enabled:
            raise HTTPException(
                status_code=503,
                detail="Item-value pricing is disabled on this deployment.",
            )

        item, identity = self._resolve_input(item_id=item_id, metadata=metadata)

        # Fast path: fresh cache hit on the priority provider wins.
        if not force_refresh:
            for provider_name in settings.PRICING_PROVIDERS:
                fresh = self._cache.get_fresh(identity.hash, provider_name)
                if fresh is not None:
                    logger.info(
                        "pricing cache hit (provider=%s hash=%s)",
                        provider_name,
                        identity.hash[:8],
                    )
                    envelope = _envelope_from_cache(fresh, cache_hit=True)
                    if item is not None:
                        self._stamp_item(item, envelope)
                    return envelope

        # Cache miss (or force refresh). Run providers in priority
        # order. Track a stale-fallback candidate in case everyone
        # fails.
        stale_fallback: Optional[CacheLookupResult] = None
        last_error: Optional[Exception] = None

        for provider in self._resolve_providers():
            try:
                estimate = await self._run_provider_async(provider, identity)
            except PriceProviderNoResult as exc:
                logger.info(
                    "pricing provider %s returned no result: %s",
                    provider.name,
                    exc,
                )
                last_error = exc
                continue
            except PriceProviderRateLimited as exc:
                logger.warning(
                    "pricing provider %s rate-limited: %s", provider.name, exc
                )
                last_error = exc
                # Remember any stale entry from this provider so we can
                # fall back if every other provider also fails.
                stash = self._cache.get_stale_fallback(identity.hash, provider.name)
                if stash is not None and stale_fallback is None:
                    stale_fallback = stash
                continue
            except PriceProviderUnavailable as exc:
                logger.warning(
                    "pricing provider %s unavailable: %s", provider.name, exc
                )
                last_error = exc
                continue
            except PriceProviderError as exc:
                logger.warning(
                    "pricing provider %s errored: %s", provider.name, exc
                )
                last_error = exc
                continue

            # Success.
            self._cache.set(identity.hash, provider.name, estimate)
            envelope = PriceEstimateEnvelope(
                estimate=estimate,
                provider=provider.name,
                prompt_version=PROMPT_VERSION if provider.name == "llm" else "",
                queried_at=datetime.now(timezone.utc),
                cache_hit=False,
            )
            if item is not None:
                self._stamp_item(item, envelope)
            return envelope

        # Every provider failed — try the stale fallback.
        if stale_fallback is not None:
            logger.info(
                "all providers failed; serving stale fallback from %s",
                stale_fallback.provider,
            )
            return _envelope_from_cache(stale_fallback, cache_hit=True)

        detail = (
            "No pricing provider returned a usable estimate"
            + (f" ({last_error})" if last_error else "")
        )
        raise HTTPException(status_code=502, detail=detail)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _resolve_input(
        self,
        *,
        item_id: Optional[str],
        metadata: Optional[Mapping[str, Any]],
    ) -> Tuple[Optional[models.Item], ItemIdentity]:
        if item_id is None and metadata is None:
            raise HTTPException(
                status_code=400,
                detail="Either item_id or metadata must be provided.",
            )
        if item_id is not None:
            stmt = select(models.Item).where(
                models.Item.id == item_id,
                models.Item.owner_id == self.user.id,
            )
            item = self.db.execute(stmt).scalar_one_or_none()
            if item is None:
                raise HTTPException(status_code=404, detail="Item not found")
            return item, normalize_identity(item)
        return None, normalize_identity(metadata or {})

    def _resolve_providers(self) -> Iterable[PriceProvider]:
        if self._providers_override is not None:
            yield from self._providers_override
            return
        seen: set[str] = set()
        for name in settings.PRICING_PROVIDERS:
            if name in seen:
                continue
            seen.add(name)
            if name == "ebay":
                yield EbayBrowseProvider()
            elif name == "llm":
                yield LLMPricingProvider()
            else:
                logger.warning("unknown pricing provider %r in PRICING_PROVIDERS", name)

    def _run_provider(
        self, provider: PriceProvider, identity: ItemIdentity
    ) -> PriceEstimate:
        """Sync shim around :meth:`_run_provider_async`."""
        return asyncio.run(self._run_provider_async(provider, identity))

    async def _run_provider_async(
        self, provider: PriceProvider, identity: ItemIdentity
    ) -> PriceEstimate:
        """Invoke the async provider (async path).

        The LLM provider touches the budget guard (we check before,
        record after). The eBay provider doesn't — it's a free-tier
        API with its own rate limiting.
        """
        guard: Optional[DailyBudgetGuard] = None
        if provider.name == "llm":
            guard = DailyBudgetGuard(self.db, self.user)
            guard.check_or_raise("pricing")

        estimate = await provider.lookup(identity)

        if guard is not None:
            # The LLM provider stashes merged usage across its two
            # calls (research + extraction) on ``last_usage``.
            provider_usage = getattr(provider, "last_usage", None) or {
                "prompt_tokens": 0,
                "completion_tokens": 0,
            }
            guard.record_usage(
                "pricing",
                model=llm_config_service.get_effective_for_db(self.db).pricing_model,
                usage=provider_usage,
            )
        return estimate

    def _stamp_item(
        self, item: models.Item, envelope: PriceEstimateEnvelope
    ) -> None:
        """Persist the latest estimate on the item row.

        Columns landed in v2.2 (pricing prewire); v3.1 is the first
        release to populate them.
        """
        item.estimated_value_low = envelope.estimate.low
        item.estimated_value_median = envelope.estimate.median
        item.estimated_value_high = envelope.estimate.high
        item.price_last_checked = datetime.now(timezone.utc).replace(tzinfo=None)
        item.price_provider = envelope.provider
        self.db.commit()


def _envelope_from_cache(
    hit: CacheLookupResult, *, cache_hit: bool
) -> PriceEstimateEnvelope:
    return PriceEstimateEnvelope(
        estimate=hit.estimate,
        provider=hit.provider,
        prompt_version="",
        queried_at=hit.stored_at.replace(tzinfo=timezone.utc)
        if hit.stored_at.tzinfo is None
        else hit.stored_at,
        cache_hit=cache_hit,
    )


__all__ = ["PricingService"]
