"""eBay Browse API provider (v3.1 Part E).

OAuth client-credentials flow with an in-memory token cache. Queries
``/buy/browse/v1/item_summary/search`` for sold + active listings,
aggregates to low/median/high via :func:`aggregate_prices`.

Requires the following settings:

* ``EBAY_APP_ID`` + ``EBAY_CERT_ID`` — Application Keys from
  developer.ebay.com.
* ``EBAY_MARKETPLACE_ID`` — default ``EBAY_US``.
* ``EBAY_ENVIRONMENT`` — ``production`` or ``sandbox``.

Provider is opt-in (returns :class:`PriceProviderUnavailable` when
credentials are missing) so local-dev stacks without an eBay account
can still run the LLM provider.
"""

from __future__ import annotations

import base64
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx

from ..schemas_llm import PriceEstimate, PriceSource
from ..settings import settings
from .aggregate import aggregate_prices
from .normalizer import ItemIdentity
from .provider_base import (
    PriceProvider,
    PriceProviderError,
    PriceProviderNoResult,
    PriceProviderRateLimited,
    PriceProviderUnavailable,
)

logger = logging.getLogger(__name__)


# Human-friendly label → eBay's Browse API condition enum. See
# https://developer.ebay.com/api-docs/buy/browse/resources/item_summary/methods/search#h4-condition
_CONDITION_MAP: Dict[str, str] = {
    "new": "NEW",
    "like new": "LIKE_NEW",
    "used like new": "LIKE_NEW",
    "used good": "USED_EXCELLENT",
    "good": "USED_EXCELLENT",
    "used fair": "USED_GOOD",
    "acceptable": "USED_ACCEPTABLE",
    "for parts": "FOR_PARTS_OR_NOT_WORKING",
}


def _marketplace_base_url(environment: str) -> str:
    if environment.lower() == "sandbox":
        return "https://api.sandbox.ebay.com"
    return "https://api.ebay.com"


@dataclass
class _CachedToken:
    access_token: str
    expires_at: float  # UNIX seconds

    def is_valid(self) -> bool:
        # 60s buffer so we never hand out a token that's about to expire.
        return self.access_token and self.expires_at - 60 > time.time()


class EbayBrowseProvider(PriceProvider):
    """eBay Browse API pricing provider."""

    name = "ebay"

    def __init__(
        self,
        *,
        http: Optional[httpx.AsyncClient] = None,
        max_samples: Optional[int] = None,
    ) -> None:
        self._token: Optional[_CachedToken] = None
        self._http = http
        self._owns_http = http is None
        self._max_samples = max_samples or settings.PRICING_MAX_SAMPLES

    async def _client(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(timeout=30.0)
        return self._http

    async def aclose(self) -> None:
        if self._owns_http and self._http is not None:
            await self._http.aclose()

    # ------------------------------------------------------------------
    # OAuth client credentials
    # ------------------------------------------------------------------

    async def _get_token(self) -> str:
        if self._token and self._token.is_valid():
            return self._token.access_token

        if not settings.EBAY_APP_ID or not settings.EBAY_CERT_ID:
            raise PriceProviderUnavailable(
                "eBay provider requires EBAY_APP_ID + EBAY_CERT_ID"
            )

        creds = base64.b64encode(
            f"{settings.EBAY_APP_ID}:{settings.EBAY_CERT_ID}".encode()
        ).decode()
        http = await self._client()
        url = f"{_marketplace_base_url(settings.EBAY_ENVIRONMENT)}/identity/v1/oauth2/token"
        response = await http.post(
            url,
            headers={
                "Authorization": f"Basic {creds}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "grant_type": "client_credentials",
                "scope": "https://api.ebay.com/oauth/api_scope",
            },
        )
        if response.status_code == 429:
            raise PriceProviderRateLimited("eBay OAuth endpoint rate-limited")
        if response.status_code >= 400:
            raise PriceProviderUnavailable(
                f"eBay OAuth failed: {response.status_code} {response.text[:200]}"
            )
        body = response.json()
        self._token = _CachedToken(
            access_token=body["access_token"],
            expires_at=time.time() + int(body.get("expires_in", 7200)),
        )
        return self._token.access_token

    # ------------------------------------------------------------------
    # Search + aggregation
    # ------------------------------------------------------------------

    def _build_query(self, identity: ItemIdentity) -> str:
        """Compose a search string from the canonical identity."""
        parts = [identity.brand, identity.model_number, identity.name]
        query = " ".join(p for p in parts if p).strip()
        if not query:
            raise PriceProviderNoResult(
                "eBay provider needs at least a brand, model, or name"
            )
        return query

    def _build_filter(self, identity: ItemIdentity) -> Optional[str]:
        mapped = _CONDITION_MAP.get(identity.condition)
        if mapped:
            return f"conditions:{{{mapped}}}"
        return None

    async def lookup(self, identity: ItemIdentity) -> PriceEstimate:
        token = await self._get_token()
        http = await self._client()

        params: Dict[str, Any] = {
            "q": self._build_query(identity),
            "limit": min(self._max_samples, 200),
        }
        filter_str = self._build_filter(identity)
        if filter_str:
            params["filter"] = filter_str

        url = f"{_marketplace_base_url(settings.EBAY_ENVIRONMENT)}/buy/browse/v1/item_summary/search"
        response = await http.get(
            url,
            params=params,
            headers={
                "Authorization": f"Bearer {token}",
                "X-EBAY-C-MARKETPLACE-ID": settings.EBAY_MARKETPLACE_ID,
                "Accept": "application/json",
            },
        )
        if response.status_code == 429:
            raise PriceProviderRateLimited("eBay Browse search rate-limited")
        if response.status_code == 204:
            raise PriceProviderNoResult("eBay returned no matches")
        if response.status_code >= 400:
            logger.warning(
                "eBay Browse error: status=%s body=%s",
                response.status_code,
                response.text[:500],
            )
            raise PriceProviderError(
                f"eBay Browse failed: {response.status_code}"
            )

        body = response.json()
        sources = _parse_item_summaries(body.get("itemSummaries", []))
        if not sources:
            raise PriceProviderNoResult("eBay response had no usable comparables")
        return aggregate_prices(sources, currency="USD")


def _parse_item_summaries(summaries: List[Dict[str, Any]]) -> List[PriceSource]:
    """Convert eBay's itemSummaries into our PriceSource shape.

    We deliberately extract only listing/catalog fields (title, url,
    price, condition) and ignore the eBay ``seller`` object (username,
    userId, feedbackPercentage, etc.). This is load-bearing for the
    Marketplace Account Deletion exemption: WHIS persists no eBay user
    data, so we are exempt from running the deletion-notification
    callback. If you ever need seller info, you must first reverse the
    exemption via the eBay developer portal and stand up the callback
    listener — see docs/EBAY_INTEGRATION.md.
    """
    parsed: List[PriceSource] = []
    for summary in summaries:
        price_obj = summary.get("price") or {}
        try:
            price = float(price_obj.get("value", 0))
        except (TypeError, ValueError):
            continue
        if price <= 0:
            continue
        parsed.append(
            PriceSource(
                title=(summary.get("title") or "").strip() or "(untitled listing)",
                url=summary.get("itemWebUrl") or summary.get("itemHref") or "",
                price=price,
                condition=summary.get("condition"),
                sold_date=None,  # Browse doesn't return sold-listings data
                source_site="ebay",
            )
        )
    return parsed
