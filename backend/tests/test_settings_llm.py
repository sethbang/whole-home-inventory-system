"""Fail-fast coverage for the v3.1 LLM settings gates."""

from __future__ import annotations

import pytest

from app.settings import Settings, _is_private_llm_host


def _env(**overrides):
    """Baseline env that passes the auth gate."""
    base = {
        "BYPASS_AUTH": "false",
        "SECRET_KEY": "ci-secret-key-not-a-placeholder-0000000000000",
        "LOG_LEVEL": "WARNING",
    }
    base.update(overrides)
    return base


def test_vision_enabled_without_llm_base_url_refuses_startup(monkeypatch):
    for k, v in _env(VISION_ENABLED="true", LLM_BASE_URL="").items():
        monkeypatch.setenv(k, v)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="LLM_BASE_URL"):
        Settings()


def test_pricing_enabled_without_api_key_refuses_startup(monkeypatch):
    env = _env(
        PRICING_ENABLED="true",
        LLM_BASE_URL="https://openrouter.ai/api/v1",
        LLM_API_KEY="",
    )
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    with pytest.raises(RuntimeError, match="LLM_API_KEY"):
        Settings()


def test_llm_allow_cloud_false_blocks_public_host(monkeypatch):
    env = _env(
        VISION_ENABLED="false",
        PRICING_ENABLED="false",
        LLM_BASE_URL="https://openrouter.ai/api/v1",
        LLM_API_KEY="sk-test",
        LLM_ALLOW_CLOUD="false",
    )
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    with pytest.raises(RuntimeError, match="LLM_ALLOW_CLOUD"):
        Settings()


def test_llm_allow_cloud_false_accepts_localhost(monkeypatch):
    env = _env(
        LLM_BASE_URL="http://localhost:11434/v1",
        LLM_API_KEY="sk-test",
        LLM_ALLOW_CLOUD="false",
    )
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    # Should not raise.
    settings_obj = Settings()
    assert settings_obj.LLM_ALLOW_CLOUD is False


def test_llm_allow_cloud_false_accepts_private_ip(monkeypatch):
    env = _env(
        LLM_BASE_URL="http://192.168.1.50:11434/v1",
        LLM_API_KEY="sk-test",
        LLM_ALLOW_CLOUD="false",
    )
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    settings_obj = Settings()
    assert settings_obj.LLM_ALLOW_CLOUD is False


def test_pricing_providers_splits_csv(monkeypatch):
    env = _env(
        PRICING_ENABLED="true",
        LLM_BASE_URL="https://openrouter.ai/api/v1",
        LLM_API_KEY="sk-test",
        PRICING_PROVIDERS="ebay,llm,etsy",
    )
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    settings_obj = Settings()
    assert settings_obj.PRICING_PROVIDERS == ["ebay", "llm", "etsy"]


def test_pricing_model_falls_back_to_vision_model(monkeypatch):
    env = _env(
        PRICING_ENABLED="true",
        LLM_BASE_URL="https://openrouter.ai/api/v1",
        LLM_API_KEY="sk-test",
        LLM_MODEL="some-model",
        LLM_PRICING_MODEL="",
    )
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    settings_obj = Settings()
    assert settings_obj.pricing_model() == "some-model"


@pytest.mark.parametrize(
    "url,expected",
    [
        ("http://localhost:11434/v1", True),
        ("http://127.0.0.1:11434/v1", True),
        ("http://10.0.0.5/v1", True),
        ("http://172.16.0.1/v1", True),
        ("http://192.168.1.50/v1", True),
        ("http://ollama:11434/v1", True),
        ("http://host.docker.internal:11434/v1", True),
        ("https://openrouter.ai/api/v1", False),
        ("https://api.openai.com/v1", False),
        ("https://api.venice.ai/api/v1", False),
        ("http://8.8.8.8/v1", False),
    ],
)
def test_is_private_llm_host(url: str, expected: bool):
    assert _is_private_llm_host(url) is expected
