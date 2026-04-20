"""Tests for ``schemas.CustomFieldsSchema``.

Validates the v2.3 strict contract: only ``ebay`` / ``facebook`` /
``user_defined`` are accepted at the top level, with per-key typing for
the first two. The import path's lenient ``coerce_from_raw`` helper
folds unknown top-level keys into ``user_defined`` so legacy data stays
portable.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.ebay.schemas import EbayCondition, EbayListingFormat
from app.facebook.schemas import FbAvailability, FbCondition
from app.schemas import CustomFieldsSchema, ItemCreate

# ---------------------------------------------------------------------------
# Strict validation (POST/PUT boundary)
# ---------------------------------------------------------------------------


def test_accepts_ebay_slot():
    cf = CustomFieldsSchema(
        ebay={
            "condition": "NEW",
            "listing_format": "FIXED_PRICE",
            "category_id": "1234",
        }
    )
    assert cf.ebay is not None
    assert cf.ebay.condition == EbayCondition.NEW
    assert cf.ebay.listing_format == EbayListingFormat.FIXED_PRICE


def test_accepts_facebook_slot():
    cf = CustomFieldsSchema(
        facebook={"condition": "NEW", "price": 99.99, "availability": "in stock"}
    )
    assert cf.facebook is not None
    assert cf.facebook.condition == FbCondition.NEW
    assert cf.facebook.price == 99.99
    assert cf.facebook.availability == FbAvailability.IN_STOCK


def test_accepts_user_defined_catchall():
    cf = CustomFieldsSchema(
        user_defined={"color": "blue", "loaned_to": "neighbor", "count": 3}
    )
    assert cf.user_defined == {"color": "blue", "loaned_to": "neighbor", "count": 3}


def test_rejects_unknown_top_level_key_at_http_boundary():
    """The whole point of strict validation — unknown keys are a 422."""
    with pytest.raises(ValidationError):
        CustomFieldsSchema.model_validate({"color": "blue"})


def test_rejects_invalid_ebay_condition_enum():
    with pytest.raises(ValidationError):
        CustomFieldsSchema(ebay={"condition": "KLINGON"})


def test_rejects_invalid_facebook_price_type():
    with pytest.raises(ValidationError):
        CustomFieldsSchema(facebook={"price": "thirty dollars maybe"})


def test_item_create_accepts_valid_custom_fields():
    created = ItemCreate(
        name="Drill",
        category="Tools",
        location="Garage",
        custom_fields={"ebay": {"condition": "NEW"}},
    )
    assert created.custom_fields is not None
    assert created.custom_fields.ebay.condition == EbayCondition.NEW


def test_item_create_rejects_unknown_custom_fields_key():
    with pytest.raises(ValidationError):
        ItemCreate(
            name="Drill",
            category="Tools",
            location="Garage",
            custom_fields={"rogue_key": "some value"},
        )


# ---------------------------------------------------------------------------
# Lenient coerce_from_raw (import path)
# ---------------------------------------------------------------------------


def test_coerce_returns_none_for_none():
    assert CustomFieldsSchema.coerce_from_raw(None) is None


def test_coerce_preserves_known_slots():
    cf = CustomFieldsSchema.coerce_from_raw(
        {"ebay": {"condition": "NEW"}, "user_defined": {"color": "red"}}
    )
    assert cf.ebay is not None
    assert cf.ebay.condition == EbayCondition.NEW
    assert cf.user_defined == {"color": "red"}


def test_coerce_moves_unknown_keys_to_user_defined():
    cf = CustomFieldsSchema.coerce_from_raw(
        {"color": "blue", "rating": 4, "loaner": "bob"}
    )
    assert cf.ebay is None
    assert cf.facebook is None
    assert cf.user_defined == {"color": "blue", "rating": 4, "loaner": "bob"}


def test_coerce_merges_unknown_keys_into_existing_user_defined():
    """Unknown keys should merge with, not shadow, an existing user_defined slot."""
    cf = CustomFieldsSchema.coerce_from_raw(
        {"color": "blue", "user_defined": {"rating": 4}}
    )
    assert cf.user_defined == {"rating": 4, "color": "blue"}


def test_coerce_still_validates_known_slot_shapes():
    """Lenience applies to top-level keys, not the content of known slots."""
    with pytest.raises(ValidationError):
        CustomFieldsSchema.coerce_from_raw({"ebay": {"condition": "KLINGON"}})


def test_coerce_rejects_non_dict_payload():
    with pytest.raises(ValueError):
        CustomFieldsSchema.coerce_from_raw("not a dict")  # type: ignore[arg-type]
