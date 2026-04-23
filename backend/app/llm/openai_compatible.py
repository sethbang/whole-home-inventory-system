"""OpenAI-compatible LLM client (v3.1).

One adapter, pluggable by ``LLM_BASE_URL`` + ``LLM_API_KEY`` + model
name. Works with:

* OpenRouter (``https://openrouter.ai/api/v1``) — canonical target.
  Supports structured outputs, the response-healing plugin, and the
  ``openrouter:web_search`` server tool.
* Venice.ai, LocalAI, Ollama's ``/v1`` — same surface; server tools
  and plugins degrade (structured outputs still work on most).
* Raw OpenAI (``https://api.openai.com/v1``) — structured outputs
  supported since gpt-4o; no OR-specific plugins.

The two public methods are:

* :meth:`structured_completion` — text-only chat with
  ``response_format: json_schema`` strict mode. Optional
  ``use_web_search=True`` attaches OR's server tool. Returns a dict.
* :meth:`vision_completion` — multipart messages carrying image parts
  (base64 data URLs). Same structured-output guarantees.

Retries via ``tenacity`` on 429 / 5xx. Per-call timeout from
``settings.LLM_TIMEOUT_SECONDS``. All network I/O is async.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urlparse

from openai import APIError, AsyncOpenAI, AuthenticationError, RateLimitError
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ..settings import settings

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Base exception for the LLM layer."""


class LLMProviderError(LLMError):
    """Raised when the provider returned a response we can't parse.

    Carries the raw content and usage stats so the caller can log
    them for debugging even though the structured decode failed.
    """

    def __init__(self, message: str, *, raw: Any = None) -> None:
        super().__init__(message)
        self.raw = raw


def _derive_provider_name(base_url: str) -> str:
    """Short identifier for logging / usage attribution.

    ``https://openrouter.ai/api/v1`` → ``openrouter``;
    ``http://ollama:11434/v1`` → ``ollama``.
    """
    if not base_url:
        return "unconfigured"
    host = urlparse(base_url).hostname or "unknown"
    # Strip the first label if it's obviously a subdomain.
    parts = host.split(".")
    if len(parts) >= 2 and parts[0] in {"api", "www"}:
        return parts[1]
    return parts[0]


def _image_to_data_url(image_bytes: bytes, mime: str = "image/jpeg") -> str:
    b64 = base64.b64encode(image_bytes).decode("ascii")
    return f"data:{mime};base64,{b64}"


def _image_hash(image_bytes: bytes) -> str:
    return hashlib.sha256(image_bytes).hexdigest()


