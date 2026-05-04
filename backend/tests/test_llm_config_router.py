"""Tests for /api/llm-config router (v3.2)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app import models, security, security_crypto
from app.services import llm_config as svc


@pytest.fixture(autouse=True)
def _reset_cache():
    svc.invalidate_cache()
    yield
    svc.invalidate_cache()


@pytest.fixture
def admin_user(db_session) -> models.User:
    user = models.User(
        email="admin@example.com",
        username="admin",
        hashed_password=security.get_password_hash("hunter2-correct-staple"),
        is_active=True,
        is_admin=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_headers(admin_user) -> dict[str, str]:
    token = security.create_access_token(data={"sub": admin_user.username})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def non_admin_user(db_session) -> models.User:
    user = models.User(
        email="bob@example.com",
        username="bob",
        hashed_password=security.get_password_hash("hunter2-correct-staple"),
        is_active=True,
        is_admin=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def non_admin_headers(non_admin_user) -> dict[str, str]:
    token = security.create_access_token(data={"sub": non_admin_user.username})
    return {"Authorization": f"Bearer {token}"}


# ---- Auth gating ---------------------------------------------------------


def test_get_requires_auth(client) -> None:
    response = client.get("/api/llm-config")
    assert response.status_code == 401


def test_non_admin_user_gets_403(client, non_admin_headers) -> None:
    response = client.get("/api/llm-config", headers=non_admin_headers)
    assert response.status_code == 403
    assert "admin" in response.json()["detail"].lower()


def test_non_admin_cannot_put(client, non_admin_headers) -> None:
    response = client.put(
        "/api/llm-config", json={"model": "x"}, headers=non_admin_headers
    )
    assert response.status_code == 403


# ---- GET / PUT round trip ------------------------------------------------


def test_get_returns_env_defaults_when_db_empty(client, admin_headers) -> None:
    response = client.get("/api/llm-config", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["api_key_set"] is False
    assert body["api_key_last4"] is None
    assert body["model"]  # always populated; default lives in env
    assert "today_vision_cost_usd" in body
    assert "sources" in body


def test_put_persists_and_reflects_in_get(client, admin_headers) -> None:
    response = client.put(
        "/api/llm-config",
        json={
            "base_url": "https://openrouter.ai/api/v1",
            "api_key": "sk-or-test-abcd1234",
            "model": "google/gemini-2.5-flash",
            "vision_daily_cap_usd": 7.5,
            "response_healing": False,
        },
        headers=admin_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["api_key_set"] is True
    assert body["api_key_last4"] == "1234"
    assert body["base_url"] == "https://openrouter.ai/api/v1"
    assert body["vision_daily_cap_usd"] == 7.5
    assert body["response_healing"] is False
    assert body["sources"]["base_url"] == "db"


def test_put_encrypts_key_at_rest(client, admin_headers, db_session) -> None:
    response = client.put(
        "/api/llm-config",
        json={"api_key": "plaintext-secret-7777"},
        headers=admin_headers,
    )
    assert response.status_code == 200
    row = svc.load_db_row(db_session)
    assert row is not None
    assert row.api_key_ciphertext is not None
    assert "plaintext-secret-7777" not in row.api_key_ciphertext
    assert security_crypto.decrypt(row.api_key_ciphertext) == "plaintext-secret-7777"


def test_put_clears_key_with_empty_string(client, admin_headers, db_session) -> None:
    client.put(
        "/api/llm-config",
        json={"api_key": "a-key-that-will-be-cleared"},
        headers=admin_headers,
    )
    response = client.put(
        "/api/llm-config", json={"api_key": ""}, headers=admin_headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body["api_key_set"] is False
    row = svc.load_db_row(db_session)
    assert row is not None and row.api_key_ciphertext is None


def test_put_invalid_field_400(client, admin_headers) -> None:
    """Pydantic rejects unknown fields if extra='forbid' is set, but
    LLMConfigUpdate doesn't forbid extras — verify the service layer
    catches negative caps instead."""
    response = client.put(
        "/api/llm-config",
        json={"vision_daily_cap_usd": -5.0},
        headers=admin_headers,
    )
    assert response.status_code == 400


def test_put_privacy_guard(client, admin_headers) -> None:
    with patch.object(svc.settings, "LLM_ALLOW_CLOUD", False):
        response = client.put(
            "/api/llm-config",
            json={"base_url": "https://openrouter.ai/api/v1"},
            headers=admin_headers,
        )
    assert response.status_code == 400
    assert "private" in response.json()["detail"].lower()


# ---- GET /models ---------------------------------------------------------


_VENICE_RESPONSE = {
    "object": "list",
    "type": "text",
    "data": [
        {
            "id": "llama-3.2-3b",
            "owned_by": "venice.ai",
            "model_spec": {
                "capabilities": {
                    "supportsVision": False,
                    "supportsResponseSchema": True,
                }
            },
        },
        {
            "id": "qwen2.5-vl",
            "owned_by": "venice.ai",
            "model_spec": {
                "capabilities": {
                    "supportsVision": True,
                    "supportsResponseSchema": True,
                }
            },
        },
    ],
}


class _MockResponse:
    def __init__(self, status_code: int, body):
        self.status_code = status_code
        self._body = body
        self.text = "" if isinstance(body, dict) else str(body)

    def json(self):
        return self._body


def _patch_httpx(response):
    """Patch httpx.AsyncClient.get to return a fixed response."""
    return patch(
        "httpx.AsyncClient.get",
        new=AsyncMock(return_value=response),
    )


def test_models_endpoint_annotates_capabilities(client, admin_headers) -> None:
    # Persist enough config to satisfy "base_url + key required".
    client.put(
        "/api/llm-config",
        json={"base_url": "https://api.venice.ai/api/v1", "api_key": "vk-abc"},
        headers=admin_headers,
    )
    with _patch_httpx(_MockResponse(200, _VENICE_RESPONSE)):
        response = client.get("/api/llm-config/models", headers=admin_headers)
    assert response.status_code == 200, response.text
    body = response.json()
    by_id = {m["id"]: m for m in body["models"]}
    assert by_id["llama-3.2-3b"]["supports_vision"] is False
    assert by_id["llama-3.2-3b"]["supports_strict_json"] is True
    assert by_id["qwen2.5-vl"]["supports_vision"] is True
    assert by_id["qwen2.5-vl"]["supports_strict_json"] is True


def test_models_endpoint_provider_401_surfaces(client, admin_headers) -> None:
    client.put(
        "/api/llm-config",
        json={"base_url": "https://api.example/api/v1", "api_key": "bad-key"},
        headers=admin_headers,
    )
    with _patch_httpx(_MockResponse(401, {"error": "invalid_key"})):
        response = client.get("/api/llm-config/models", headers=admin_headers)
    assert response.status_code == 401


def test_models_endpoint_no_credentials_400(client, admin_headers) -> None:
    """When neither DB nor env supplies a base_url, /models 400s."""
    with patch.multiple(svc.settings, LLM_BASE_URL="", LLM_API_KEY=""):
        svc.invalidate_cache()
        response = client.get("/api/llm-config/models", headers=admin_headers)
    assert response.status_code == 400


# ---- POST /test (quick) --------------------------------------------------


def test_quick_test_passes_when_models_listed(client, admin_headers) -> None:
    # Wipe env-supplied vision/pricing model overrides so they default to
    # the configured ``model`` instead of inheriting from .env.
    with patch.multiple(
        svc.settings, LLM_VISION_MODEL="", LLM_PRICING_MODEL=""
    ):
        svc.invalidate_cache()
        client.put(
            "/api/llm-config",
            json={
                "base_url": "https://api.venice.ai/api/v1",
                "api_key": "vk-abc",
                "model": "qwen2.5-vl",
            },
            headers=admin_headers,
        )
        with _patch_httpx(_MockResponse(200, _VENICE_RESPONSE)):
            response = client.post(
                "/api/llm-config/test", headers=admin_headers
            )
    body = response.json()
    assert response.status_code == 200, body
    assert body["ok"] is True, body
    assert body["checks"]["model_present"] is True


def test_quick_test_fails_when_model_missing(client, admin_headers) -> None:
    client.put(
        "/api/llm-config",
        json={
            "base_url": "https://api.venice.ai/api/v1",
            "api_key": "vk-abc",
            "model": "nonexistent-model",
        },
        headers=admin_headers,
    )
    with _patch_httpx(_MockResponse(200, _VENICE_RESPONSE)):
        response = client.post("/api/llm-config/test", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert "nonexistent-model" in body["detail"]


def test_quick_test_with_inline_payload_does_not_persist(
    client, admin_headers, db_session
) -> None:
    """POST body should be used for validation, not persisted."""
    with _patch_httpx(_MockResponse(200, _VENICE_RESPONSE)):
        response = client.post(
            "/api/llm-config/test",
            json={
                "base_url": "https://api.venice.ai/api/v1",
                "api_key": "ephemeral-key",
                "model": "qwen2.5-vl",
            },
            headers=admin_headers,
        )
    assert response.status_code == 200
    assert response.json()["ok"] is True
    # The DB row shouldn't carry the ephemeral key.
    row = svc.load_db_row(db_session)
    if row is not None:
        assert row.api_key_ciphertext is None


# ---- POST /test-vision (deep) --------------------------------------------


def test_deep_test_records_usage(client, admin_headers, db_session, admin_user) -> None:
    client.put(
        "/api/llm-config",
        json={
            "base_url": "https://api.example/api/v1",
            "api_key": "vk-deep",
            "model": "vision-test-model",
        },
        headers=admin_headers,
    )

    fake_result = {
        "data": {"ok": True, "description": "a small red square"},
        "usage": {"prompt_tokens": 50, "completion_tokens": 8, "total_tokens": 58},
        "provider": "example",
        "queried_at": None,
    }

    with patch(
        "app.routers.llm_config.OpenAICompatibleClient",
        autospec=True,
    ) as mock_client_cls:
        mock_client = mock_client_cls.return_value
        mock_client.vision_completion = AsyncMock(return_value=fake_result)
        response = client.post(
            "/api/llm-config/test-vision", headers=admin_headers
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["ok"] is True
    assert body["parsed_response"] == {
        "ok": True,
        "description": "a small red square",
    }
    assert body["usage"]["prompt_tokens"] == 50

    # An LLMUsage row tagged feature="config_test" was stamped.
    rows = (
        db_session.query(models.LLMUsage)
        .filter(models.LLMUsage.user_id == admin_user.id)
        .filter(models.LLMUsage.feature == "config_test")
        .all()
    )
    assert len(rows) == 1
    assert rows[0].request_count == 1
    assert rows[0].tokens_in == 50


def test_deep_test_second_run_same_day_accumulates_into_existing_row(
    client, admin_headers, db_session, admin_user
) -> None:
    """Two test-vision calls on the same UTC day must upsert, not crash.

    ``llm_usage`` has UNIQUE(user_id, usage_date, feature); a blind
    INSERT on the second call would raise IntegrityError 500. Regression
    test for the duplicate-row crash an operator hit re-running the
    Vision test against Venice after the first run already stamped a
    ``config_test`` row for today.
    """
    client.put(
        "/api/llm-config",
        json={
            "base_url": "https://api.example/api/v1",
            "api_key": "vk-deep",
            "model": "vision-test-model",
        },
        headers=admin_headers,
    )
    fake_result = {
        "data": {"ok": True, "description": "fixture"},
        "usage": {"prompt_tokens": 50, "completion_tokens": 8, "total_tokens": 58},
        "provider": "example",
        "queried_at": None,
    }

    with patch(
        "app.routers.llm_config.OpenAICompatibleClient", autospec=True
    ) as mock_client_cls:
        mock_client = mock_client_cls.return_value
        mock_client.vision_completion = AsyncMock(return_value=fake_result)
        first = client.post("/api/llm-config/test-vision", headers=admin_headers)
        second = client.post("/api/llm-config/test-vision", headers=admin_headers)

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text

    rows = (
        db_session.query(models.LLMUsage)
        .filter(models.LLMUsage.user_id == admin_user.id)
        .filter(models.LLMUsage.feature == "config_test")
        .all()
    )
    assert len(rows) == 1
    assert rows[0].request_count == 2
    assert rows[0].tokens_in == 100
    assert rows[0].tokens_out == 16


def test_deep_test_failure_surfaces_clean_message(client, admin_headers) -> None:
    client.put(
        "/api/llm-config",
        json={
            "base_url": "https://api.example/api/v1",
            "api_key": "vk-deep",
            "model": "vision-test-model",
        },
        headers=admin_headers,
    )
    from app.llm import LLMProviderError

    with patch(
        "app.routers.llm_config.OpenAICompatibleClient", autospec=True
    ) as mock_client_cls:
        mock_client = mock_client_cls.return_value
        mock_client.vision_completion = AsyncMock(
            side_effect=LLMProviderError("model returned text/plain")
        )
        response = client.post(
            "/api/llm-config/test-vision", headers=admin_headers
        )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert "unparseable" in body["detail"].lower()


def test_deep_test_no_credentials(client, admin_headers) -> None:
    with patch.multiple(svc.settings, LLM_BASE_URL="", LLM_API_KEY=""):
        svc.invalidate_cache()
        response = client.post(
            "/api/llm-config/test-vision", headers=admin_headers
        )
    body = response.json()
    assert response.status_code == 200
    assert body["ok"] is False
    assert "must both be set" in body["detail"]


# ---- Admin promotion -----------------------------------------------------


def test_first_registered_user_is_admin(client) -> None:
    response = client.post(
        "/api/register",
        json={
            "email": "first@example.com",
            "username": "first",
            "password": "hunter2-correct-staple",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["is_admin"] is True


def test_subsequent_registrations_are_not_admin(client) -> None:
    client.post(
        "/api/register",
        json={
            "email": "first@example.com",
            "username": "first",
            "password": "hunter2-correct-staple",
        },
    )
    response = client.post(
        "/api/register",
        json={
            "email": "second@example.com",
            "username": "second",
            "password": "hunter2-correct-staple",
        },
    )
    assert response.status_code == 200
    assert response.json()["is_admin"] is False
