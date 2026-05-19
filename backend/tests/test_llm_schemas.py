"""Round-trip coverage for app.schemas_llm.

The schemas are consumed in two ways:
1. ``Model.model_json_schema()`` → handed to OpenRouter's
   ``response_format`` strict mode.
2. ``Model.model_validate(...)`` → belt-and-suspenders check on the
   model's response.

If those two ever drift we silently get invalid data. These tests
pin down the contract.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas_llm import (
    PRICE_ESTIMATE_SCHEMA,
    PROMPT_VERSION,
    VISION_SUGGESTION_SCHEMA,
    PriceEstimate,
    PriceEstimateEnvelope,
    VisionResult,
    VisionSuggestion,
)


def test_prompt_version_is_nonempty():
    assert PROMPT_VERSION and PROMPT_VERSION.startswith("v")


def test_vision_schema_wrapper_shape():
    # OR response_format expects {name, strict, schema}.
    assert VISION_SUGGESTION_SCHEMA["name"] == "VisionSuggestion"
    assert VISION_SUGGESTION_SCHEMA["strict"] is True
    inner = VISION_SUGGESTION_SCHEMA["schema"]
    # Core fields surface in the JSON Schema.
    assert "properties" in inner
    assert "confidence" in inner["properties"]
    # confidence is required (no default).
    assert "confidence" in inner.get("required", [])


def test_price_estimate_schema_wrapper_shape():
    assert PRICE_ESTIMATE_SCHEMA["name"] == "PriceEstimate"
    assert PRICE_ESTIMATE_SCHEMA["strict"] is True


def test_vision_suggestion_accepts_minimum_payload():
    model = VisionSuggestion.model_validate({"confidence": 0.7})
    assert model.confidence == 0.7
    assert model.name is None
    assert model.suggested_tags == []


def test_vision_suggestion_rejects_out_of_range_confidence():
    with pytest.raises(ValidationError):
        VisionSuggestion.model_validate({"confidence": 1.5})
    with pytest.raises(ValidationError):
        VisionSuggestion.model_validate({"confidence": -0.1})


def test_vision_suggestion_forbids_extra_fields():
    with pytest.raises(ValidationError):
        VisionSuggestion.model_validate({"confidence": 0.5, "surprise": True})


def test_price_estimate_round_trip():
    payload = {
        "currency": "USD",
        "low": 100.0,
        "median": 150.0,
        "high": 200.0,
        "sample_count": 5,
        "sources": [
            {
                "title": "Canon EOS R5 body",
                "url": "https://ebay.com/itm/123",
                "price": 145.0,
                "condition": "USED",
                "sold_date": "2026-04-01",
                "source_site": "ebay",
            }
        ],
        "confidence": 0.82,
    }
    model = PriceEstimate.model_validate(payload)
    assert model.median == 150.0
    assert model.sources[0].source_site == "ebay"
    # Dump round-trips cleanly.
    dumped = json.loads(model.model_dump_json())
    assert dumped["sources"][0]["url"] == "https://ebay.com/itm/123"


def test_vision_result_envelope_carries_bookkeeping():
    suggestion = VisionSuggestion(confidence=0.8)
    result = VisionResult(
        suggestion=suggestion,
        provider="openrouter",
        model="google/gemini-2.5-flash",
        prompt_version=PROMPT_VERSION,
        tokens_in=100,
        tokens_out=50,
        cost_usd_estimate=0.002,
        queried_at=datetime.now(timezone.utc),
    )
    assert result.model == "google/gemini-2.5-flash"


def test_price_envelope_carries_cache_hit_flag():
    env = PriceEstimateEnvelope(
        estimate=PriceEstimate(
            low=1, median=2, high=3, sample_count=0, sources=[], confidence=0.5
        ),
        provider="ebay",
        queried_at=datetime.now(timezone.utc),
        cache_hit=True,
    )
    assert env.cache_hit is True
