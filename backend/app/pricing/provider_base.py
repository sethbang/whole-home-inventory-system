"""Base class + common exceptions for pricing providers (v3.1)."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..schemas_llm import PriceEstimate
from .normalizer import ItemIdentity


class PriceProviderError(Exception):
    """Base exception for provider-side failures.

    Subtypes exist so the service layer can decide whether to retry,
    fall back to another provider, or return a stale cache entry.
    """


class PriceProviderRateLimited(PriceProviderError):
    """Provider returned 429 / exhausted quota. Stale cache is an OK fallback."""


class PriceProviderUnavailable(PriceProviderError):
    """Provider is down / misconfigured. No stale fallback; surface the error."""


class PriceProviderNoResult(PriceProviderError):
    """Provider reached successfully but found no comparables."""


class PriceProvider(ABC):
    """Common interface for every pricing source.

    Concrete implementations:

    * :class:`EbayBrowseProvider` — eBay Browse API (v3.1 Part E).
    * :class:`LLMPricingProvider` — OpenRouter structured outputs +
      the ``openrouter:web_search`` server tool (v3.1 Part E).

    Providers are stateless from the caller's perspective. Any
    request-scoped resources (OAuth tokens, HTTP clients) live as
    instance attributes and should be safe to share across
    coroutines.
    """

    name: str  # "ebay" | "llm" | etc. Matches the PRICING_PROVIDERS list entries.

    @abstractmethod
    async def lookup(self, identity: ItemIdentity) -> PriceEstimate:
        """Return a PriceEstimate for the given canonical identity.

        Raises a :class:`PriceProviderError` subclass on failure.
        """
