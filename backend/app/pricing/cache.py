"""Persistent cache for pricing estimates (v3.1).

Uses the ``price_cache`` table that landed in v2.2 so the schema work
is already done. Fresh entries (within PRICING_CACHE_DAYS) come back
with full confidence; stale entries (past TTL but within 60 days)
are returned when the provider is rate-limited or unavailable, with
``confidence *= 0.75`` to flag the staleness to the UI.

Providers are keyed independently — ``(identity_hash, provider_name)``
is the primary key, so an eBay miss doesn't stomp on an LLM hit.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from ..schemas_llm import PriceEstimate
from ..settings import settings

logger = logging.getLogger(__name__)

# Upper bound on staleness. Beyond this we treat the cache as empty
# even on rate-limit fallback — a 6-month-old estimate for a
# consumer-electronics item is more misleading than useful.
_STALE_FALLBACK_MAX_DAYS = 60

# Multiplier applied to stored confidence when we serve a stale entry
# as a fallback (i.e. the provider failed but we had something
# cached). Chosen to visibly degrade the UI's badge without going to
# zero.
_STALE_CONFIDENCE_DECAY = 0.75


@dataclass(frozen=True, slots=True)
class CacheLookupResult:
    estimate: PriceEstimate
    stale: bool
    stored_at: datetime
    provider: str


class PriceCache:
    """Thin wrapper around the ``price_cache`` table.

    Not a service in its own right — :class:`PricingService` owns the
    lifecycle; this class just encapsulates the SQL.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    def get_fresh(
        self, identity_hash: str, provider: str
    ) -> Optional[CacheLookupResult]:
        """Return a cache entry only when it's within the fresh TTL."""
        row = self._row(identity_hash, provider)
        if row is None:
            return None
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        if row.expires_at <= now:
            return None
        return _row_to_result(row, stale=False)

    def get_stale_fallback(
        self, identity_hash: str, provider: str
    ) -> Optional[CacheLookupResult]:
        """Return an older entry (past TTL but within max staleness).

        Confidence is decayed by ``_STALE_CONFIDENCE_DECAY``. Used when
        the live provider is rate-limited or unreachable and the
        alternative is returning no answer at all.
        """
        row = self._row(identity_hash, provider)
        if row is None:
            return None
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        max_age = now - timedelta(days=_STALE_FALLBACK_MAX_DAYS)
        if row.created_at < max_age:
            logger.info(
                "stale cache entry exceeded %d-day max age (hash=%s provider=%s)",
                _STALE_FALLBACK_MAX_DAYS,
                identity_hash[:8],
                provider,
            )
            return None
        # Decay the confidence in-flight; don't persist the decayed
        # value back.
        estimate = _payload_to_estimate(row.payload)
        decayed = estimate.model_copy(
            update={
                "confidence": max(0.0, estimate.confidence * _STALE_CONFIDENCE_DECAY)
            }
        )
        return CacheLookupResult(
            estimate=decayed,
            stale=True,
            stored_at=row.created_at,
            provider=provider,
        )

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------

    def set(
        self,
        identity_hash: str,
        provider: str,
        estimate: PriceEstimate,
    ) -> None:
        """Upsert a fresh estimate. TTL driven by PRICING_CACHE_DAYS."""
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        expires = now + timedelta(days=settings.PRICING_CACHE_DAYS)
        payload = estimate.model_dump(mode="json")

        row = self._row(identity_hash, provider)
        if row is None:
            row = models.PriceCache(
                identity_hash=identity_hash,
                provider=provider,
                payload=payload,
                created_at=now,
                expires_at=expires,
            )
            self.db.add(row)
        else:
            row.payload = payload
            row.created_at = now
            row.expires_at = expires
        self.db.commit()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _row(
        self, identity_hash: str, provider: str
    ) -> Optional[models.PriceCache]:
        # price_cache's PK is (identity_hash) today (v2.2) — the
        # provider column was added for future use but isn't part of
        # the PK. We filter on both so the same hash can host one
        # entry per provider.
        stmt = select(models.PriceCache).where(
            models.PriceCache.identity_hash == identity_hash,
            models.PriceCache.provider == provider,
        )
        return self.db.execute(stmt).scalar_one_or_none()


def _row_to_result(
    row: "models.PriceCache", *, stale: bool
) -> CacheLookupResult:
    return CacheLookupResult(
        estimate=_payload_to_estimate(row.payload),
        stale=stale,
        stored_at=row.created_at,
        provider=row.provider,
    )


def _payload_to_estimate(payload: dict) -> PriceEstimate:
    return PriceEstimate.model_validate(payload)
