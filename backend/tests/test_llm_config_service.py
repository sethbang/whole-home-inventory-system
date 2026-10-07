"""Tests for app.services.llm_config."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app import security_crypto
from app.services import llm_config as svc


@pytest.fixture(autouse=True)
def _clear_cache():
    """Every test starts with a clean module cache."""
    svc.invalidate_cache()
    yield
    svc.invalidate_cache()


@pytest.fixture
def env_defaults():
    """Force a known set of env defaults so tests don't depend on whatever
    pytest config set up. Matches the v3.1 baseline values."""
    with patch.multiple(
        svc.settings,
        LLM_BASE_URL="",
        LLM_API_KEY="",
        LLM_MODEL="google/gemini-2.5-flash",
        LLM_VISION_MODEL="",
        LLM_PRICING_MODEL="",
        LLM_TIMEOUT_SECONDS=90,
        LLM_RESPONSE_HEALING=True,
        VISION_ENABLED=False,
        PRICING_ENABLED=False,
        VISION_DAILY_COST_CAP_USD=5.0,
        PRICING_DAILY_COST_CAP_USD=5.0,
        LLM_ALLOW_CLOUD=True,
    ):
        yield


def test_effective_with_no_db_row_uses_env(db_session, env_defaults) -> None:
    eff = svc.get_effective_for_db(db_session)
    assert eff.base_url == ""
    assert eff.api_key == ""
    assert eff.model == "google/gemini-2.5-flash"
    # vision/pricing fall back to model when their override env is empty
    assert eff.vision_model == "google/gemini-2.5-flash"
    assert eff.pricing_model == "google/gemini-2.5-flash"
    assert eff.timeout_seconds == 90
    assert eff.response_healing is True
    assert eff.vision_enabled is False
    assert eff.vision_daily_cap_usd == 5.0
    assert eff.sources["api_key"] == "default"
    assert eff.sources["vision_model"] == "default"


def test_db_row_overrides_env(db_session, env_defaults) -> None:
    with patch.object(svc.settings, "LLM_BASE_URL", "https://env.example/api/v1"):
        svc.apply_update(
            db_session,
            {
                "base_url": "https://openrouter.ai/api/v1",
                "model": "google/gemini-3-flash-preview",
                "timeout_seconds": 30,
                "vision_daily_cap_usd": 12.5,
            },
            actor=None,
            api_key="sk-or-secret-1234",
        )
        eff = svc.get_effective_for_db(db_session)
    assert eff.base_url == "https://openrouter.ai/api/v1"
    assert eff.api_key == "sk-or-secret-1234"
    assert eff.model == "google/gemini-3-flash-preview"
    assert eff.timeout_seconds == 30
    assert eff.vision_daily_cap_usd == 12.5
    assert eff.sources["base_url"] == "db"
    assert eff.sources["api_key"] == "db"


def test_clearing_field_falls_back_to_env(db_session, env_defaults) -> None:
    with patch.object(svc.settings, "LLM_BASE_URL", "https://env.example/api/v1"):
        svc.apply_update(
            db_session,
            {"base_url": "https://override.example/api/v1"},
            api_key="abc",
        )
        # Clearing with empty string -> reverts to env
        svc.apply_update(db_session, {"base_url": ""})
        eff = svc.get_effective_for_db(db_session)
    assert eff.base_url == "https://env.example/api/v1"
    assert eff.sources["base_url"] == "env"


def test_clearing_api_key_falls_back_to_env(db_session, env_defaults) -> None:
    with patch.object(svc.settings, "LLM_API_KEY", "env-key-value"):
        svc.apply_update(db_session, {}, api_key="db-key-value")
        assert svc.get_effective_for_db(db_session).api_key == "db-key-value"
        svc.apply_update(db_session, {}, clear_api_key=True)
        eff = svc.get_effective_for_db(db_session)
    assert eff.api_key == "env-key-value"
    assert eff.sources["api_key"] == "env"


def test_api_key_is_encrypted_at_rest(db_session, env_defaults) -> None:
    svc.apply_update(db_session, {}, api_key="plaintext-secret-zzz")
    row = svc.load_db_row(db_session)
    assert row is not None
    assert row.api_key_ciphertext is not None
    assert "plaintext-secret-zzz" not in row.api_key_ciphertext
    # Round-trip through the crypto helper.
    assert security_crypto.decrypt(row.api_key_ciphertext) == "plaintext-secret-zzz"


def test_cache_invalidates_on_update(db_session, env_defaults) -> None:
    """apply_update must drop the module cache so subsequent reads see
    the new value. Validated via get_effective_for_db so the test
    isn't sensitive to which DB SessionLocal points at."""
    svc.apply_update(db_session, {"model": "model-a"}, api_key="k")
    # Prime the cache by hand so the next read would hit it if the
    # invalidation logic were broken.
    svc._cache = svc.get_effective_for_db(db_session)
    assert svc._cache is not None and svc._cache.model == "model-a"
    svc.apply_update(db_session, {"model": "model-b"})
    assert svc._cache is None
    eff2 = svc.get_effective_for_db(db_session)
    assert eff2.model == "model-b"


def test_invalid_field_rejected(db_session, env_defaults) -> None:
    with pytest.raises(svc.ConfigUpdateError):
        svc.apply_update(db_session, {"not_a_field": "x"})


def test_negative_cap_rejected(db_session, env_defaults) -> None:
    with pytest.raises(svc.ConfigUpdateError):
        svc.apply_update(db_session, {"vision_daily_cap_usd": -1.0})


def test_invalid_timeout_rejected(db_session, env_defaults) -> None:
    with pytest.raises(svc.ConfigUpdateError):
        svc.apply_update(db_session, {"timeout_seconds": 0})
    with pytest.raises(svc.ConfigUpdateError):
        svc.apply_update(db_session, {"timeout_seconds": 9999})


def test_privacy_guard_rejects_public_url_when_allow_cloud_false(
    db_session, env_defaults
) -> None:
    with patch.object(svc.settings, "LLM_ALLOW_CLOUD", False):
        with pytest.raises(svc.ConfigUpdateError):
            svc.apply_update(
                db_session, {"base_url": "https://openrouter.ai/api/v1"}
            )
        # localhost is allowed.
        svc.apply_update(db_session, {"base_url": "http://localhost:11434/v1"})
        eff = svc.get_effective_for_db(db_session)
    assert eff.base_url == "http://localhost:11434/v1"


def test_actor_recorded(db_session, env_defaults, user) -> None:
    svc.apply_update(db_session, {"model": "x"}, actor=user)
    row = svc.load_db_row(db_session)
    assert row is not None
    assert row.updated_by == user.id


def test_set_and_clear_api_key_simultaneously_rejected(
    db_session, env_defaults
) -> None:
    with pytest.raises(svc.ConfigUpdateError):
        svc.apply_update(
            db_session, {}, api_key="abc", clear_api_key=True
        )


def test_garbled_ciphertext_falls_back_to_env(db_session, env_defaults) -> None:
    """Simulate a SECRET_KEY rotation: stored ciphertext can no longer decrypt."""
    svc.apply_update(db_session, {}, api_key="will-be-orphaned")
    row = svc.load_db_row(db_session)
    assert row is not None
    # Tamper with the ciphertext so decrypt() raises.
    row.api_key_ciphertext = "definitely-not-a-valid-fernet-token"
    db_session.commit()
    svc.invalidate_cache()
    with patch.object(svc.settings, "LLM_API_KEY", "env-fallback-key"):
        eff = svc.get_effective_for_db(db_session)
    assert eff.api_key == "env-fallback-key"
    assert eff.sources["api_key"] == "env"
