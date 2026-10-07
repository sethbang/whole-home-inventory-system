"""Tests for the PriceCache layer (v3.1 Part D)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app import models
from app.pricing.cache import (
    _STALE_CONFIDENCE_DECAY,
    _STALE_FALLBACK_MAX_DAYS,
    PriceCache,
)
from app.schemas_llm import PriceEstimate, PriceSource
from app.settings import settings


def _estimate(confidence: float = 0.8) -> PriceEstimate:
    return PriceEstimate(
        currency="USD",
        low=100.0,
        median=150.0,
        high=200.0,
        sample_count=5,
        sources=[
            PriceSource(
                title="Test listing",
                url="https://ebay.com/itm/1",
                price=150.0,
                condition="USED",
                sold_date="2026-04-01",
                source_site="ebay",
            )
        ],
        confidence=confidence,
    )


def _set_row_age(
    db_session, identity_hash: str, provider: str, *, days_old: int
):
    """Directly rewind created_at + expires_at so we can exercise TTL paths."""
    row = (
        db_session.query(models.PriceCache)
        .filter_by(identity_hash=identity_hash, provider=provider)
        .one()
    )
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    row.created_at = now - timedelta(days=days_old)
    row.expires_at = row.created_at + timedelta(days=settings.PRICING_CACHE_DAYS)
    db_session.commit()


def test_get_fresh_returns_none_for_empty_cache(db_session):
    cache = PriceCache(db_session)
    assert cache.get_fresh("nothing", "ebay") is None


def test_set_then_get_fresh_round_trips(db_session):
    cache = PriceCache(db_session)
    estimate = _estimate()
    cache.set("hash-a", "ebay", estimate)

    result = cache.get_fresh("hash-a", "ebay")
    assert result is not None
    assert result.stale is False
    assert result.provider == "ebay"
    assert result.estimate.median == 150.0
    assert result.estimate.confidence == 0.8
    assert len(result.estimate.sources) == 1


def test_get_fresh_ignores_entry_past_ttl(db_session, monkeypatch):
    monkeypatch.setattr(settings, "PRICING_CACHE_DAYS", 14)
    cache = PriceCache(db_session)
    cache.set("hash-a", "ebay", _estimate())
    _set_row_age(db_session, "hash-a", "ebay", days_old=settings.PRICING_CACHE_DAYS + 1)

    assert cache.get_fresh("hash-a", "ebay") is None


def test_stale_fallback_returns_decayed_confidence(db_session, monkeypatch):
    monkeypatch.setattr(settings, "PRICING_CACHE_DAYS", 14)
    cache = PriceCache(db_session)
    cache.set("hash-b", "ebay", _estimate(confidence=0.9))
    # 30 days old — past TTL but within the 60-day fallback window.
    _set_row_age(db_session, "hash-b", "ebay", days_old=30)

    fallback = cache.get_stale_fallback("hash-b", "ebay")
    assert fallback is not None
    assert fallback.stale is True
    # Confidence decayed by the documented multiplier.
    assert fallback.estimate.confidence == pytest.approx(
        0.9 * _STALE_CONFIDENCE_DECAY
    )
    # low/median/high unchanged.
    assert fallback.estimate.median == 150.0


def test_stale_fallback_refuses_entries_past_max_age(db_session):
    cache = PriceCache(db_session)
    cache.set("hash-c", "ebay", _estimate())
    _set_row_age(
        db_session,
        "hash-c",
        "ebay",
        days_old=_STALE_FALLBACK_MAX_DAYS + 5,
    )

    assert cache.get_stale_fallback("hash-c", "ebay") is None


def test_providers_are_keyed_independently(db_session):
    """An eBay miss shouldn't stomp on an LLM hit for the same hash."""
    cache = PriceCache(db_session)
    cache.set("shared-hash", "ebay", _estimate(confidence=0.9))
    cache.set(
        "shared-hash",
        "llm",
        _estimate(confidence=0.6).model_copy(update={"median": 120.0}),
    )

    ebay = cache.get_fresh("shared-hash", "ebay")
    llm = cache.get_fresh("shared-hash", "llm")
    assert ebay is not None and llm is not None
    assert ebay.estimate.confidence == 0.9
    assert llm.estimate.median == 120.0


def test_set_overwrites_existing_row(db_session):
    cache = PriceCache(db_session)
    cache.set("hash-d", "ebay", _estimate(confidence=0.5))
    cache.set("hash-d", "ebay", _estimate(confidence=0.95))
    result = cache.get_fresh("hash-d", "ebay")
    assert result is not None
    assert result.estimate.confidence == 0.95
    # Exactly one row.
    count = (
        db_session.query(models.PriceCache)
        .filter_by(identity_hash="hash-d", provider="ebay")
        .count()
    )
    assert count == 1
