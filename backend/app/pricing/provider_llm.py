"""LLM pricing provider (v3.1 Part E).

Hands the pricing prompt to an OpenRouter-hosted model with
``response_format: json_schema`` + the ``openrouter:web_search``
server tool. The model decides when to search, OR executes the
searches, results come back grounded and cited inside the final
JSON. We validate with Pydantic and return.

Stateless from the caller's perspective — the provider owns an
``OpenAICompatibleClient`` but builds no request state between
calls. Safe to share across coroutines.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from ..llm import (
    LLMError,
    LLMProviderError,
    OpenAICompatibleClient,
)
from ..llm.prompts import PRICING_SYSTEM_PROMPT
from ..schemas_llm import PRICE_ESTIMATE_SCHEMA, PriceEstimate
from ..settings import settings
from .normalizer import ItemIdentity
from .provider_base import (
    PriceProvider,
    PriceProviderError,
    PriceProviderNoResult,
    PriceProviderUnavailable,
)

logger = logging.getLogger(__name__)


class LLMPricingProvider(PriceProvider):
    """OpenRouter-backed pricing provider using server-side web search."""

    name = "llm"

    def __init__(self, client: Optional[OpenAICompatibleClient] = None) -> None:
        # Defer client construction so tests can inject a stub without
        # triggering the OpenAICompatibleClient constructor's
        # LLM_BASE_URL / LLM_API_KEY check.
        self._client = client

    async def lookup(self, identity: ItemIdentity) -> PriceEstimate:
        if not settings.LLM_BASE_URL or not settings.LLM_API_KEY:
            raise PriceProviderUnavailable(
                "LLM pricing provider requires LLM_BASE_URL + LLM_API_KEY"
            )

        client = self._client or OpenAICompatibleClient()

        messages = [
            {"role": "system", "content": PRICING_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": _format_identity_prompt(identity),
            },
        ]

        try:
            response = await client.structured_completion(
                messages=messages,
                schema=PRICE_ESTIMATE_SCHEMA,
                model=settings.pricing_model(),
                use_web_search=True,
            )
        except LLMProviderError as exc:
            raise PriceProviderError(
                f"LLM provider returned an unparseable response: {exc}"
            ) from exc
        except LLMError as exc:
            raise PriceProviderUnavailable(
                f"LLM provider call failed: {exc}"
            ) from exc

        data: Dict[str, Any] = response["data"]
        try:
            estimate = PriceEstimate.model_validate(data)
        except Exception as exc:
            raise PriceProviderError(
                f"LLM response didn't match PriceEstimate schema: {exc}"
            ) from exc

        if estimate.sample_count == 0 and not estimate.sources:
            raise PriceProviderNoResult(
                "LLM provider returned no comparables — try a more specific query"
            )

        # Log web_search usage for cost tracking (per OR docs the
        # server_tool_use object lands under usage).
        web_searches = (
            response.get("usage", {})
            .get("server_tool_use", {})
            .get("web_search_requests")
        )
        if web_searches:
            logger.info(
                "llm pricing lookup used %d web_search calls (hash=%s)",
                web_searches,
                identity.hash[:8],
            )

        return estimate


def _format_identity_prompt(identity: ItemIdentity) -> str:
    """Render the canonical identity as a terse user message.

    JSON is fine here — the pricing prompt explicitly tells the model
    to expect structured metadata. Keep keys snake_case to match the
    schema the LLM is about to emit.
    """
    payload = {
        "brand": identity.brand,
        "model_number": identity.model_number,
        "name": identity.name,
        "condition": identity.condition or None,
        "year": identity.year,
    }
    clean = {k: v for k, v in payload.items() if v not in (None, "")}
    return (
        "Estimate the resale value of this item. Return only the "
        "PriceEstimate JSON.\n\nITEM:\n"
        + json.dumps(clean, sort_keys=True, indent=2)
    )
