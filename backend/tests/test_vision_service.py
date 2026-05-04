"""Tests for VisionService (v3.1 Part C).

A fake OpenAICompatibleClient stand-in exercises the happy path,
bad-schema response handling, and the interaction with the budget
guard. No network.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from PIL import Image as PILImage
import io

from app import models
from app.schemas_llm import VisionResult, VisionSuggestion
from app.settings import settings
from app.vision import VisionService


def _png(size=(64, 64)) -> bytes:
    img = PILImage.new("RGB", size, color=(200, 200, 200))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setattr(settings, "VISION_ENABLED", True)
    monkeypatch.setattr(settings, "VISION_MAX_IMAGES_PER_REQUEST", 4)
    monkeypatch.setattr(settings, "VISION_DAILY_COST_CAP_USD", 10.0)
    monkeypatch.setattr(settings, "LLM_BASE_URL", "https://openrouter.ai/api/v1")
    monkeypatch.setattr(settings, "LLM_API_KEY", "sk-test")
    monkeypatch.setattr(settings, "LLM_MODEL", "google/gemini-2.5-flash")
    # F12 introduced LLM_VISION_MODEL with a fallback to LLM_MODEL via
    # settings.vision_model(). Pin to "" so these tests exercise the
    # fallback regardless of what backend/.env happens to set.
    monkeypatch.setattr(settings, "LLM_VISION_MODEL", "")


def _fake_client(payload: dict, usage: dict | None = None, *, raises=None):
    """Build a stand-in OpenAICompatibleClient.

    We only need the interface the service calls — `provider` and
    `vision_completion` (async). Real client is never instantiated.
    """
    client = MagicMock()
    client.provider = "openrouter"
    if raises is not None:
        client.vision_completion = AsyncMock(side_effect=raises)
    else:
        client.vision_completion = AsyncMock(
            return_value={
                "data": payload,
                "usage": usage or {
                    "prompt_tokens": 200,
                    "completion_tokens": 100,
                    "total_tokens": 300,
                },
                "provider": "openrouter",
                "queried_at": None,
            }
        )
    return client


def test_identify_happy_path_records_usage(db_session, user):
    client = _fake_client(
        {
            "name": "Canon EOS R5",
            "brand": "Canon",
            "confidence": 0.9,
            "warnings": [],
            "suggested_tags": ["camera"],
            "ebay_item_specifics": {},
            "fb_item_specifics": {},
        }
    )

    service = VisionService(db_session, user)
    result = service.identify([_png()], client=client)

    assert isinstance(result, VisionResult)
    assert result.suggestion.name == "Canon EOS R5"
    assert result.suggestion.brand == "Canon"
    assert result.model == "google/gemini-2.5-flash"
    assert result.tokens_in == 200
    assert result.tokens_out == 100
    assert result.cost_usd_estimate > 0

    # Budget row was stamped.
    usage_row = (
        db_session.query(models.LLMUsage)
        .filter_by(user_id=user.id, feature="vision")
        .one()
    )
    assert usage_row.request_count == 1
    assert usage_row.tokens_in == 200


def test_identify_rejects_when_feature_disabled(db_session, user, monkeypatch):
    monkeypatch.setattr(settings, "VISION_ENABLED", False)
    service = VisionService(db_session, user)
    with pytest.raises(HTTPException) as exc:
        service.identify([_png()], client=_fake_client({}))
    assert exc.value.status_code == 503


def test_identify_rejects_empty_images(db_session, user):
    service = VisionService(db_session, user)
    with pytest.raises(HTTPException) as exc:
        service.identify([], client=_fake_client({}))
    assert exc.value.status_code == 400


def test_identify_rejects_too_many_images(db_session, user, monkeypatch):
    monkeypatch.setattr(settings, "VISION_MAX_IMAGES_PER_REQUEST", 2)
    service = VisionService(db_session, user)
    with pytest.raises(HTTPException) as exc:
        service.identify(
            [_png(), _png(), _png()], client=_fake_client({})
        )
    assert exc.value.status_code == 400
    assert "max is 2" in exc.value.detail.lower()


def test_identify_enforces_budget_cap(db_session, user, monkeypatch):
    """When the user has already hit today's cap, refuse before calling the LLM."""
    monkeypatch.setattr(settings, "VISION_DAILY_COST_CAP_USD", 0.001)
    # Pre-seed an over-cap row for today.
    from app.llm.budget import DailyBudgetGuard

    DailyBudgetGuard(db_session, user).record_usage(
        "vision",
        model="anthropic/claude-sonnet-4.6",
        usage={"prompt_tokens": 1_000_000, "completion_tokens": 100_000},
    )

    client = _fake_client({"confidence": 0.9, "warnings": [], "suggested_tags": [], "ebay_item_specifics": {}, "fb_item_specifics": {}})
    service = VisionService(db_session, user)
    with pytest.raises(HTTPException) as exc:
        service.identify([_png()], client=client)
    assert exc.value.status_code == 402
    # LLM was never called.
    client.vision_completion.assert_not_called()


def test_identify_surfaces_provider_parse_error_as_502(db_session, user):
    """LLMProviderError means the model returned garbage — 502, not 500."""
    from app.llm import LLMProviderError

    client = _fake_client(
        {}, raises=LLMProviderError("bad json", raw="garbage")
    )
    service = VisionService(db_session, user)
    with pytest.raises(HTTPException) as exc:
        service.identify([_png()], client=client)
    assert exc.value.status_code == 502
    # Even the failed call counts as a request (just with zero tokens) so
    # operators can see something tried.
    row = (
        db_session.query(models.LLMUsage)
        .filter_by(user_id=user.id, feature="vision")
        .one()
    )
    assert row.request_count == 1


def test_identify_surfaces_schema_violation_as_502(db_session, user):
    """Model returned JSON but confidence was out of range — flag as 502."""
    client = _fake_client(
        {
            # confidence must be 0..1; 42 is outside the range.
            "confidence": 42,
            "warnings": [],
            "suggested_tags": [],
            "ebay_item_specifics": {},
            "fb_item_specifics": {},
        }
    )
    service = VisionService(db_session, user)
    with pytest.raises(HTTPException) as exc:
        service.identify([_png()], client=client)
    assert exc.value.status_code == 502


def test_identify_async_awaitable_inside_running_loop(db_session, user):
    """Regression for F8 (pre-push validation pass).

    ``VisionService.identify`` used to call :func:`asyncio.run` internally,
    which raises ``asyncio.run() cannot be called from a running event loop``
    when the caller is already inside one — i.e. FastAPI's async route
    handler or an ARQ worker task. Ensure ``identify_async`` can be awaited
    from a running loop without nesting ``asyncio.run``.
    """
    client = _fake_client(
        {
            "name": "Test",
            "brand": None,
            "category": None,
            "confidence": 0.5,
            "warnings": [],
            "suggested_tags": [],
            "ebay_item_specifics": {},
            "fb_item_specifics": {},
        }
    )

    async def inner():
        service = VisionService(db_session, user)
        return await service.identify_async([_png()], client=client)

    result = asyncio.run(inner())
    assert isinstance(result, VisionResult)
    assert result.suggestion.name == "Test"
