"""Item-value pricing (v3.1).

Given an item's identifying metadata, return a PriceEstimate with
low/median/high + citable comparables. Behind ``PRICING_ENABLED``.

Flow at the service level:

    user clicks "Estimate value"
    → PricingService.estimate(item_id | metadata)
    → normalize_identity → identity_hash
    → cache.get(hash, provider) ?
    → if miss/stale: enqueue pricing_refresh ARQ task
    → task: provider.lookup(identity) in priority order
    → cache.set(hash, provider, estimate)
    → response ends up on GET /api/jobs/{id}
"""

from .aggregate import aggregate_prices
from .cache import CacheLookupResult, PriceCache
from .normalizer import ItemIdentity, normalize_identity
from .provider_base import (
    PriceProvider,
    PriceProviderError,
    PriceProviderNoResult,
    PriceProviderRateLimited,
    PriceProviderUnavailable,
)
from .provider_ebay_browse import EbayBrowseProvider
from .provider_llm import LLMPricingProvider

__all__ = [
    "CacheLookupResult",
    "EbayBrowseProvider",
    "ItemIdentity",
    "LLMPricingProvider",
    "PriceCache",
    "PriceProvider",
    "PriceProviderError",
    "PriceProviderNoResult",
    "PriceProviderRateLimited",
    "PriceProviderUnavailable",
    "aggregate_prices",
    "normalize_identity",
]
