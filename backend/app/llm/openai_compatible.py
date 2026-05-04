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

The three public methods are:

* :meth:`structured_completion` — chat with ``response_format:
  json_schema`` strict mode. Does NOT accept web_search — see
  ``chat_completion`` for why. Returns ``{"data", "usage", ...}``.
* :meth:`chat_completion` — natural-language chat, optionally with
  the ``openrouter:web_search`` server tool. Returns ``{"text",
  "usage", ...}``. Callers that want grounded structured output must
  orchestrate a two-call flow (web_search here → structured extract
  via ``structured_completion``), because OR's web_search middleware
  mangles nested objects in structured-output responses by wrapping
  them in a stringified ``{completionState, entries, type}``
  envelope. Splitting the calls sidesteps the middleware path.
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

from ..services import llm_config as llm_config_service
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


# JSON-schema numeric / string constraints that some providers (notably
# Anthropic via Azure) reject with 400 "For 'number' type, property
# 'minimum' is not supported". Pydantic emits these from Field(ge=...,
# le=..., min_length=..., pattern=...). The strictness still applies on
# our side at .model_validate() time, so hiding them from the provider
# costs nothing.
_SCHEMA_STRIP_KEYS = frozenset(
    {
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
    }
)


def _strip_schema_constraints(node: Any) -> Any:
    """Recursively drop provider-unsupported constraint keys.

    See ``_SCHEMA_STRIP_KEYS`` for the rationale. Returns a new
    structure; the input is not mutated.
    """
    if isinstance(node, dict):
        return {
            k: _strip_schema_constraints(v)
            for k, v in node.items()
            if k not in _SCHEMA_STRIP_KEYS
        }
    if isinstance(node, list):
        return [_strip_schema_constraints(v) for v in node]
    return node


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
        response_healing: Optional[bool] = None,
    ) -> None:
        # When the caller doesn't supply explicit values, fall back to
        # the operator-editable config (DB row + env fallback). This is
        # what makes UI-driven config changes go live without a restart.
        if (
            base_url is None
            or api_key is None
            or timeout_seconds is None
            or response_healing is None
        ):
            try:
                eff = llm_config_service.get_effective()
            except Exception:  # pragma: no cover — boot-order safety net
                eff = None
            if eff is not None:
                base_url = base_url or eff.base_url
                api_key = api_key or eff.api_key
                timeout_seconds = timeout_seconds or eff.timeout_seconds
                if response_healing is None:
                    response_healing = eff.response_healing

        self.base_url = base_url or settings.LLM_BASE_URL
        self.api_key = api_key or settings.LLM_API_KEY
        self.timeout_seconds = timeout_seconds or settings.LLM_TIMEOUT_SECONDS
        self.response_healing = (
            response_healing
            if response_healing is not None
            else settings.LLM_RESPONSE_HEALING
        )
        self.provider = _derive_provider_name(self.base_url)

        if not self.base_url or not self.api_key:
            raise LLMError(
                "OpenAICompatibleClient requires base_url + api_key "
                "(set via /api/llm-config UI or LLM_BASE_URL / LLM_API_KEY env)"
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
    ) -> Dict[str, Any]:
        """Ask the model for a schema-valid JSON object.

        ``schema`` is the dict shape OpenRouter's ``response_format``
        expects — ``{"name", "strict", "schema"}``. See
        :mod:`app.schemas_llm` for the canonical constants. The
        embedded JSON schema is run through
        :func:`_strip_schema_constraints` before being sent so
        provider-side strictness about ``minimum`` / ``maxLength``
        / ``pattern`` etc. doesn't trip 400s; the constraints are
        still enforced on our side at ``model_validate`` time.

        Returns ``{"data": <parsed JSON>, "usage": {...}}``. Raises
        :class:`LLMProviderError` when the response can't be parsed
        even after the response-healing plugin has its turn.
        """
        model_name = model or settings.LLM_MODEL
        sanitized_schema = {
            **schema,
            "schema": _strip_schema_constraints(schema.get("schema", {})),
        }
        body: Dict[str, Any] = {
            "model": model_name,
            "messages": messages,
            "response_format": {
                "type": "json_schema",
                "json_schema": sanitized_schema,
            },
        }

        # OpenRouter-specific knobs go through the OpenAI SDK's
        # ``extra_body`` escape hatch; the SDK raises a TypeError on
        # any keyword argument it doesn't recognize
        # (``AsyncCompletions.create() got an unexpected keyword
        # argument 'plugins'``) so `plugins` with the ``openrouter:``
        # type prefix must be nested under ``extra_body`` rather than
        # lifted to top-level body keys.
        #
        # Provider-gated: only OpenRouter accepts the ``plugins`` key.
        # Venice / OpenAI / Ollama reject unknown keys with a 400, so
        # we never attach it for non-OR providers regardless of the
        # operator's response-healing toggle.
        if self.provider == "openrouter" and self.response_healing:
            body["extra_body"] = {"plugins": [{"id": "response-healing"}]}

        response = await self._with_retry(body)
        return self._parse_response(response)

    async def chat_completion(
        self,
        *,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        use_web_search: bool = False,
        extra_search_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Natural-language chat completion, optionally web-grounded.

        Used by :class:`LLMPricingProvider` as the first leg of its
        two-call flow — ``web_search=True`` attaches OR's server tool
        and the model returns grounded analysis as plain text. A
        second call to :meth:`structured_completion` then converts
        that text into a strict schema. The split is necessary
        because OR's ``openrouter:web_search`` middleware mangles
        nested objects in structured-output responses (every nested
        object gets wrapped in a stringified ``{completionState,
        entries, type}`` envelope). Confirmed across Anthropic /
        OpenAI / Google models — it's an OR middleware issue.

        Returns ``{"text": <content>, "usage": {...}, "provider":
        ..., "queried_at": ..., "raw": <SDK response>}``. The raw
        response is included so callers can introspect citations
        (``response.choices[0].message.annotations``).
        """
        model_name = model or settings.LLM_MODEL
        body: Dict[str, Any] = {
            "model": model_name,
            "messages": messages,
        }
        extra_body: Dict[str, Any] = {}

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
            extra_body["tools"] = [
                {"type": "openrouter:web_search", "parameters": search_params}
            ]

        if extra_body:
            body["extra_body"] = extra_body

        response = await self._with_retry(body)
        text = self._extract_content(response)
        usage = _usage_dict(getattr(response, "usage", None))
        return {
            "text": text,
            "usage": usage,
            "provider": self.provider,
            "queried_at": datetime.now(timezone.utc),
            "raw": response,
        }

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
    def _extract_content(response: Any) -> str:
        """Pull ``choices[0].message.content`` defensively.

        OR sometimes returns 200 OK with an upstream-error envelope
        shaped ``{error: {message, code}, choices: null, usage: null,
        ...}`` (observed when Anthropic-via-Azure hits a 524 timeout,
        but the same shape comes from other transient upstream
        failures). The OpenAI SDK deserializes that into a
        ChatCompletion with ``choices=None``, so accessing
        ``choices[0]`` raises ``TypeError`` instead of the
        ``AttributeError`` / ``IndexError`` a naive parser expects.
        Detect the ``error`` envelope first and surface its message;
        otherwise the empty-choices case raises with a generic note.
        Either way the router maps to a meaningful HTTP status instead
        of 500.
        """
        provider_error = getattr(response, "error", None)
        if provider_error:
            err_msg = (
                getattr(provider_error, "message", None)
                or (provider_error.get("message") if isinstance(provider_error, dict) else None)
                or "LLM provider returned an error envelope"
            )
            err_code = (
                getattr(provider_error, "code", None)
                or (provider_error.get("code") if isinstance(provider_error, dict) else None)
            )
            raise LLMProviderError(
                f"LLM provider error (code={err_code}): {err_msg}", raw=response
            )

        choices = getattr(response, "choices", None)
        if not choices:
            raise LLMProviderError(
                "LLM response had no choices (empty or null)", raw=response
            )
        try:
            content = choices[0].message.content
        except (AttributeError, IndexError, TypeError) as exc:
            raise LLMProviderError(
                "LLM response had no choices/message", raw=response
            ) from exc
        if content is None:
            raise LLMProviderError("LLM response content was null", raw=response)
        return content

    @classmethod
    def _parse_response(cls, response: Any) -> Dict[str, Any]:
        """Pull the JSON body out of a chat.completions response.

        OR returns ``response.choices[0].message.content`` as a string
        that should already be schema-valid JSON (thanks to strict
        mode + response healing). We json.loads it and surface the
        raw content on failure.
        """
        content = cls._extract_content(response)
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
