"""Tests for the v3.1 pricing providers.

eBay Browse: exercised via httpx.MockTransport so we assert the OAuth
round-trip, query shape, and aggregation end-to-end without touching
the network. LLM provider: exercised with a stub OpenAICompatibleClient.
"""

from __future__ import annotations

import json
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from app.pricing import (
    EbayBrowseProvider,
    ItemIdentity,
    LLMPricingProvider,
    PriceProviderNoResult,
    PriceProviderRateLimited,
    PriceProviderUnavailable,
    normalize_identity,
)
from app.settings import settings


# ---------------------------------------------------------------------------
# eBay Browse provider
# ---------------------------------------------------------------------------


def _ebay_identity() -> ItemIdentity:
    return normalize_identity(
        {"brand": "Canon", "model_number": "EOS R5", "condition": "used good"}
    )


def _mock_transport(responses: Dict[str, httpx.Response]) -> httpx.MockTransport:
    """Return a MockTransport that dispatches by URL substring."""

    def handler(request: httpx.Request) -> httpx.Response:
        for needle, response in responses.items():
            if needle in str(request.url):
                return response
        return httpx.Response(500, text=f"no mock for {request.url}")

    return httpx.MockTransport(handler)


def _oauth_ok() -> httpx.Response:
    return httpx.Response(
        200,
        json={"access_token": "test-token", "expires_in": 7200},
    )