class OpenAICompatibleClient:
    """Thin wrapper around the OpenAI async SDK.

    Configured once at request time. Callers that need per-process
    caching should build a singleton themselves — we keep this
    stateless so tests can swap the underlying client freely.
    """

    def __init__(
        self,
        *,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
    ) -> None:
        self.base_url = base_url or settings.LLM_BASE_URL
        self.api_key = api_key or settings.LLM_API_KEY
        self.timeout_seconds = timeout_seconds or settings.LLM_TIMEOUT_SECONDS
        self.provider = _derive_provider_name(self.base_url)

        if not self.base_url or not self.api_key:
            raise LLMError(
                "OpenAICompatibleClient requires LLM_BASE_URL + LLM_API_KEY"
            )

        self._client = AsyncOpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            timeout=self.timeout_seconds,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def structured_completion(
        self,
        *,
        messages: List[Dict[str, Any]],
        schema: Dict[str, Any],
        model: Optional[str] = None,
        use_web_search: bool = False,
        extra_search_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Ask the model for a schema-valid JSON object.

        ``schema`` is the dict shape OpenRouter's ``response_format``
        expects — ``{"name", "strict", "schema"}``. See
        :mod:`app.schemas_llm` for the canonical constants.

        Returns ``{"data": <parsed JSON>, "usage": {...}}``. Raises
        :class:`LLMProviderError` when the response can't be parsed
        even after the response-healing plugin has its turn.
        """
        model_name = model or settings.LLM_MODEL
        body: Dict[str, Any] = {
            "model": model_name,
            "messages": messages,
            "response_format": {
                "type": "json_schema",
                "json_schema": schema,
            },
        }

        if use_web_search:
            search_params: Dict[str, Any] = {
                "max_results": settings.PRICING_WEB_SEARCH_MAX_RESULTS,
                "max_total_results": settings.PRICING_WEB_SEARCH_MAX_TOTAL,
            }
            if settings.PRICING_WEB_SEARCH_DOMAINS:
                search_params["allowed_domains"] = list(
                    settings.PRICING_WEB_SEARCH_DOMAINS
                )
            if extra_search_params:
                search_params.update(extra_search_params)
            body["tools"] = [
                {"type": "openrouter:web_search", "parameters": search_params}
            ]

        if settings.LLM_RESPONSE_HEALING:
            body["plugins"] = [{"id": "response-healing"}]

        response = await self._with_retry(body)
        return self._parse_response(response)

    async def vision_completion(
        self,
        *,
        system_prompt: str,
        images: Iterable[bytes],
        hints: Optional[Dict[str, Any]] = None,
        schema: Dict[str, Any],
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Structured completion with one or more image attachments.

        ``images`` is an iterable of raw bytes; the method base64-encodes
        them into data URLs. Each image is logged by sha256 hash only
        when ``VISION_LOG_IMAGE_HASHES_ONLY`` is set (the default).
        """
        user_content: List[Dict[str, Any]] = []
        hash_list: List[str] = []
        for image_bytes in images:
            hash_list.append(_image_hash(image_bytes))
            user_content.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": _image_to_data_url(image_bytes),
                        "detail": "high",
                    },
                }
            )
        if hints:
            user_content.append(
                {
                    "type": "text",
                    "text": f"User hints (may be empty): {json.dumps(hints, sort_keys=True)}",
                }
            )
        if not user_content:
            raise LLMError("vision_completion called with no images")

        if settings.VISION_LOG_IMAGE_HASHES_ONLY:
            logger.info(
                "vision_completion hashes=%s images=%d",
                hash_list,
                len(hash_list),
            )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]
        return await self.structured_completion(
            messages=messages, schema=schema, model=model
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    async def _with_retry(self, body: Dict[str, Any]) -> Any:
        """POST chat.completions with backoff on 429 / 5xx."""
        # Retry only on transient errors. AuthenticationError /
        # validation errors fail fast so the operator sees the real
        # problem on the first try.
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type((RateLimitError, APIError)),
            reraise=True,
        ):
            with attempt:
                try:
                    return await self._client.chat.completions.create(**body)
                except AuthenticationError:
                    # Don't retry auth failures — the key isn't going to
                    # start working on its own.
                    raise
                except (RateLimitError, APIError):
                    raise
        # Unreachable but keeps mypy happy.
        raise LLMError("retry exhausted without a response")

    @staticmethod
    def _parse_response(response: Any) -> Dict[str, Any]:
        """Pull the JSON body out of a chat.completions response.

        OR returns ``response.choices[0].message.content`` as a string
        that should already be schema-valid JSON (thanks to strict
        mode + response healing). We json.loads it and surface the
        raw content on failure.
        """
        try:
            content = response.choices[0].message.content
        except (AttributeError, IndexError) as exc:
            raise LLMProviderError(
                "LLM response had no choices/message", raw=response
            ) from exc
        if content is None:
            raise LLMProviderError("LLM response content was null", raw=response)
        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            # Final defense: response-healing already had its shot. If
            # we still can't parse, surface the raw content to the
            # caller for logging — don't silently swallow.
            raise LLMProviderError(
                f"LLM response was not valid JSON: {exc}", raw=content
            ) from exc

        usage = _usage_dict(getattr(response, "usage", None))
        return {
            "data": data,
            "usage": usage,
            "provider": _derive_provider_name(""),
            "queried_at": datetime.now(timezone.utc),
        }


def _usage_dict(usage: Any) -> Dict[str, Any]:
    """Convert the SDK's usage object to a plain dict.

    OR returns ``prompt_tokens``, ``completion_tokens``, ``total_tokens``
    and (when the web_search tool fires) a nested
    ``server_tool_use.web_search_requests`` counter.
    """
    if usage is None:
        return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    try:
        out = usage.model_dump()
    except AttributeError:
        # Plain dict on some providers.
        out = dict(usage) if isinstance(usage, dict) else {}
    out.setdefault("prompt_tokens", 0)
    out.setdefault("completion_tokens", 0)
    out.setdefault("total_tokens", 0)
    return out
