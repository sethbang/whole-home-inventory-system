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
from app.services import llm_config as llm_config_service
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
    # The client constructor consults the effective-config cache for
    # response_healing (and other fields); drop any cache populated by
    # a previous test so per-test ``settings`` patches take effect.
    llm_config_service.invalidate_cache()
    yield
    llm_config_service.invalidate_cache()


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
    # Response-healing plugin is attached by default, nested under
    # extra_body so the OpenAI SDK doesn't reject the OpenRouter-only
    # kwarg. (F9 — pre-push validation regression.)
    extra_body = kwargs.get("extra_body", {})
    assert extra_body.get("plugins") == [{"id": "response-healing"}]
    # plugins must NEVER be a top-level kwarg — SDK raises TypeError.
    assert "plugins" not in kwargs
    # No web_search tool unless explicitly requested.
    assert "tools" not in kwargs
    assert "tools" not in extra_body


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
    assert "plugins" not in kwargs.get("extra_body", {})


def test_structured_completion_skips_plugins_for_non_openrouter(monkeypatch):
    # Venice / OpenAI / Ollama reject unknown body keys; the
    # response-healing plugin is OpenRouter-specific and must not be
    # attached even when the toggle is on.
    monkeypatch.setattr(settings, "LLM_BASE_URL", "https://api.venice.ai/api/v1")
    monkeypatch.setattr(settings, "LLM_RESPONSE_HEALING", True)
    client = OpenAICompatibleClient()
    assert client.provider != "openrouter"
    create = _install_stub(
        client,
        {"low": 1.0, "median": 2.0, "high": 3.0, "sample_count": 0, "sources": [], "confidence": 0.5, "currency": "USD"},
    )

    import asyncio

    asyncio.run(
        client.structured_completion(
            messages=[{"role": "user", "content": "x"}],
            schema=PRICE_ESTIMATE_SCHEMA,
        )
    )
    kwargs = create.await_args.kwargs
    assert "plugins" not in kwargs
    assert "plugins" not in kwargs.get("extra_body", {})


def test_chat_completion_attaches_web_search_tool():
    """The ``chat_completion`` method is the web_search entry point.

    ``structured_completion`` no longer accepts web_search — see the
    F10a fix: OR's web_search middleware mangles nested objects in
    structured-output responses, so pricing uses a two-call flow
    (web_search chat_completion → schema-only structured_completion).
    """
    client = OpenAICompatibleClient()
    # chat_completion returns text, not JSON — install a text stub.
    from unittest.mock import AsyncMock

    resp = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content="some grounded analysis text"),
                finish_reason="stop",
            )
        ],
        usage=SimpleNamespace(
            prompt_tokens=100, completion_tokens=50, total_tokens=150
        ),
    )
    create = AsyncMock(return_value=resp)
    client._client.chat = SimpleNamespace(completions=SimpleNamespace(create=create))

    import asyncio

    result = asyncio.run(
        client.chat_completion(
            messages=[{"role": "user", "content": "price it"}],
            use_web_search=True,
            extra_search_params={"max_results": 2},
        )
    )

    assert result["text"] == "some grounded analysis text"
    # OpenRouter-type tools live under extra_body (F9), not top-level.
    kwargs = create.await_args.kwargs
    assert "tools" not in kwargs
    tools = kwargs["extra_body"]["tools"]
    assert len(tools) == 1
    assert tools[0]["type"] == "openrouter:web_search"
    # max_results override from extra_search_params wins over settings default.
    assert tools[0]["parameters"]["max_results"] == 2
    # max_total_results from settings applies.
    assert "max_total_results" in tools[0]["parameters"]
    # chat_completion never sends response_format — that's the whole point
    # of the two-call split (F10a).
    assert "response_format" not in kwargs


def test_structured_completion_strips_provider_unsupported_constraints():
    """Pydantic emits ``minimum``/``maximum``/``pattern`` constraints that
    Anthropic-via-Azure (and possibly others) reject with 400. The client
    strips these from the json_schema before sending; strictness still
    applies on our side at ``model_validate`` time.
    """
    client = OpenAICompatibleClient()
    create = _install_stub(
        client,
        {"low": 1.0, "median": 2.0, "high": 3.0, "sample_count": 0,
         "sources": [], "confidence": 0.5, "currency": "USD"},
    )

    import asyncio

    asyncio.run(
        client.structured_completion(
            messages=[{"role": "user", "content": "x"}],
            schema=PRICE_ESTIMATE_SCHEMA,
        )
    )

    sent_schema = create.await_args.kwargs["response_format"]["json_schema"]["schema"]

    def _walk(node):
        if isinstance(node, dict):
            for k, v in node.items():
                assert k not in {
                    "minimum",
                    "maximum",
                    "exclusiveMinimum",
                    "exclusiveMaximum",
                    "minLength",
                    "maxLength",
                    "minItems",
                    "maxItems",
                    "pattern",
                    "format",
                    "multipleOf",
                }, f"found forbidden schema key {k!r} in outgoing payload"
                _walk(v)
        elif isinstance(node, list):
            for v in node:
                _walk(v)

    _walk(sent_schema)


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


def test_parse_response_surfaces_provider_error_envelope():
    """OR returns 200 OK with `{error: {message, code}, choices: null}`
    when an upstream (e.g. Anthropic-via-Azure) hits a 524 timeout. The
    OpenAI SDK deserializes this as a ChatCompletion with choices=None
    — naive parsers TypeError on `choices[0]`. Defensive parser must
    detect the error envelope and raise LLMProviderError with the
    upstream message, never crash to 500.
    """
    client = OpenAICompatibleClient()
    create = AsyncMock(
        return_value=SimpleNamespace(
            choices=None,
            usage=None,
            error={"message": "Provider returned error", "code": 524},
        )
    )
    client._client.chat = SimpleNamespace(
        completions=SimpleNamespace(create=create)
    )

    import asyncio

    with pytest.raises(LLMProviderError) as exc:
        asyncio.run(
            client.structured_completion(
                messages=[{"role": "user", "content": "x"}],
                schema=VISION_SUGGESTION_SCHEMA,
            )
        )
    msg = str(exc.value)
    assert "524" in msg
    assert "Provider returned error" in msg


def test_parse_response_handles_null_choices_without_error():
    """Defense-in-depth: if `choices` is None but no error envelope
    accompanies it, still raise cleanly instead of TypeError-crashing.
    """
    client = OpenAICompatibleClient()
    create = AsyncMock(
        return_value=SimpleNamespace(
            choices=None,
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
