"""Unit tests for app.facebook.formatter helpers.

Pure-function tests — no DB required. Drives the formatter directly
with model instances to keep the HTTP tests in test_facebook_router.py
focused on request/response shape.
"""

from __future__ import annotations

import uuid

from app import models
from app.facebook.category_mapping import FALLBACK_CATEGORY, suggest_fb_category
from app.facebook.formatter import (
    FB_CATALOG_COLUMNS,
    FB_TITLE_MAX_LENGTH,
    build_catalog_csv_row,
    build_copy_paste_block,
)
from app.facebook.schemas import FbAvailability, FbCondition, FbFields
from app.utctime import utcnow


def _item(**overrides) -> models.Item:
    defaults = {
        "id": uuid.uuid4(),
        "owner_id": uuid.uuid4(),
        "name": "Cordless Drill",
        "category": "Tools",
        "location": "Garage",
        "brand": "Milwaukee",
        "model_number": "M18",
        "serial_number": None,
        "barcode": None,
        "purchase_date": None,
        "purchase_price": 100.0,
        "current_value": 60.0,
        "warranty_expiration": None,
        "notes": "Barely used.",
        "custom_fields": None,
        "created_at": utcnow(),
        "updated_at": utcnow(),
    }
    defaults.update(overrides)
    item = models.Item(**defaults)
    item.images = []
    return item


# ---------------------------------------------------------------------------
# suggest_fb_category
# ---------------------------------------------------------------------------


def test_suggest_fb_category_known_categories():
    assert suggest_fb_category("Tools") == "Tools"
    assert suggest_fb_category("electronics") == "Electronics"
    # Case-insensitive lookup.
    assert suggest_fb_category("FURNITURE") == "Furniture"


def test_suggest_fb_category_unknown_falls_back():
    assert suggest_fb_category("my-made-up-thing") == FALLBACK_CATEGORY
    assert suggest_fb_category(None) == FALLBACK_CATEGORY
    assert suggest_fb_category("") == FALLBACK_CATEGORY


# ---------------------------------------------------------------------------
# build_copy_paste_block
# ---------------------------------------------------------------------------


def test_copy_paste_happy_path():
    block = build_copy_paste_block(_item(), None)
    assert block.title == "Cordless Drill"
    assert block.price == 60.0
    assert block.suggested_category == "Tools"
    assert "Cordless Drill" in block.block
    assert "Price: $60.00" in block.block
    assert "Category: Tools" in block.block
    assert "Barely used." in block.block
    assert "Brand: Milwaukee" in block.block


def test_copy_paste_uses_fb_field_overrides_when_set():
    fb = FbFields(
        price=49.99,
        category="Hardware",
        description_override="Like new, local pickup only.",
    )
    block = build_copy_paste_block(_item(), fb)
    assert block.price == 49.99
    assert block.suggested_category == "Hardware"
    assert block.description == "Like new, local pickup only."
    # Override wins — the item's own notes and brand don't leak through.
    assert "Barely used." not in block.block
    assert "Milwaukee" not in block.description


def test_copy_paste_truncates_title_at_100_chars():
    long_name = (
        "Brand New Pristine Condition Ultra-Deluxe Cordless Hammer Drill "
        "with Carrying Case and Extra Batteries Included"
    )
    block = build_copy_paste_block(_item(name=long_name), None)
    assert len(block.title) <= FB_TITLE_MAX_LENGTH
    # Should cut at a word boundary when possible — no partial words.
    assert not block.title.endswith(" ")


def test_copy_paste_handles_missing_price_and_description():
    item = _item(
        current_value=None,
        purchase_price=None,
        notes=None,
        brand=None,
        model_number=None,
    )
    block = build_copy_paste_block(item, None)
    assert block.price is None
    assert block.description == ""
    # "Price:" shouldn't appear when there's no price.
    assert "Price:" not in block.block


def test_copy_paste_tags_include_category_brand_location_deduped():
    block = build_copy_paste_block(_item(brand="Milwaukee"), None)
    # Tags are included in the block text.
    assert "#Tools" in block.block
    assert "#Milwaukee" in block.block
    assert "#Garage" in block.block


def test_copy_paste_fallback_category_not_shown_in_block():
    """Miscellaneous is a UI fallback; we don't shout it at the user."""
    block = build_copy_paste_block(_item(category="quibbleflatz"), None)
    assert block.suggested_category == FALLBACK_CATEGORY
    assert "Category: Miscellaneous" not in block.block


# ---------------------------------------------------------------------------
# build_catalog_csv_row
# ---------------------------------------------------------------------------


def test_catalog_row_has_every_expected_column():
    row = build_catalog_csv_row(_item(), None)
    assert set(row.keys()) == set(FB_CATALOG_COLUMNS)


def test_catalog_row_condition_and_availability_defaults():
    row = build_catalog_csv_row(_item(), None)
    assert row["condition"] == "used"
    assert row["availability"] == "in stock"
    assert row["brand"] == "Milwaukee"
    assert row["price"] == "60.00 USD"
    assert row["quantity_to_sell_on_facebook"] == "1"


def test_catalog_row_fb_fields_override_defaults():
    fb = FbFields(
        condition=FbCondition.NEW,
        availability=FbAvailability.OUT_OF_STOCK,
        price=123.45,
        category="Hardware",
    )
    row = build_catalog_csv_row(_item(), fb)
    assert row["condition"] == "new"
    assert row["availability"] == "out of stock"
    assert row["price"] == "123.45 USD"
    assert row["fb_product_category"] == "Hardware"


def test_catalog_row_request_defaults_fill_unset_slots():
    """Export-request defaults apply when a per-item FbFields slot is empty."""
    defaults = FbFields(condition=FbCondition.USED_LIKE_NEW)
    # Item has no FbFields of its own — defaults should win.
    row = build_catalog_csv_row(_item(), None, defaults=defaults)
    assert row["condition"] == "used_like_new"


def test_catalog_row_item_fields_override_request_defaults():
    defaults = FbFields(condition=FbCondition.USED_LIKE_NEW)
    override = FbFields(condition=FbCondition.NEW)
    row = build_catalog_csv_row(_item(), override, defaults=defaults)
    assert row["condition"] == "new"


def test_catalog_row_price_empty_when_no_value():
    item = _item(current_value=None, purchase_price=None)
    row = build_catalog_csv_row(item, None)
    assert row["price"] == ""
