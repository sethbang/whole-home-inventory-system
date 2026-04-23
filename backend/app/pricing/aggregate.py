"""Statistical aggregation of comparable prices (v3.1 Part E).

Both the eBay Browse provider and the LLM provider produce a list of
comparable listings; this helper flattens them to the PriceEstimate
low/median/high shape and computes a confidence score from sample
count + price spread.
"""

from __future__ import annotations

import statistics
from typing import List, Sequence

from ..schemas_llm import PriceEstimate, PriceSource


# Below this sample size we fall back to min/median/max rather than
# P10/P50/P90 — percentiles are meaningless at N=3 and actively
# misleading at N=2.
_MIN_PERCENTILE_SAMPLES = 5


def _percentile(sorted_prices: Sequence[float], pct: float) -> float:
    """Linear-interpolated percentile on a pre-sorted list."""
    if not sorted_prices:
        return 0.0
    if len(sorted_prices) == 1:
        return sorted_prices[0]
    k = (len(sorted_prices) - 1) * pct
    lo = int(k)
    hi = min(lo + 1, len(sorted_prices) - 1)
    frac = k - lo
    return sorted_prices[lo] + frac * (sorted_prices[hi] - sorted_prices[lo])


def _confidence_from_spread(prices: Sequence[float], sample_count: int) -> float:
    """0..1 score weighing sample size + price coefficient of variation.

    High sample + tight spread → confidence ≈ 0.9. Low sample or wide
    spread (CV > 0.5) → confidence drops. The degrade rate matches
    what the plan specified — 0.75× per missing sample below 3, and
    a proportional hit for CV > 0.5.
    """
    if not prices:
        return 0.0

    base = 0.9
    if sample_count < 3:
        base *= 0.75 ** (3 - sample_count)

    if len(prices) >= 2:
        mean = statistics.fmean(prices)
        if mean > 0:
            stdev = statistics.pstdev(prices)
            cv = stdev / mean
            if cv > 0.5:
                # Scale down proportionally; CV=1.0 → 0.5×, CV=2.0 → 0.25×.
                base *= max(0.25, 0.5 / cv)
    return max(0.0, min(1.0, base))


def aggregate_prices(
    sources: List[PriceSource],
    *,
    currency: str = "USD",
) -> PriceEstimate:
    """Build a PriceEstimate from a list of comparable listings.

    Drops any source with price <= 0 (API sometimes returns 0 for
    "Best Offer" listings that aren't directly comparable). Returns
    a zero-ed estimate when no usable sources remain — the caller
    decides whether to surface that or try a different provider.
    """
    usable = [s for s in sources if s.price and s.price > 0]
    if not usable:
        return PriceEstimate(
            currency=currency,
            low=0.0,
            median=0.0,
            high=0.0,
            sample_count=0,
            sources=[],
            confidence=0.0,
        )

    prices = sorted(s.price for s in usable)
    if len(prices) >= _MIN_PERCENTILE_SAMPLES:
        low = _percentile(prices, 0.10)
        median = statistics.median(prices)
        high = _percentile(prices, 0.90)
    else:
        low = min(prices)
        median = statistics.median(prices)
        high = max(prices)

    confidence = _confidence_from_spread(prices, len(usable))

    # Keep the citable sources list bounded so the response doesn't
    # balloon. Surface the 10 closest to median.
    usable.sort(key=lambda s: abs(s.price - median))
    trimmed = usable[:10]

    return PriceEstimate(
        currency=currency,
        low=round(low, 2),
        median=round(median, 2),
        high=round(high, 2),
        sample_count=len(usable),
        sources=trimmed,
        confidence=round(confidence, 3),
    )
