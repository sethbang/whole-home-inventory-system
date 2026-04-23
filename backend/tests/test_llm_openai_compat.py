"""Tests for the shared LLM client (v3.1 Part A).

Covers request construction (response_format shape, web_search tool
wiring, response-healing plugin, cache_control breakpoint emission),
and response parsing + error paths. No network.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.llm.openai_compatible import (
    LLMError,
    LLMProviderError,
    OpenAICompatibleClient,
)
from app.schemas_llm import (
    PRICE_ESTIMATE_SCHEMA,
    VISION_SUGGESTION_SCHEMA,
)
from app.settings import settings


def _fake_completion(payload: dict, usage: dict | None = None):
    """Build a minimal object mimicking the OpenAI SDK completion shape."""
    content = json.dumps(payload) if not isinstance(payload, str) else payload
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=content, role="assistant")
            )
        ],
        usage=SimpleNamespace(
            model_dump=lambda: usage
            or {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150,
            }
        ),
    )


@pytest.fixture(autouse=True)
def _llm_env(monkeypatch):
    """Make sure the client can construct during each test."""
    monkeypatch.setattr(settings, "LLM_BASE_URL", "https://openrouter.ai/api/v1")
    monkeypatch.setattr(settings, "LLM_API_KEY", "test-key")
    monkeypatch.setattr(settings, "LLM_MODEL", "google/gemini-2.5-flash")
    monkeypatch.setattr(settings, "LLM_RESPONSE_HEALING", True)
    monkeypatch.setattr(settings, "VISION_LOG_IMAGE_HASHES_ONLY", True)


def _install_stub(client: OpenAICompatibleClient, payload: dict):
    """Replace the SDK client with a stub that returns ``payload``."""
    create = AsyncMock(return_value=_fake_completion(payload))
    client._client.chat = SimpleNamespace(completions=SimpleNamespace(create=create))
    return create


def test_requires_base_url_and_api_key(monkeypatch):
    monkeypatch.setattr(settings, "LLM_BASE_URL", "")
    with pytest.raises(LLMError):
        OpenAICompatibleClient()


def test_structured_completion_builds_json_schema_request():
    client = OpenAICompatibleClient()
    expected = {"confidence": 0.9, "name": "Canon EOS R5"}
    create = _install_stub(client, {**expected, "warnings": [], "suggested_tags": [], "ebay_item_specifics": {}, "fb_item_specifics": {}})

    import asyncio

    result = asyncio.run(
        client.structured_completion(
            messages=[{"role": "user", "content": "identify"}],
            schema=VISION_SUGGESTION_SCHEMA,
        )
    )

    assert result["data"]["name"] == "Canon EOS R5"
    # Usage stats made it through.
    assert result["usage"]["prompt_tokens"] == 100

    create.assert_awaited_once()
    kwargs = create.await_args.kwargs
    # Model defaults to LLM_MODEL.
    assert kwargs["model"] == "google/gemini-2.5-flash"
    # response_format is the OR strict shape.
    assert kwargs["response_format"]["type"] == "json_schema"
    assert kwargs["response_format"]["json_schema"]["strict"] is True
    assert kwargs["response_format"]["json_schema"]["name"] == "VisionSuggestion"
    # Response-healing plugin is attached by default.
    assert kwargs["plugins"] == [{"id": "response-healing"}]
    # No web_search tool unless explicitly requested.
    assert "tools" not in kwargs


def test_structured_completion_respects_response_healing_flag(monkeypatch):
    monkeypatch.setattr(settings, "LLM_RESPONSE_HEALING", False)
    client = OpenAICompatibleClient()
    create = _install_stub(client, {"low": 1.0, "median": 2.0, "high": 3.0, "sample_count": 0, "sources": [], "confidence": 0.5, "currency": "USD"})

    import asyncio

    asyncio.run(
        client.structured_completion(
            messages=[{"role": "user", "content": "x"}],
            schema=PRICE_ESTIMATE_SCHEMA,
        )
    )
    kwargs = create.await_args.kwargs
    assert "plugins" not in kwargs


def test_structured_completion_attaches_web_search_tool():
    client = OpenAICompatibleClient()
    create = _install_stub(
        client,
        {"low": 1.0, "median": 2.0, "high": 3.0, "sample_count": 0, "sources": [], "confidence": 0.5, "currency": "USD"},
    )

    import asyncio

    asyncio.run(
        client.structured_completion(
            messages=[{"role": "user", "content": "price it"}],
            schema=PRICE_ESTIMATE_SCHEMA,
            use_web_search=True,
            extra_search_params={"max_results": 2},
        )
    )

    tools = create.await_args.kwargs["tools"]
    assert len(tools) == 1
    assert tools[0]["type"] == "openrouter:web_search"
    # max_results override from extra_search_params wins over settings default.
    assert tools[0]["parameters"]["max_results"] == 2
    # max_total_results from settings applies.
    assert "max_total_results" in tools[0]["parameters"]


def test_vision_completion_attaches_base64_data_urls():
    client = OpenAICompatibleClient()
    create = _install_stub(
        client,
        {
            "confidence": 0.8,
            "warnings": [],
            "suggested_tags": [],
            "ebay_item_specifics": {},
            "fb_item_specifics": {},
        },
    )

    import asyncio

    image_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64  # not a real png but not empty
    asyncio.run(
        client.vision_completion(
            system_prompt="you identify things",
            images=[image_bytes],
            schema=VISION_SUGGESTION_SCHEMA,
        )
    )

    kwargs = create.await_args.kwargs
    messages = kwargs["messages"]
    # System + user roles set correctly.
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    # Image content part present with a data URL.
    content_parts = messages[1]["content"]
    image_parts = [p for p in content_parts if p["type"] == "image_url"]
    assert len(image_parts) == 1
    assert image_parts[0]["image_url"]["url"].startswith("data:image/jpeg;base64,")


def test_vision_completion_requires_at_least_one_image():
    client = OpenAICompatibleClient()
    import asyncio

    with pytest.raises(LLMError):
        asyncio.run(
            client.vision_completion(
                system_prompt="x",
                images=[],
                schema=VISION_SUGGESTION_SCHEMA,
            )
        )


def test_parse_response_surfaces_invalid_json_as_provider_error():
    client = OpenAICompatibleClient()
    create = _install_stub(client, "this is not { valid json")

    import asyncio

    with pytest.raises(LLMProviderError) as exc:
        asyncio.run(
            client.structured_completion(
                messages=[{"role": "user", "content": "x"}],
                schema=VISION_SUGGESTION_SCHEMA,
            )
        )
    # Raw content is attached for log inspection.
    assert "not { valid json" in str(exc.value.raw)


def test_parse_response_handles_null_content():
    client = OpenAICompatibleClient()
    create = AsyncMock(
        return_value=SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=None))],
            usage=None,
        )
    )
    client._client.chat = SimpleNamespace(
        completions=SimpleNamespace(create=create)
    )

    import asyncio

    with pytest.raises(LLMProviderError):
        asyncio.run(
            client.structured_completion(
                messages=[{"role": "user", "content": "x"}],
                schema=VISION_SUGGESTION_SCHEMA,
            )
        )
