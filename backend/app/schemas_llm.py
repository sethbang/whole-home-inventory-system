"""LLM-facing Pydantic models + JSON Schemas (v3.1).

The triangular invariant established in v3.0 Part G: one set of
Pydantic models, published in two ways.

* **Frontend (TS)** — OpenAPI → ``frontend/src/api/openapi.d.ts``
  via the v3.0 codegen pipeline. Every field's shape, name, and
  nullability is the same as what the backend returns.
* **LLM (OpenRouter structured outputs)** — ``model_json_schema()``
  hands the same schema to ``response_format: json_schema`` so the
  model returns schema-valid JSON by construction. See
  ``OR_docs/OR_structured-outputs.md``.

When ``OpenAICompatibleClient.structured_completion`` runs, it pulls
the schema from ``model_json_schema()`` of the target Pydantic model
and hands it verbatim to the OR API. The response comes back as a
dict that we round-trip through ``Model.model_validate`` — that
second validation is belt-and-suspenders against the edge case of a
provider that silently fails the ``require_parameters`` check.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Vision auto-fill
# ---------------------------------------------------------------------------


class VisionSuggestion(BaseModel):
    """Structured metadata inferred from one or more photos of an item.

    Every field is ``Optional`` so the model can leave a slot blank
    when it's genuinely uncertain — forcing it to hallucinate a
    serial number when it can't read the label is exactly the
    failure mode this feature should avoid. The UI surfaces
    ``confidence`` + ``warnings`` so the user can decide what to
    accept.
    """

    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = Field(
        None,
        description="Short, search-friendly item name. Prefer canonical names over marketing slogans.",
    )
    category: Optional[str] = Field(
        None,
        description="High-level category (Electronics, Tools, Kitchen, etc.). One noun or phrase.",
    )
    description: Optional[str] = Field(
        None,
        description="One or two sentences describing the item. Factual; no purple prose.",
    )
    brand: Optional[str] = Field(None, description="Manufacturer brand name as printed on the item.")
    model_number: Optional[str] = Field(
        None, description="Model / part number when visible on the item or label."
    )
    serial_number: Optional[str] = Field(
        None,
        description="Serial number only when clearly visible. NEVER guess.",
    )
    condition: Optional[str] = Field(
        None,
        description="Physical condition: NEW, LIKE_NEW, GOOD, ACCEPTABLE, FOR_PARTS.",
    )
    year: Optional[int] = Field(
        None, description="Model / release year when inferable from the item.", ge=1900, le=2100
    )
    color: Optional[str] = Field(None, description="Dominant color.")
    dimensions: Optional[str] = Field(
        None,
        description="Rough dimensions in the form 'WxDxH in cm' or 'diameter X cm'. Omit if not visible.",
    )
    suggested_tags: List[str] = Field(
        default_factory=list,
        description="Short keyword tags (≤5 words each) to aid later search.",
    )
    ebay_item_specifics: Dict[str, str] = Field(
        default_factory=dict,
        description="Flat key→value map aligned to eBay's Item Specifics fields for this category.",
    )
    fb_item_specifics: Dict[str, str] = Field(
        default_factory=dict,
        description="Flat key→value map aligned to Facebook Marketplace's item attributes.",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Overall confidence in the suggestion, 0..1. Lower when photo quality is poor or the item is unrecognized.",
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Human-readable notes about uncertainty (e.g. 'Serial obscured', 'Multiple items in frame').",
    )


class VisionResult(BaseModel):
    """Full wrapper returned by ``VisionService.identify``.

    Carries the raw suggestion plus the bookkeeping the UI + billing
    layer need (provider, model, prompt version, token usage, cost).
    The frontend polls ``GET /api/jobs/{id}`` and receives this
    shape under ``result`` once the task is complete.
    """

    model_config = ConfigDict(extra="forbid")

    suggestion: VisionSuggestion
    provider: str = Field(
        ..., description="Configured LLM provider identifier (derived from base URL)."
    )
    model: str = Field(..., description="Model name used for the vision call.")
    prompt_version: str = Field(..., description="PROMPT_VERSION at call time, for A/B tracking.")
    tokens_in: int = Field(0, ge=0)
    tokens_out: int = Field(0, ge=0)
    cost_usd_estimate: float = Field(0.0, ge=0.0)
    queried_at: datetime


# ---------------------------------------------------------------------------
# Item-value pricing
# ---------------------------------------------------------------------------


class PriceSource(BaseModel):
    """One comparable listing that contributes to a price estimate."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., description="Listing title as shown at the source.")
    url: str = Field(..., description="Direct URL to the comparable listing. Must be canonical.")
    price: float = Field(..., ge=0.0, description="Listed or sold price, in USD.")
    condition: Optional[str] = Field(
        None, description="Condition label the source used (NEW / USED / etc.)."
    )
    sold_date: Optional[str] = Field(
        None,
        description="ISO date when the item sold (empty for active listings). Format YYYY-MM-DD.",
    )
    source_site: Optional[str] = Field(
        None, description="Short site name (e.g. 'ebay', 'mercari')."
    )


