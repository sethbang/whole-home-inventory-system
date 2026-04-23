"""Tests for the vision router (v3.1 Part C)."""

from __future__ import annotations

import io
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from PIL import Image as PILImage

from app.main import app
from app.settings import settings


def _png() -> bytes:
    img = PILImage.new("RGB", (64, 64), color=(80, 140, 220))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def _enabled(monkeypatch):
    monkeypatch.setattr(settings, "VISION_ENABLED", True)
    monkeypatch.setattr(settings, "LLM_BASE_URL", "https://openrouter.ai/api/v1")
    monkeypatch.setattr(settings, "LLM_API_KEY", "sk-test")


@pytest.fixture
def stub_arq_pool():
    pool = MagicMock()
    pool.close = AsyncMock(return_value=None)
    job = MagicMock(job_id="vision-stub-1")
    pool.enqueue_job = AsyncMock(return_value=job)
    app.state.arq = pool
    try:
        yield pool
    finally:
        app.state.arq = None


def test_503_when_feature_disabled(client, auth_headers, monkeypatch):
    monkeypatch.setattr(settings, "VISION_ENABLED", False)
    resp = client.post(
        "/api/vision/identify",
        headers=auth_headers,
        files={"files": ("a.png", _png(), "image/png")},
    )
    assert resp.status_code == 503


def test_400_when_no_files(client, auth_headers, _enabled):
    resp = client.post("/api/vision/identify", headers=auth_headers, files=[])
    assert resp.status_code in {400, 422}


def test_400_when_too_many_images(client, auth_headers, _enabled, monkeypatch):
    monkeypatch.setattr(settings, "VISION_MAX_IMAGES_PER_REQUEST", 2)
    files = [("files", (f"img{i}.png", _png(), "image/png")) for i in range(3)]
    resp = client.post("/api/vision/identify", headers=auth_headers, files=files)
    assert resp.status_code == 400
    assert "max is 2" in resp.json()["detail"].lower()


def test_400_when_hints_is_not_json(client, auth_headers, _enabled):
    resp = client.post(
        "/api/vision/identify",
        headers=auth_headers,
        files={"files": ("a.png", _png(), "image/png")},
        data={"hints": "not {json"},
    )
    assert resp.status_code == 400
    assert "hints" in resp.json()["detail"].lower()


def test_enqueues_when_pool_active(client, auth_headers, _enabled, stub_arq_pool, user):
    resp = client.post(
        "/api/vision/identify",
        headers=auth_headers,
        files={"files": ("a.png", _png(), "image/png")},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body == {"kind": "job", "job_id": "vision-stub-1"}

    stub_arq_pool.enqueue_job.assert_awaited_once()
    call = stub_arq_pool.enqueue_job.await_args
    assert call.args[0] == "vision_identify"
    assert call.kwargs["user_id"] == str(user.id)
    # Images arrive as base64 strings.
    assert len(call.kwargs["images_b64"]) == 1
    assert isinstance(call.kwargs["images_b64"][0], str)


def test_sync_fallback_runs_service_inline(client, auth_headers, _enabled, user, db_session):
    """Without a pool, the router calls VisionService directly."""
    app.state.arq = None

    fake_result_data = {
        "suggestion": {
            "name": "Canon EOS R5",
            "confidence": 0.88,
            "warnings": [],
            "suggested_tags": [],
            "ebay_item_specifics": {},
            "fb_item_specifics": {},
        },
        "provider": "openrouter",
        "model": "google/gemini-2.5-flash",
        "prompt_version": "v3.1.0",
        "tokens_in": 120,
        "tokens_out": 50,
        "cost_usd_estimate": 0.001,
        "queried_at": "2026-04-23T00:00:00Z",
    }

    from app.schemas_llm import VisionResult

    with patch(
        "app.routers.vision.VisionService.identify_async",
        new_callable=AsyncMock,
        return_value=VisionResult.model_validate(fake_result_data),
    ) as mock_identify:
        resp = client.post(
            "/api/vision/identify",
            headers=auth_headers,
            files={"files": ("a.png", _png(), "image/png")},
        )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["suggestion"]["name"] == "Canon EOS R5"
    mock_identify.assert_called_once()


def test_enqueue_failure_falls_back_to_sync(client, auth_headers, _enabled, user, db_session):
    pool = MagicMock()
    pool.close = AsyncMock(return_value=None)
    pool.enqueue_job = AsyncMock(side_effect=RuntimeError("redis down"))
    app.state.arq = pool

    from app.schemas_llm import VisionResult

    fake_result_data = {
        "suggestion": {
            "confidence": 0.5,
            "warnings": [],
            "suggested_tags": [],
            "ebay_item_specifics": {},
            "fb_item_specifics": {},
        },
        "provider": "openrouter",
        "model": "google/gemini-2.5-flash",
        "prompt_version": "v3.1.0",
        "tokens_in": 0,
        "tokens_out": 0,
        "cost_usd_estimate": 0.0,
        "queried_at": "2026-04-23T00:00:00Z",
    }

    try:
        with patch(
            "app.routers.vision.VisionService.identify_async",
            new_callable=AsyncMock,
            return_value=VisionResult.model_validate(fake_result_data),
        ):
            resp = client.post(
                "/api/vision/identify",
                headers=auth_headers,
                files={"files": ("a.png", _png(), "image/png")},
            )
    finally:
        app.state.arq = None

    assert resp.status_code == 200, resp.text
    body = resp.json()
    # Sync path — no `kind` discriminator.
    assert "kind" not in body
    assert "suggestion" in body
