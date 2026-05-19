"""LLM pricing provider (v3.1 Part E).

Two-call flow against an OpenRouter-hosted model:

1. **Research** — ``chat_completion`` with
   ``openrouter:web_search`` ON and no schema. The model searches
   the web, picks comparables, and returns a grounded analysis in
   natural text.
2. **Extraction** — ``structured_completion`` (no web_search) with
   the strict ``PRICE_ESTIMATE_SCHEMA``. Converts step-1's text
   into a validated ``PriceEstimate``.

The split sidesteps an OpenRouter middleware bug where
``openrouter:web_search`` + ``response_format: json_schema``
composed together mangle nested objects in the response: every
nested object gets wrapped in a stringified
``{completionState, entries, type}`` envelope instead of the shape
we asked for. Confirmed across Anthropic / OpenAI / Google models.
See CHANGELOG "F10a" for details.

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
from ..llm.prompts import PRICING_EXTRACTION_PROMPT, PRICING_RESEARCH_PROMPT
from ..schemas_llm import PRICE_ESTIMATE_SCHEMA, PriceEstimate
from ..services import llm_config as llm_config_service
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
        # Merged prompt/completion-token counters across the two calls.
        # PricingService reads this after ``lookup`` to stamp LLMUsage.
        self.last_usage: Dict[str, Any] = {}

    async def lookup(self, identity: ItemIdentity) -> PriceEstimate:
        eff = llm_config_service.get_effective()
        if not eff.base_url or not eff.api_key:
            raise PriceProviderUnavailable(
                "LLM pricing provider requires base_url + api_key "
                "(set via /api/llm-config or env)"
            )

        client = self._client or OpenAICompatibleClient()
        model = eff.pricing_model
        item_prompt = _format_identity_prompt(identity)

        # --- Call 1: web_search research, no schema -------------------
        research_messages = [
            {"role": "system", "content": PRICING_RESEARCH_PROMPT},
            {"role": "user", "content": item_prompt},
        ]
        try:
            research = await client.chat_completion(
                messages=research_messages,
                model=model,
                use_web_search=True,
            )
        except LLMProviderError as exc:
            raise PriceProviderError(
                f"LLM research call returned an unparseable response: {exc}"
            ) from exc
        except LLMError as exc:
            raise PriceProviderUnavailable(
                f"LLM research call failed: {exc}"
            ) from exc

        analysis_text: str = research["text"]
        research_usage: Dict[str, Any] = research.get("usage", {}) or {}
        web_searches = (
            research_usage.get("server_tool_use", {}).get("web_search_requests")
        )
        if web_searches:
            logger.info(
                "llm pricing research used %d web_search calls (hash=%s)",
                web_searches,
                identity.hash[:8],
            )

        # --- Call 2: structured extraction, no web_search -------------
        extraction_messages = [
            {"role": "system", "content": PRICING_EXTRACTION_PROMPT},
            {
                "role": "user",
                "content": (
                    f"ORIGINAL ITEM METADATA:\n{item_prompt}\n\n"
                    f"PRICING ANALYSIS TO EXTRACT:\n\n{analysis_text}"
                ),
            },
        ]
        try:
            extraction = await client.structured_completion(
                messages=extraction_messages,
                schema=PRICE_ESTIMATE_SCHEMA,
                model=model,
            )
        except LLMProviderError as exc:
            raise PriceProviderError(
                f"LLM extraction returned an unparseable response: {exc}"
            ) from exc
        except LLMError as exc:
            raise PriceProviderUnavailable(
                f"LLM extraction call failed: {exc}"
            ) from exc

        data: Dict[str, Any] = extraction["data"]
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

        # Merge usage so the budget guard sees the total cost for this
        # lookup (both calls). Token / cost / web_search counters stack.
        combined_usage = _merge_usage(
            research_usage, extraction.get("usage", {}) or {}
        )
        # Stash the combined usage so PricingService can read it off
        # the provider after lookup() to stamp an accurate LLMUsage row
        # and drive the daily budget guard. Re-assigned on every
        # ``lookup`` call; not safe to read across concurrent lookups
        # on the same instance.
        self.last_usage = combined_usage

        return estimate


def _merge_usage(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    """Sum token counters across two LLM calls.

    Keeps the ``server_tool_use.web_search_requests`` counter additive
    so the total search count for a lookup is visible in logs.
    """
    out: Dict[str, Any] = {}
    for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
        out[key] = int(a.get(key, 0) or 0) + int(b.get(key, 0) or 0)
    # Preserve server_tool_use if either side reported it.
    a_tool = (a.get("server_tool_use") or {}).get("web_search_requests", 0) or 0
    b_tool = (b.get("server_tool_use") or {}).get("web_search_requests", 0) or 0
    tool_total = int(a_tool) + int(b_tool)
    if tool_total:
        out["server_tool_use"] = {"web_search_requests": tool_total}
    return out


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