class PriceEstimate(BaseModel):
    """Structured resale estimate returned by a ``PriceProvider``."""

    model_config = ConfigDict(extra="forbid")

    currency: str = Field("USD", description="ISO 4217 currency code.")
    low: float = Field(..., ge=0.0)
    median: float = Field(..., ge=0.0)
    high: float = Field(..., ge=0.0)
    sample_count: int = Field(
        ..., ge=0, description="Number of comparables that contributed to the aggregate."
    )
    sources: List[PriceSource] = Field(
        default_factory=list,
        description="Representative comparables (max ~10). Bigger samples are summarized in the aggregate.",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="0..1. Degrade when sample_count is low, comparables conflict, or staleness fallback fires.",
    )


class PriceEstimateEnvelope(BaseModel):
    """PriceEstimate + metadata returned by the pricing service.

    The envelope adds provider / cache / cost bookkeeping that the LLM
    doesn't need to produce — it's populated by ``PricingService`` as
    the estimate flows through the layers.
    """

    model_config = ConfigDict(extra="forbid")

    estimate: PriceEstimate
    provider: str = Field(..., description="Which provider produced this estimate.")
    prompt_version: str = Field(
        "", description="PROMPT_VERSION when the LLM provider was used; empty for API-only providers."
    )
    queried_at: datetime
    cache_hit: bool = False
    cost_usd_estimate: float = Field(0.0, ge=0.0)


# ---------------------------------------------------------------------------
# Prompt versioning
# ---------------------------------------------------------------------------

# Bumped whenever the system prompt or target schema changes materially.
# Persisted on every suggestion / estimate row so we can A/B future
# prompt variants.
PROMPT_VERSION = "v3.1.0"


# ---------------------------------------------------------------------------
# JSON Schemas handed to OpenRouter structured outputs
# ---------------------------------------------------------------------------


def _json_schema(model: type[BaseModel], name: str) -> Dict[str, Any]:
    """Wrap a Pydantic schema in the shape ``response_format`` expects.

    OR wants ``{"name", "strict", "schema"}``. Pydantic's
    ``model_json_schema()`` emits the inner ``schema`` payload; we
    inject the outer metadata here.
    """
    schema = model.model_json_schema(ref_template="#/$defs/{model}")
    return {
        "name": name,
        "strict": True,
        "schema": schema,
    }


VISION_SUGGESTION_SCHEMA: Dict[str, Any] = _json_schema(
    VisionSuggestion, "VisionSuggestion"
)
PRICE_ESTIMATE_SCHEMA: Dict[str, Any] = _json_schema(PriceEstimate, "PriceEstimate")


__all__ = [
    "VisionSuggestion",
    "VisionResult",
    "PriceSource",
    "PriceEstimate",
    "PriceEstimateEnvelope",
    "PROMPT_VERSION",
    "VISION_SUGGESTION_SCHEMA",
    "PRICE_ESTIMATE_SCHEMA",
]
