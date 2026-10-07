"""Tests for aggregate_prices (v3.1 Part E)."""

from __future__ import annotations

import pytest

from app.pricing.aggregate import aggregate_prices
from app.schemas_llm import PriceSource


def _src(price: float, title: str = "x") -> PriceSource:
    return PriceSource(
        title=title,
        url="https://example.com/1",
        price=price,
        source_site="test",
    )


def test_empty_list_returns_zeroed_estimate():
    est = aggregate_prices([])
    assert est.low == 0
    assert est.median == 0
    assert est.high == 0
    assert est.sample_count == 0
    assert est.confidence == 0.0
    assert est.sources == []


def test_single_source_collapses_to_single_point():
    est = aggregate_prices([_src(100.0)])
    assert est.low == 100.0
    assert est.median == 100.0
    assert est.high == 100.0
    assert est.sample_count == 1
    # Sample count < 3 incurs heavy confidence decay.
    assert 0.3 < est.confidence < 0.7


def test_small_sample_uses_min_median_max():
    # Under 5 samples → no percentiles.
    est = aggregate_prices([_src(80), _src(100), _src(200)])
    assert est.low == 80.0
    assert est.high == 200.0
    assert est.median == 100.0
    assert est.sample_count == 3


def test_large_sample_uses_percentiles():
    prices = [50, 80, 90, 100, 100, 110, 120, 150, 200, 500]
    est = aggregate_prices([_src(p) for p in prices])
    # With 10 samples P10 = ~77, P90 = ~230.
    assert 70 < est.low < 90
    assert 200 < est.high < 350
    # Median is robust: (100+110)/2 = 105.
    assert est.median == 105.0
    assert est.sample_count == 10


def test_drops_zero_prices():
    """$0 listings (Best Offer placeholders) are noise; the aggregator
    drops them. Negative prices are rejected upstream by the PriceSource
    schema's `ge=0` constraint, so we only test the zero path here."""
    est = aggregate_prices([_src(0), _src(100), _src(120)])
    assert est.sample_count == 2
    assert est.low == 100.0
    assert est.high == 120.0


def test_tight_spread_gets_high_confidence():
    prices = [95, 98, 100, 102, 105, 99, 101, 103, 97, 100]
    est = aggregate_prices([_src(p) for p in prices])
    # CV is ~3-4%, well below 0.5 threshold; sample_count = 10.
    assert est.confidence > 0.8


def test_wide_spread_drops_confidence():
    prices = [10, 50, 100, 500, 1000, 2000, 50, 70]
    est = aggregate_prices([_src(p) for p in prices])
    assert est.confidence < 0.6  # high CV penalty


def test_sources_trimmed_to_ten_closest_to_median():
    # 15 prices — aggregator keeps the 10 closest to median.
    prices = [100, 101, 99, 98, 102, 95, 105, 90, 110, 80, 120, 70, 130, 200, 500]
    est = aggregate_prices([_src(p, title=f"t{i}") for i, p in enumerate(prices)])
    assert len(est.sources) == 10
    # 500 is furthest from median (100) so it should be dropped.
    assert all(s.price != 500 for s in est.sources)


def test_values_rounded_to_cents():
    prices = [10.123456, 20.987654]
    est = aggregate_prices([_src(p) for p in prices])
    # Two decimals only.
    assert est.low == pytest.approx(10.12, abs=0.01)
    assert est.high == pytest.approx(20.99, abs=0.01)
