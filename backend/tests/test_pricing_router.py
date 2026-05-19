"""Tests for the pricing router (v3.1 Part F)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app import models
from app.main import app
from app.settings import settings


@pytest.fixture(autouse=True)
def _enabled(monkeypatch):
    monkeypatch.setattr(settings, "PRICING_ENABLED", True)
    monkeypatch.setattr(settings, "PRICING_PROVIDERS", ["ebay"])
    monkeypatch.setattr(settings, "LLM_BASE_URL", "https://openrouter.ai/api/v1")
    monkeypatch.setattr(settings, "LLM_API_KEY", "sk-test")


@pytest.fixture
def stub_arq_pool():
    pool = MagicMock()
    pool.close = AsyncMock(return_value=None)
    pool.enqueue_job = AsyncMock(return_value=MagicMock(job_id="pricing-stub"))
    app.state.arq = pool
    try:
        yield pool
    finally:
        app.state.arq = None


def _fake_envelope():
    from datetime import datetime, timezone

    from app.schemas_llm import (
        PriceEstimate,
        PriceEstimateEnvelope,
        PriceSource,
    )

    return PriceEstimateEnvelope(
        estimate=PriceEstimate(
            currency="USD",
            low=100.0,
            median=150.0,
            high=200.0,
            sample_count=5,
            sources=[
                PriceSource(
                    title="Test",
                    url="https://ebay.com/itm/1",
                    price=150.0,
                    source_site="ebay",
                )
            ],
            confidence=0.85,
        ),
        provider="ebay",
        prompt_version="",
        queried_at=datetime.now(timezone.utc),
        cache_hit=False,
    )


def _seed_item(db_session, user):
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


# ---------------------------------------------------------------------------
# POST /api/pricing/estimate
# ---------------------------------------------------------------------------


def test_estimate_returns_503_when_disabled(client, auth_headers, monkeypatch):
    monkeypatch.setattr(settings, "PRICING_ENABLED", False)
    resp = client.post(
        "/api/pricing/estimate",
        headers=auth_headers,
        json={"metadata": {"brand": "Canon"}},
    )
    assert resp.status_code == 503


def test_estimate_requires_one_of_inputs(client, auth_headers):
    resp = client.post("/api/pricing/estimate", headers=auth_headers, json={})
    assert resp.status_code == 400


def test_estimate_rejects_both_inputs(client, auth_headers):
    resp = client.post(
        "/api/pricing/estimate",
        headers=auth_headers,
        json={"item_id": "x", "metadata": {"brand": "y"}},
    )
    assert resp.status_code == 400


def test_estimate_enqueues_when_pool_active(
    client, auth_headers, stub_arq_pool, user
):
    """Fresh lookup (no cache) with pool active → 202 + JobReference."""
    resp = client.post(
        "/api/pricing/estimate",
        headers=auth_headers,
        json={"metadata": {"brand": "Canon", "model_number": "EOS R5"}},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"kind": "job", "job_id": "pricing-stub"}
    stub_arq_pool.enqueue_job.assert_awaited_once()
    call = stub_arq_pool.enqueue_job.await_args
    assert call.args[0] == "pricing_refresh"
    assert call.kwargs["user_id"] == str(user.id)
    assert call.kwargs["force_refresh"] is False


def test_estimate_sync_fallback_runs_service(
    client, auth_headers, user, db_session
):
    """Without a pool, the router awaits PricingService.estimate_async directly."""
    app.state.arq = None
    with patch(
        "app.routers.pricing.PricingService.estimate_async",
        new_callable=AsyncMock,
        return_value=_fake_envelope(),
    ) as mock_estimate:
        resp = client.post(
            "/api/pricing/estimate",
            headers=auth_headers,
            json={"metadata": {"brand": "Canon", "model_number": "EOS R5"}},
        )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "kind" not in body
    assert body["estimate"]["median"] == 150.0
    mock_estimate.assert_called_once()


def test_estimate_serves_cache_without_enqueuing(
    client, auth_headers, stub_arq_pool, user, db_session
):
    """A fresh cache hit short-circuits the router before any enqueue."""
    from app.pricing import PriceCache, normalize_identity
    from app.schemas_llm import PriceEstimate, PriceSource

    identity = normalize_identity({"brand": "Canon", "model_number": "EOS R5"})
    PriceCache(db_session).set(
        identity.hash,
        "ebay",
        PriceEstimate(
            currency="USD",
            low=90.0,
            median=120.0,
            high=150.0,
            sample_count=5,
            sources=[
                PriceSource(
                    title="Cached", url="https://ebay.com/itm/1", price=120.0
                )
            ],
            confidence=0.8,
        ),
    )

    resp = client.post(
        "/api/pricing/estimate",
        headers=auth_headers,
        json={"metadata": {"brand": "Canon", "model_number": "EOS R5"}},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # Sync-cache response, not a JobReference.
    assert "kind" not in body
    assert body["cache_hit"] is True
    assert body["estimate"]["median"] == 120.0
    stub_arq_pool.enqueue_job.assert_not_awaited()


# ---------------------------------------------------------------------------
# POST /api/pricing/refresh/{item_id}
# ---------------------------------------------------------------------------


def test_refresh_passes_force_refresh_to_worker(
    client, auth_headers, stub_arq_pool, user, db_session
):
    item = _seed_item(db_session, user)
    resp = client.post(
        f"/api/pricing/refresh/{item.id}", headers=auth_headers
    )
    assert resp.status_code == 200, resp.text
    stub_arq_pool.enqueue_job.assert_awaited_once()
    call = stub_arq_pool.enqueue_job.await_args
    assert call.kwargs["force_refresh"] is True
    assert call.kwargs["item_id"] == str(item.id)


# ---------------------------------------------------------------------------
# GET /api/pricing/estimate/{item_id}
# ---------------------------------------------------------------------------


def test_get_cached_estimate_uses_cache_when_available(
    client, auth_headers, user, db_session
):
    from app.pricing import PriceCache, normalize_identity
    from app.schemas_llm import PriceEstimate, PriceSource

    item = _seed_item(db_session, user)
    identity = normalize_identity(item)
    PriceCache(db_session).set(
        identity.hash,
        "ebay",
        PriceEstimate(
            currency="USD",
            low=90.0,
            median=120.0,
            high=150.0,
            sample_count=5,
            sources=[
                PriceSource(
                    title="Cached", url="https://ebay.com/itm/1", price=120.0
                )
            ],
            confidence=0.8,
        ),
    )

    app.state.arq = None
    resp = client.get(
        f"/api/pricing/estimate/{item.id}", headers=auth_headers
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["cache_hit"] is True
    assert body["estimate"]["median"] == 120.0
