"""Tests for the pricing identity normalizer (v3.1 Part D)."""

from __future__ import annotations

from app.pricing.normalizer import ItemIdentity, normalize_identity


def test_identical_inputs_hash_equal():
    a = normalize_identity({"brand": "Canon", "model_number": "EOS R5", "name": "Camera"})
    b = normalize_identity({"brand": "Canon", "model_number": "EOS R5", "name": "Camera"})
    assert a.hash == b.hash


def test_casing_and_punctuation_collapse():
    a = normalize_identity({"brand": "CANON", "model_number": "eos-r5", "name": "Camera!"})
    b = normalize_identity({"brand": "Canon", "model_number": "EOS R5", "name": "camera"})
    assert a.hash == b.hash
    assert a.brand == "canon"
    assert a.model_number == "eos r5"
    assert a.name == "camera"


def test_brand_synonym_dewalt_variants():
    canonical = normalize_identity({"brand": "DEWALT", "model_number": "DCD777"})
    with_space = normalize_identity({"brand": "De Walt", "model_number": "DCD777"})
    with_hyphen = normalize_identity({"brand": "de-walt", "model_number": "DCD777"})
    assert canonical.brand == "dewalt"
    assert with_space.brand == "dewalt"
    assert with_hyphen.brand == "dewalt"
    assert canonical.hash == with_space.hash == with_hyphen.hash


def test_corporate_suffix_stripping():
    a = normalize_identity({"brand": "Canon USA", "model_number": "EOS R5"})
    b = normalize_identity({"brand": "Canon Inc", "model_number": "EOS R5"})
    c = normalize_identity({"brand": "Canon", "model_number": "EOS R5"})
    # Explicit synonyms above cover usa/inc; suffix stripping handles
    # less common cases.
    assert a.brand == "canon"
    assert b.brand == "canon"
    assert c.brand == "canon"
    assert a.hash == b.hash == c.hash


def test_unknown_suffix_stripped():
    a = normalize_identity({"brand": "Widget Corp", "model_number": "W1"})
    b = normalize_identity({"brand": "Widget", "model_number": "W1"})
    assert a.brand == "widget"
    assert b.brand == "widget"
    assert a.hash == b.hash


def test_different_models_hash_different():
    a = normalize_identity({"brand": "Canon", "model_number": "EOS R5"})
    b = normalize_identity({"brand": "Canon", "model_number": "EOS R6"})
    assert a.hash != b.hash


def test_year_affects_hash_when_provided():
    a = normalize_identity({"brand": "Canon", "model_number": "EOS R5"})
    b = normalize_identity({"brand": "Canon", "model_number": "EOS R5", "year": 2020})
    assert a.hash != b.hash


def test_year_none_and_missing_are_equivalent():
    a = normalize_identity({"brand": "Canon", "model_number": "EOS R5", "year": None})
    b = normalize_identity({"brand": "Canon", "model_number": "EOS R5"})
    assert a.hash == b.hash


def test_year_non_numeric_falls_back_to_none():
    ident = normalize_identity({"brand": "Canon", "model_number": "EOS R5", "year": "unknown"})
    assert ident.year is None


def test_accepts_attribute_objects():
    """normalize_identity should work on Item model instances too."""

    class FakeItem:
        brand = "Nikon USA"
        model_number = "D850"
        name = "Nikon full-frame DSLR"
        condition = "USED_GOOD"
        year = 2017

    ident = normalize_identity(FakeItem())
    assert ident.brand == "nikon"
    assert ident.model_number == "d850"
    assert ident.condition == "used good"
    assert ident.year == 2017


def test_empty_inputs_produce_empty_identity():
    ident = normalize_identity({})
    assert ident.brand == ""
    assert ident.model_number == ""
    # Empty hash still deterministic.
    assert ident.hash == normalize_identity({}).hash


def test_canonical_dict_is_json_safe():
    import json

    ident = normalize_identity({"brand": "Canon", "model_number": "EOS R5", "year": 2020})
    # Should be trivially serializable — no exotic types.
    dumped = json.dumps(ident.canonical_dict())
    assert "canon" in dumped
    assert "2020" in dumped


def test_identity_immutable():
    ident = ItemIdentity(brand="canon", model_number="eos r5", name="", condition="", year=None)
    try:
        ident.brand = "something"  # type: ignore[misc]
    except (AttributeError, Exception):
        pass
    else:
        raise AssertionError("ItemIdentity should be frozen")
