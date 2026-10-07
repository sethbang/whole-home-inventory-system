"""Pure formatting helpers for Facebook Marketplace exports.

Two output shapes:

- ``build_copy_paste_block`` — a text block the user pastes into the FB
  Marketplace web form, plus structured fields for the frontend's
  "copy to clipboard" UX.
- ``build_catalog_csv_row`` — one dict per item matching Meta's
  Commerce Manager catalog feed column set (business-seller feature).

The router composes these into response payloads / streaming CSVs.
"""

from __future__ import annotations

from typing import Any

from .. import models
from .category_mapping import FALLBACK_CATEGORY, suggest_fb_category
from .schemas import FbCopyPasteBlock, FbFields

# FB's web form caps listing titles at 100 characters.
FB_TITLE_MAX_LENGTH = 100

# Per Meta's Commerce Manager feed spec. Kept here as a canonical list
# so the tests can assert the CSV column ordering.
FB_CATALOG_COLUMNS: list[str] = [
    "id",
    "title",
    "description",
    "availability",
    "condition",
    "price",
    "link",
    "image_link",
    "brand",
    "google_product_category",
    "fb_product_category",
    "quantity_to_sell_on_facebook",
]


def _truncate_title(name: str) -> str:
    title = (name or "").strip()
    if len(title) > FB_TITLE_MAX_LENGTH:
        # Keep the cut at a word boundary when we can.
        clipped = title[:FB_TITLE_MAX_LENGTH].rsplit(" ", 1)[0]
        return clipped or title[:FB_TITLE_MAX_LENGTH]
    return title


def _description(item: models.Item, fb_fields: FbFields | None) -> str:
    if fb_fields and fb_fields.description_override:
        return fb_fields.description_override
    parts: list[str] = []
    if item.notes:
        parts.append(item.notes)
    detail_bits: list[str] = []
    if item.brand:
        detail_bits.append(f"Brand: {item.brand}")
    if item.model_number:
        detail_bits.append(f"Model: {item.model_number}")
    if detail_bits:
        parts.append("\n".join(detail_bits))
    return "\n\n".join(parts).strip()


def _resolve_price(item: models.Item, fb_fields: FbFields | None) -> float | None:
    if fb_fields and fb_fields.price is not None:
        return fb_fields.price
    if item.current_value is not None:
        return float(item.current_value)
    if item.purchase_price is not None:
        return float(item.purchase_price)
    return None


def _resolve_category(item: models.Item, fb_fields: FbFields | None) -> str:
    if fb_fields and fb_fields.category:
        return fb_fields.category
    return suggest_fb_category(item.category)


def _tags(item: models.Item) -> list[str]:
    tags: list[str] = []
    if item.category:
        tags.append(item.category)
    if item.brand:
        tags.append(item.brand)
    if item.location:
        tags.append(item.location)
    # De-duplicate while preserving order.
    seen: set[str] = set()
    out: list[str] = []
    for t in tags:
        key = t.lower()
        if key not in seen:
            seen.add(key)
            out.append(t)
    return out


def build_copy_paste_block(
    item: models.Item, fb_fields: FbFields | None
) -> FbCopyPasteBlock:
    """Render the item as an FbCopyPasteBlock ready for clipboard paste."""
    title = _truncate_title(item.name)
    description = _description(item, fb_fields)
    price = _resolve_price(item, fb_fields)
    category = _resolve_category(item, fb_fields)
    tags = _tags(item)

    lines: list[str] = [title]
    if price is not None:
        lines.append(f"Price: ${price:.2f}")
    if category and category != FALLBACK_CATEGORY:
        lines.append(f"Category: {category}")
    if description:
        lines.append("")
        lines.append(description)
    if tags:
        lines.append("")
        lines.append("Tags: " + ", ".join(f"#{t.replace(' ', '')}" for t in tags))

    return FbCopyPasteBlock(
        title=title,
        description=description,
        price=price,
        suggested_category=category,
        tags=tags,
        block="\n".join(lines).strip(),
    )


def build_catalog_csv_row(
    item: models.Item,
    fb_fields: FbFields | None,
    *,
    defaults: FbFields | None = None,
) -> dict[str, Any]:
    """One dict per item matching Meta's Commerce Manager feed columns.

    ``defaults`` come from the bulk-export request body and fill in any
    slots the per-item ``fb_fields`` didn't set.
    """
    # Merge defaults under, item-specific over.
    merged = _merge_fields(defaults, fb_fields)

    price = _resolve_price(item, merged)
    category = _resolve_category(item, merged)
    condition = (
        merged.condition.value if merged and merged.condition else "used"
    ).lower()
    availability = (
        merged.availability.value if merged and merged.availability else "in stock"
    )
    first_image = item.images[0].file_path if item.images else ""

    return {
        "id": str(item.id),
        "title": _truncate_title(item.name),
        "description": _description(item, merged),
        "availability": availability,
        "condition": condition,
        "price": f"{price:.2f} USD" if price is not None else "",
        "link": f"/items/{item.id}",
        "image_link": first_image,
        "brand": item.brand or "",
        "google_product_category": "",
        "fb_product_category": category,
        "quantity_to_sell_on_facebook": "1",
    }


def _merge_fields(
    defaults: FbFields | None, override: FbFields | None
) -> FbFields | None:
    """Return a single FbFields with override taking precedence over defaults."""
    if defaults is None and override is None:
        return None
    if defaults is None:
        return override
    if override is None:
        return defaults
    merged = defaults.model_dump()
    for key, value in override.model_dump(exclude_unset=True).items():
        if value is not None:
            merged[key] = value
    return FbFields(**merged)
