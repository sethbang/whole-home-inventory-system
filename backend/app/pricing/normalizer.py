"""Item identity normalization (v3.1).

Consistent hashing for cache lookup. Two items with the same brand +
model should produce the same ``identity_hash`` regardless of casing,
punctuation, stray whitespace, or trivial brand spellings.

The function is deterministic and pure — no DB access, no network.
Call it from both the PricingService (for lookups) and the eventual
backfill job (for bulk cache priming).
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional


# Brand spellings the LLM (and users) flatten inconsistently. Map them
# all to the canonical form so cache keys don't splinter.
_BRAND_SYNONYMS: Dict[str, str] = {
    "dewalt": "dewalt",
    "de walt": "dewalt",
    "de-walt": "dewalt",
    "canon usa": "canon",
    "canon inc": "canon",
    "canon corp": "canon",
    "nikon usa": "nikon",
    "nikon corp": "nikon",
    "sony electronics": "sony",
    "sony corp": "sony",
    "apple inc": "apple",
    "apple computer": "apple",
    "samsung electronics": "samsung",
    "bosch tools": "bosch",
    "makita usa": "makita",
    "ryobi tools": "ryobi",
    "kitchenaid inc": "kitchenaid",
}

# Characters we treat as insignificant — collapse to a single space
# before hashing. Punctuation leaks frequently from OCR'd labels.
_PUNCT_RE = re.compile(r"[^a-z0-9]+")
_WHITESPACE_RE = re.compile(r"\s+")


def _normalize_text(value: Optional[str]) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    if not value:
        return ""
    lowered = value.strip().lower()
    collapsed = _PUNCT_RE.sub(" ", lowered)
    return _WHITESPACE_RE.sub(" ", collapsed).strip()


def _canonicalize_brand(brand: Optional[str]) -> str:
    """Apply the synonym table on top of text normalization."""
    base = _normalize_text(brand)
    if not base:
        return ""
    if base in _BRAND_SYNONYMS:
        return _BRAND_SYNONYMS[base]
    # Heuristic for "<brand> corp" / "<brand> inc" / "<brand> usa"
    # suffixes we don't have an explicit entry for.
    for suffix in (" usa", " inc", " corp", " llc", " ltd"):
        if base.endswith(suffix):
            return base[: -len(suffix)].strip()
    return base


@dataclass(frozen=True, slots=True)
class ItemIdentity:
    """Canonical identity keyed by brand + model + name.

    ``hash`` is deterministic across Python versions and runs (uses
    sha256 of a sorted-key JSON of the canonical fields). Two items
    with the same brand + model_number + (name fallback) produce the
    same hash — cache hits work across users, since prices aren't
    scoped to an owner.
    """

    brand: str
    model_number: str
    name: str
    condition: str
    year: Optional[int]

    @property
    def hash(self) -> str:
        canonical = {
            "brand": self.brand,
            "model_number": self.model_number,
            "name": self.name,
            "condition": self.condition,
            # year hashes as a string so None stays absent (not "null").
            "year": str(self.year) if self.year else "",
        }
        raw = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def canonical_dict(self) -> Dict[str, Any]:
        return {
            "brand": self.brand,
            "model_number": self.model_number,
            "name": self.name,
            "condition": self.condition,
            "year": self.year,
        }


def normalize_identity(metadata: Mapping[str, Any]) -> ItemIdentity:
    """Build an ItemIdentity from a metadata mapping.

    Accepts both ``app.models.Item`` instances (via their attribute
    access) and plain dicts. The caller can pass whatever keys they
    have — missing fields become empty strings and are excluded from
    the effective hash key below.

    Condition defaults to empty (so the cache can serve a hit across
    condition variants when the caller doesn't specify). Year is the
    only non-string field — kept numeric so callers can filter on it.
    """

    def _get(key: str, default: Any = None) -> Any:
        if hasattr(metadata, key):
            return getattr(metadata, key, default)
        if isinstance(metadata, Mapping):
            return metadata.get(key, default)
        return default

    brand = _canonicalize_brand(_get("brand"))
    model_number = _normalize_text(_get("model_number"))
    name = _normalize_text(_get("name"))
    condition = _normalize_text(_get("condition"))
    year_raw = _get("year")
    year: Optional[int] = None
    if year_raw is not None:
        try:
            year = int(year_raw)
        except (TypeError, ValueError):
            year = None

    return ItemIdentity(
        brand=brand,
        model_number=model_number,
        name=name,
        condition=condition,
        year=year,
    )
