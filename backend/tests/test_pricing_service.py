"""Tests for PricingService (v3.1 Part F)."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app import models
from app.pricing import (
    PriceCache,
    PriceProvider,
    PriceProviderNoResult,
    PriceProviderRateLimited,
    PriceProviderUnavailable,
    PricingService,
    normalize_identity,
)
from app.schemas_llm import PriceEstimate, PriceSource
from app.settings import settings


def _estimate(median: float = 150.0, confidence: float = 0.85) -> PriceEstimate:
    return PriceEstimate(
        currency="USD",
        low=median * 0.8,
        median=median,
        high=median * 1.2,
        sample_count=5,
        sources=[
            PriceSource(
                title="Test",
                url="https://ebay.com/itm/1",
                price=median,
                condition="USED",
                source_site="ebay",
            )
        ],
        confidence=confidence,
    )


class _StubProvider(PriceProvider):
    """Simple stub that returns a canned estimate or raises."""

    def __init__(self, name: str, *, estimate=None, raises=None):
        self.name = name
        self._estimate = estimate
        self._raises = raises
        self.calls = 0

    async def lookup(self, identity):
        self.calls += 1
        if self._raises is not None:
            raise self._raises
        return self._estimate


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setattr(settings, "PRICING_ENABLED", True)
    monkeypatch.setattr(settings, "PRICING_PROVIDERS", ["ebay", "llm"])
    monkeypatch.setattr(settings, "PRICING_DAILY_COST_CAP_USD", 10.0)
    monkeypatch.setattr(settings, "PRICING_CACHE_DAYS", 14)


def _seed_item(db_session, user: models.User) -> models.Item:
    item = models.Item(
        name="Canon EOS R5",
        brand="Canon",
        model_number="EOS R5",
        owner_id=user.id,
    )
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)
    return item


def test_disabled_returns_503(db_session, user, monkeypatch):
    monkeypatch.setattr(settings, "PRICING_ENABLED", False)
    service = PricingService(db_session, user)
    with pytest.raises(HTTPException) as exc:
        service.estimate(metadata={"brand": "Canon"})
    assert exc.value.status_code == 503


def test_missing_input_raises_400(db_session, user):
    service = PricingService(
        db_session, user, providers=[_StubProvider("ebay", estimate=_estimate())]
    )
    with pytest.raises(HTTPException) as exc:
        service.estimate()
    assert exc.value.status_code == 400


def test_happy_path_runs_first_provider_and_caches(db_session, user):
    ebay = _StubProvider("ebay", estimate=_estimate(median=200.0))
    llm = _StubProvider("llm", estimate=_estimate(median=999.0))
    service = PricingService(db_session, user, providers=[ebay, llm])

    envelope = service.estimate(
        metadata={"brand": "Canon", "model_number": "EOS R5"}
    )
    assert envelope.estimate.median == 200.0
    assert envelope.provider == "ebay"
    assert envelope.cache_hit is False
    assert ebay.calls == 1
    assert llm.calls == 0  # short-circuited on ebay success

    # Re-running should hit the cache.
    envelope2 = service.estimate(
        metadata={"brand": "Canon", "model_number": "EOS R5"}
    )
    assert envelope2.cache_hit is True
    # Providers were not called again.
    assert ebay.calls == 1


def test_falls_back_to_next_provider_on_no_result(db_session, user):
    ebay = _StubProvider("ebay", raises=PriceProviderNoResult("empty"))
    llm = _StubProvider("llm", estimate=_estimate(median=300.0))
    service = PricingService(db_session, user, providers=[ebay, llm])

    envelope = service.estimate(
        metadata={"brand": "Canon", "model_number": "EOS R5"}
    )
    assert envelope.provider == "llm"
    assert envelope.estimate.median == 300.0
    assert ebay.calls == 1
    assert llm.calls == 1


def test_rate_limited_then_success_falls_through(db_session, user):
    ebay = _StubProvider("ebay", raises=PriceProviderRateLimited("429"))
    llm = _StubProvider("llm", estimate=_estimate(median=250.0))
    service = PricingService(db_session, user, providers=[ebay, llm])

    envelope = service.estimate(
        metadata={"brand": "Canon", "model_number": "EOS R5"}
    )
    assert envelope.provider == "llm"


def test_all_providers_fail_uses_stale_cache_when_available(db_session, user):
    """Cache a stale ebay entry, then have both providers fail."""
    identity = normalize_identity(
        {"brand": "Canon", "model_number": "EOS R5"}
    )
    cache = PriceCache(db_session)
    cache.set(identity.hash, "ebay", _estimate(median=200.0, confidence=0.9))
    # Rewind so it's past TTL.
    row = (
        db_session.query(models.PriceCache)
        .filter_by(identity_hash=identity.hash, provider="ebay")
        .one()
    )
    row.expires_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(
        days=1
    )
    row.created_at = row.expires_at - timedelta(days=settings.PRICING_CACHE_DAYS)
    db_session.commit()

    ebay = _StubProvider("ebay", raises=PriceProviderRateLimited("429"))
    llm = _StubProvider("llm", raises=PriceProviderUnavailable("down"))
    service = PricingService(db_session, user, providers=[ebay, llm])

    envelope = service.estimate(
        metadata={"brand": "Canon", "model_number": "EOS R5"},
        force_refresh=True,
    )
    assert envelope.cache_hit is True
    assert envelope.provider == "ebay"
    # Stale decay applied.
    assert envelope.estimate.confidence < 0.9


def test_all_providers_fail_no_stale_cache_raises_502(db_session, user):
    ebay = _StubProvider("ebay", raises=PriceProviderNoResult("nope"))
    llm = _StubProvider("llm", raises=PriceProviderUnavailable("down"))
    service = PricingService(db_session, user, providers=[ebay, llm])

    with pytest.raises(HTTPException) as exc:
        service.estimate(
            metadata={"brand": "Canon", "model_number": "EOS R5"}
        )
    assert exc.value.status_code == 502


def test_item_id_path_stamps_pricing_columns(db_session, user):
    item = _seed_item(db_session, user)
    ebay = _StubProvider("ebay", estimate=_estimate(median=250.0))
    service = PricingService(db_session, user, providers=[ebay])

    envelope = service.estimate(item_id=str(item.id))
    assert envelope.estimate.median == 250.0

    db_session.refresh(item)
    assert item.estimated_value_median == 250.0
    assert item.estimated_value_low == pytest.approx(200.0)
    assert item.estimated_value_high == pytest.approx(300.0)
    assert item.price_provider == "ebay"
    assert item.price_last_checked is not None


def test_item_id_404_when_cross_user(db_session, user):
    from app import security

    other = models.User(
        email="bob@example.com",
        username="bob",
        hashed_password=security.get_password_hash("x"),
        is_active=True,
    )
    db_session.add(other)
    db_session.commit()
    db_session.refresh(other)

    their_item = models.Item(
        name="X", owner_id=other.id, brand="Canon", model_number="EOS R5"
    )
    db_session.add(their_item)
    db_session.commit()

    service = PricingService(
        db_session, user, providers=[_StubProvider("ebay", estimate=_estimate())]
    )
    with pytest.raises(HTTPException) as exc:
        service.estimate(item_id=str(their_item.id))
    assert exc.value.status_code == 404


def test_force_refresh_bypasses_cache(db_session, user):
    """force_refresh=True should ignore a fresh cache entry."""
    identity = normalize_identity({"brand": "Canon", "model_number": "EOS R5"})
    PriceCache(db_session).set(
        identity.hash, "ebay", _estimate(median=100.0)
    )

    ebay = _StubProvider("ebay", estimate=_estimate(median=500.0))
    service = PricingService(db_session, user, providers=[ebay])

    envelope = service.estimate(
        metadata={"brand": "Canon", "model_number": "EOS R5"},
        force_refresh=True,
    )
    assert envelope.estimate.median == 500.0
    assert envelope.cache_hit is False
    assert ebay.calls == 1


def test_estimate_async_awaitable_inside_running_loop(db_session, user):
    """Regression for F8 (pre-push validation pass).

    ``PricingService.estimate`` used to call :func:`asyncio.run` internally
    at the provider boundary, which raises ``asyncio.run() cannot be called
    from a running event loop`` when the caller is already inside one —
    i.e. FastAPI's async ``_enqueue_or_run`` fallback path or an ARQ worker
    task. Ensure ``estimate_async`` can be awaited from a running loop
    without nesting ``asyncio.run``.
    """
    ebay = _StubProvider("ebay", estimate=_estimate(median=250.0))
    service = PricingService(db_session, user, providers=[ebay])

    async def inner():
        return await service.estimate_async(
            metadata={"brand": "Sony", "model_number": "A7 IV"},
        )

    envelope = asyncio.run(inner())
    assert envelope.estimate.median == 250.0
    assert envelope.provider == "ebay"
    assert ebay.calls == 1