@pytest.fixture(autouse=True)
def _ebay_env(monkeypatch):
    monkeypatch.setattr(settings, "EBAY_APP_ID", "app-id")
    monkeypatch.setattr(settings, "EBAY_CERT_ID", "cert-id")
    monkeypatch.setattr(settings, "EBAY_MARKETPLACE_ID", "EBAY_US")
    monkeypatch.setattr(settings, "EBAY_ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "PRICING_MAX_SAMPLES", 30)


def test_ebay_lookup_happy_path():
    """Full round-trip: OAuth → search → aggregate."""
    listings = {
        "itemSummaries": [
            {
                "title": "Canon EOS R5 body (used)",
                "itemWebUrl": "https://ebay.com/itm/1",
                "price": {"value": "2400.00", "currency": "USD"},
                "condition": "Used",
            },
            {
                "title": "Canon EOS R5 body with grip",
                "itemWebUrl": "https://ebay.com/itm/2",
                "price": {"value": "2600.00", "currency": "USD"},
                "condition": "Used - Excellent",
            },
            {
                "title": "Canon EOS R5 w/ lens kit",
                "itemWebUrl": "https://ebay.com/itm/3",
                "price": {"value": "2800.00", "currency": "USD"},
                "condition": "Used",
            },
        ]
    }
    transport = _mock_transport(
        {
            "/identity/v1/oauth2/token": _oauth_ok(),
            "/buy/browse/v1/item_summary/search": httpx.Response(200, json=listings),
        }
    )

    import asyncio

    async def run():
        http = httpx.AsyncClient(transport=transport)
        provider = EbayBrowseProvider(http=http)
        try:
            return await provider.lookup(_ebay_identity())
        finally:
            await http.aclose()

    estimate = asyncio.run(run())
    assert estimate.currency == "USD"
    assert estimate.sample_count == 3
    assert 2400.0 <= estimate.low <= estimate.median <= estimate.high <= 2800.0
    assert len(estimate.sources) == 3


def test_ebay_missing_credentials_returns_unavailable(monkeypatch):
    monkeypatch.setattr(settings, "EBAY_APP_ID", "")
    import asyncio

    async def run():
        http = httpx.AsyncClient(transport=_mock_transport({}))
        try:
            provider = EbayBrowseProvider(http=http)
            await provider.lookup(_ebay_identity())
        finally:
            await http.aclose()

    with pytest.raises(PriceProviderUnavailable):
        asyncio.run(run())


def test_ebay_429_on_search_raises_rate_limited():
    transport = _mock_transport(
        {
            "/identity/v1/oauth2/token": _oauth_ok(),
            "/buy/browse/v1/item_summary/search": httpx.Response(429, text="Too Many"),
        }
    )
    import asyncio

    async def run():
        http = httpx.AsyncClient(transport=transport)
        try:
            provider = EbayBrowseProvider(http=http)
            await provider.lookup(_ebay_identity())
        finally:
            await http.aclose()

    with pytest.raises(PriceProviderRateLimited):
        asyncio.run(run())


def test_ebay_empty_results_raises_no_result():
    transport = _mock_transport(
        {
            "/identity/v1/oauth2/token": _oauth_ok(),
            "/buy/browse/v1/item_summary/search": httpx.Response(
                200, json={"itemSummaries": []}
            ),
        }
    )
    import asyncio

    async def run():
        http = httpx.AsyncClient(transport=transport)
        try:
            provider = EbayBrowseProvider(http=http)
            await provider.lookup(_ebay_identity())
        finally:
            await http.aclose()

    with pytest.raises(PriceProviderNoResult):
        asyncio.run(run())


def test_ebay_filters_zero_priced_items():
    """Best-Offer listings with price=0 shouldn't pollute the aggregate."""
    listings = {
        "itemSummaries": [
            {
                "title": "Real listing",
                "itemWebUrl": "https://ebay.com/itm/1",
                "price": {"value": "1000.00"},
                "condition": "Used",
            },
            {
                "title": "Best offer placeholder",
                "itemWebUrl": "https://ebay.com/itm/2",
                "price": {"value": "0"},
                "condition": "Used",
            },
        ]
    }
    transport = _mock_transport(
        {
            "/identity/v1/oauth2/token": _oauth_ok(),
            "/buy/browse/v1/item_summary/search": httpx.Response(200, json=listings),
        }
    )
    import asyncio

    async def run():
        http = httpx.AsyncClient(transport=transport)
        try:
            provider = EbayBrowseProvider(http=http)
            return await provider.lookup(_ebay_identity())
        finally:
            await http.aclose()

    estimate = asyncio.run(run())
    assert estimate.sample_count == 1
    assert estimate.median == 1000.0


def test_ebay_empty_query_raises_no_result():
    transport = _mock_transport({"/identity/v1/oauth2/token": _oauth_ok()})
    import asyncio

    async def run():
        http = httpx.AsyncClient(transport=transport)
        try:
            provider = EbayBrowseProvider(http=http)
            # Blank identity — no brand/model/name.
            await provider.lookup(normalize_identity({}))
        finally:
            await http.aclose()

    with pytest.raises(PriceProviderNoResult):
        asyncio.run(run())


def test_ebay_token_cache_skips_second_oauth():
    """Back-to-back lookups reuse the cached token."""
    call_count = {"oauth": 0, "search": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if "/oauth2/token" in str(request.url):
            call_count["oauth"] += 1
            return _oauth_ok()
        call_count["search"] += 1
        return httpx.Response(
            200,
            json={
                "itemSummaries": [
                    {
                        "title": "x",
                        "itemWebUrl": "https://ebay.com/itm/1",
                        "price": {"value": "100"},
                        "condition": "Used",
                    }
                ]
            },
        )

    import asyncio

    async def run():
        http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        try:
            provider = EbayBrowseProvider(http=http)
            await provider.lookup(_ebay_identity())
            await provider.lookup(_ebay_identity())
        finally:
            await http.aclose()

    asyncio.run(run())
    assert call_count["oauth"] == 1
    assert call_count["search"] == 2


# ---------------------------------------------------------------------------
# LLM pricing provider
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _llm_env(monkeypatch):
    monkeypatch.setattr(settings, "LLM_BASE_URL", "https://openrouter.ai/api/v1")
    monkeypatch.setattr(settings, "LLM_API_KEY", "sk-test")
    monkeypatch.setattr(settings, "LLM_PRICING_MODEL", "anthropic/claude-sonnet-4.6")


def _stub_llm_client(estimate_payload: dict, *, web_search_count: int = 2):
    """Build a minimal OpenAICompatibleClient stand-in.

    The provider uses a two-call flow (F10a fix): chat_completion with
    web_search ON returns grounded text; structured_completion with
    schema ON extracts the strict estimate. This stub wires both.
    """
    client = MagicMock()
    client.chat_completion = AsyncMock(
        return_value={
            "text": "Grounded analysis: low $1 median $2 high $3 etc.",
            "usage": {
                "prompt_tokens": 800,
                "completion_tokens": 400,
                "total_tokens": 1200,
                "server_tool_use": {"web_search_requests": web_search_count},
            },
            "provider": "openrouter",
            "queried_at": None,
            "raw": None,
        }
    )
    client.structured_completion = AsyncMock(
        return_value={
            "data": estimate_payload,
            "usage": {
                "prompt_tokens": 500,
                "completion_tokens": 200,
                "total_tokens": 700,
            },
            "provider": "openrouter",
            "queried_at": None,
        }
    )
    return client


def test_llm_provider_happy_path_runs_two_call_flow():
    payload = {
        "currency": "USD",
        "low": 2300.0,
        "median": 2500.0,
        "high": 2700.0,
        "sample_count": 6,
        "sources": [
            {
                "title": "Canon EOS R5 sold Apr 2026",
                "url": "https://ebay.com/itm/42",
                "price": 2500.0,
                "condition": "USED",
                "sold_date": "2026-04-10",
                "source_site": "ebay",
            }
        ],
        "confidence": 0.82,
    }
    client = _stub_llm_client(payload)
    provider = LLMPricingProvider(client=client)

    import asyncio

    estimate = asyncio.run(provider.lookup(_ebay_identity()))
    assert estimate.median == 2500.0
    assert estimate.confidence == 0.82

    # Call 1: chat_completion with web_search=True, correct model.
    client.chat_completion.assert_awaited_once()
    call1 = client.chat_completion.await_args
    assert call1.kwargs["use_web_search"] is True
    assert call1.kwargs["model"] == "anthropic/claude-sonnet-4.6"

    # Call 2: structured_completion (no web_search kwarg at all) with the
    # strict schema.
    client.structured_completion.assert_awaited_once()
    call2 = client.structured_completion.await_args
    assert "use_web_search" not in call2.kwargs
    assert call2.kwargs["model"] == "anthropic/claude-sonnet-4.6"
    # Extraction prompt must carry the research text into the user turn.
    user_turn = [m for m in call2.kwargs["messages"] if m["role"] == "user"][0]
    assert "Grounded analysis" in user_turn["content"]

    # Merged usage from both calls is stashed for the service to read.
    assert provider.last_usage["prompt_tokens"] == 800 + 500
    assert provider.last_usage["completion_tokens"] == 400 + 200
    assert provider.last_usage["server_tool_use"]["web_search_requests"] == 2


def test_llm_provider_requires_llm_config(monkeypatch):
    monkeypatch.setattr(settings, "LLM_BASE_URL", "")
    provider = LLMPricingProvider()

    import asyncio

    with pytest.raises(PriceProviderUnavailable):
        asyncio.run(provider.lookup(_ebay_identity()))


def test_llm_provider_no_result_when_model_returns_empty_aggregate():
    payload = {
        "currency": "USD",
        "low": 0,
        "median": 0,
        "high": 0,
        "sample_count": 0,
        "sources": [],
        "confidence": 0.0,
    }
    client = _stub_llm_client(payload, web_search_count=0)
    provider = LLMPricingProvider(client=client)

    import asyncio

    with pytest.raises(PriceProviderNoResult):
        asyncio.run(provider.lookup(_ebay_identity()))


def test_llm_provider_surfaces_schema_violations():
    """If the model returns JSON that violates PriceEstimate, we raise."""
    bad_payload = {
        "currency": "USD",
        "low": 100.0,
        # missing median / high — required fields.
        "sample_count": 1,
        "sources": [],
        "confidence": 0.5,
    }
    client = _stub_llm_client(bad_payload)
    provider = LLMPricingProvider(client=client)

    import asyncio

    from app.pricing import PriceProviderError

    with pytest.raises(PriceProviderError):
        asyncio.run(provider.lookup(_ebay_identity()))
