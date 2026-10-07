"""WHIS category -> Facebook Marketplace category string mapping.

Unlike eBay, Facebook Marketplace doesn't publish a canonical numeric
category ID list — the API (where one exists, for business commerce) and
the web form both use human-readable string taxonomies. This module
keeps a small curated map from the WHIS-side free-form ``Item.category``
value (user-entered, lowercased for lookup) to the FB category string
the copy-paste block / catalog CSV should prefer.

The map is intentionally small and operator-editable. Unknown WHIS
categories fall back to ``Miscellaneous``, which is a valid FB bucket.
"""

from __future__ import annotations

# WHIS category (lowercased) -> FB Marketplace category string.
_FB_CATEGORY_MAP: dict[str, str] = {
    # Electronics cluster
    "electronics": "Electronics",
    "computers": "Electronics",
    "phones": "Cell Phones",
    "cameras": "Cameras & Photography",
    "tv": "TVs",
    "audio": "Audio Equipment",
    # Home cluster
    "home": "Home Goods",
    "furniture": "Furniture",
    "appliances": "Home Appliances",
    "kitchen": "Kitchen Goods",
    "garden": "Garden & Outdoor",
    "tools": "Tools",
    "tool": "Tools",
    # Apparel
    "clothing": "Clothing & Shoes",
    "clothes": "Clothing & Shoes",
    "shoes": "Clothing & Shoes",
    "accessories": "Clothing & Accessories",
    # Sport / leisure
    "sports": "Sporting Goods",
    "sporting goods": "Sporting Goods",
    "bikes": "Bikes",
    "outdoor": "Outdoor Recreation",
    # Kids
    "toys": "Toys & Games",
    "baby": "Baby & Kids",
    # Media
    "books": "Books, Movies & Music",
    "music": "Books, Movies & Music",
    "movies": "Books, Movies & Music",
    # Vehicles (FB has a separate vertical but keep the hint)
    "vehicles": "Vehicles",
    "auto": "Auto Parts",
}

FALLBACK_CATEGORY = "Miscellaneous"


def suggest_fb_category(whis_category: str | None) -> str:
    """Map a WHIS-side category to an FB Marketplace category string.

    Case-insensitive lookup; unknown values fall back to
    ``Miscellaneous``. An explicit user-supplied override on the
    ``FbFields`` slot takes precedence over this function — see the
    formatter for the resolution order.
    """
    if not whis_category:
        return FALLBACK_CATEGORY
    return _FB_CATEGORY_MAP.get(whis_category.strip().lower(), FALLBACK_CATEGORY)


def all_fb_categories() -> list[str]:
    """Flat, deduplicated list of every FB category we map to.

    Used by ``GET /api/facebook/categories`` to populate the frontend's
    dropdown. ``Miscellaneous`` is included so users can select it
    explicitly.
    """
    unique = {*_FB_CATEGORY_MAP.values(), FALLBACK_CATEGORY}
    return sorted(unique)
