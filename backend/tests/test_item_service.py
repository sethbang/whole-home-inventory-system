"""Unit tests for ``services.items.ItemService``.

Drives the service directly with a real ``db_session`` so the search/filter
matrix can be exercised without the HTTP harness. HTTP tests continue to
live in ``tests/test_items.py``.
"""

from __future__ import annotations

import uuid as _uuid
from datetime import datetime

import pytest
from fastapi import HTTPException

from app import models, schemas, security
from app.services.items import ItemService


@pytest.fixture
def other_user(db_session) -> models.User:
    u = models.User(
        email="bob@example.com",
        username="bob",
        hashed_password=security.get_password_hash("correct-horse-battery-staple"),
        is_active=True,
    )
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


def _seed(db_session, user, **overrides) -> models.Item:
    defaults = {
        "owner_id": user.id,
        "name": "Drill",
        "category": "Tools",
        "location": "Garage",
    }
    defaults.update(overrides)
    item = models.Item(**defaults)
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)
    return item


def _filter(**overrides) -> schemas.SearchFilter:
    base: dict = {
        "query": None,
        "category": None,
        "location": None,
        "min_value": None,
        "max_value": None,
        "sort_by": None,
        "sort_desc": False,
        "page": 1,
        "page_size": 20,
    }
    base.update(overrides)
    return schemas.SearchFilter(**base)


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


def test_create_persists_item_for_user(db_session, user):
    svc = ItemService(db_session, user)
    created = svc.create(
        schemas.ItemCreate(name="Saw", category="Tools", location="Garage")
    )
    assert created.owner_id == user.id
    assert created.name == "Saw"


def test_get_returns_own_item(db_session, user):
    item = _seed(db_session, user)
    assert ItemService(db_session, user).get(item.id).id == item.id


def test_get_cross_user_is_404(db_session, user, other_user):
    item = _seed(db_session, user)
    with pytest.raises(HTTPException) as exc_info:
        ItemService(db_session, other_user).get(item.id)
    assert exc_info.value.status_code == 404


def test_update_applies_only_provided_fields(db_session, user):
    item = _seed(db_session, user, name="Old", brand="Acme")
    svc = ItemService(db_session, user)

    updated = svc.update(item.id, schemas.ItemUpdate(name="New"))
    assert updated.name == "New"
    assert updated.brand == "Acme"  # preserved — not touched by ItemUpdate


def test_update_cross_user_is_404(db_session, user, other_user):
    item = _seed(db_session, user)
    with pytest.raises(HTTPException) as exc_info:
        ItemService(db_session, other_user).update(
            item.id, schemas.ItemUpdate(name="Hijacked")
        )
    assert exc_info.value.status_code == 404


def test_delete_removes_own_item(db_session, user):
    item = _seed(db_session, user)
    ItemService(db_session, user).delete(item.id)
    assert db_session.get(models.Item, item.id) is None


def test_delete_cross_user_is_404(db_session, user, other_user):
    item = _seed(db_session, user)
    with pytest.raises(HTTPException) as exc_info:
        ItemService(db_session, other_user).delete(item.id)
    assert exc_info.value.status_code == 404
    assert db_session.get(models.Item, item.id) is not None


# ---------------------------------------------------------------------------
# bulk_delete
# ---------------------------------------------------------------------------


def test_bulk_delete_returns_count_and_respects_ownership(
    db_session, user, other_user
):
    alice_items = [_seed(db_session, user, name=f"a{i}") for i in range(3)]
    bob_items = [_seed(db_session, other_user, name=f"b{i}") for i in range(2)]

    # Alice asks to delete a mix — hers AND Bob's — she should only hit her own.
    ids = [i.id for i in alice_items + bob_items]
    deleted = ItemService(db_session, user).bulk_delete(ids)
    assert deleted == 3

    # Bob's items must still exist.
    for bob_item in bob_items:
        assert db_session.get(models.Item, bob_item.id) is not None


def test_bulk_delete_empty_list_is_noop(db_session, user):
    assert ItemService(db_session, user).bulk_delete([]) == 0


# ---------------------------------------------------------------------------
# list / search
# ---------------------------------------------------------------------------


def test_list_scopes_to_user(db_session, user, other_user):
    _seed(db_session, user, name="alice")
    _seed(db_session, other_user, name="bob")
    items, total = ItemService(db_session, user).list(_filter())
    assert total == 1
    assert items[0].name == "alice"


def test_list_text_query_matches_multiple_columns(db_session, user):
    _seed(db_session, user, name="Cordless Drill", brand="DeWalt", notes="good")
    _seed(db_session, user, name="Hammer", brand="Stanley", notes="drill-adjacent")
    _seed(db_session, user, name="Fridge", brand="LG", notes="appliance")

    items, total = ItemService(db_session, user).list(_filter(query="drill"))
    assert total == 2  # matches name AND notes


def test_list_category_and_location_filter(db_session, user):
    _seed(db_session, user, name="a", category="Tools", location="Garage")
    _seed(db_session, user, name="b", category="Tools", location="Basement")
    _seed(db_session, user, name="c", category="Kitchen", location="Kitchen")

    svc = ItemService(db_session, user)
    assert svc.list(_filter(category="Tools"))[1] == 2
    assert svc.list(_filter(location="Basement"))[1] == 1
    assert svc.list(_filter(category="Tools", location="Garage"))[1] == 1


def test_list_value_range_filter(db_session, user):
    _seed(db_session, user, name="cheap", current_value=5.0)
    _seed(db_session, user, name="mid", current_value=50.0)
    _seed(db_session, user, name="pricey", current_value=500.0)

    svc = ItemService(db_session, user)
    assert svc.list(_filter(min_value=10))[1] == 2
    assert svc.list(_filter(max_value=100))[1] == 2
    assert svc.list(_filter(min_value=10, max_value=100))[1] == 1


def test_list_sorts_by_valid_column(db_session, user):
    for n in ("c", "a", "b"):
        _seed(db_session, user, name=n)

    items, _ = ItemService(db_session, user).list(_filter(sort_by="name"))
    assert [i.name for i in items] == ["a", "b", "c"]

    items_desc, _ = ItemService(db_session, user).list(
        _filter(sort_by="name", sort_desc=True)
    )
    assert [i.name for i in items_desc] == ["c", "b", "a"]


def test_list_ignores_unknown_sort_by(db_session, user):
    _seed(db_session, user, name="x")
    # Should not raise — unknown attribute is silently ignored.
    items, _ = ItemService(db_session, user).list(_filter(sort_by="not_a_column"))
    assert len(items) == 1


def test_list_pagination(db_session, user):
    for i in range(25):
        _seed(db_session, user, name=f"item-{i:02d}")
    svc = ItemService(db_session, user)

    page1, total = svc.list(_filter(sort_by="name", page=1, page_size=10))
    assert total == 25
    assert len(page1) == 10

    page3, _ = svc.list(_filter(sort_by="name", page=3, page_size=10))
    assert len(page3) == 5  # 25 total, 10 + 10 + 5


# ---------------------------------------------------------------------------
# categories / locations
# ---------------------------------------------------------------------------


def test_categories_dedupes_and_excludes_nulls(db_session, user):
    _seed(db_session, user, name="a", category="Tools")
    _seed(db_session, user, name="b", category="Tools")
    _seed(db_session, user, name="c", category="Kitchen")
    _seed(db_session, user, name="d", category=None)

    cats = sorted(ItemService(db_session, user).categories())
    assert cats == ["Kitchen", "Tools"]


def test_locations_scopes_to_user(db_session, user, other_user):
    _seed(db_session, user, location="Garage")
    _seed(db_session, other_user, location="Bob's Den")
    locs = ItemService(db_session, user).locations()
    assert locs == ["Garage"]


# ---------------------------------------------------------------------------
# lookup_by_barcode
# ---------------------------------------------------------------------------


def test_lookup_by_barcode_returns_own(db_session, user):
    _seed(db_session, user, barcode="BAR-1")
    item = ItemService(db_session, user).lookup_by_barcode("BAR-1")
    assert item.barcode == "BAR-1"


def test_lookup_by_barcode_cross_user_is_404(db_session, user, other_user):
    _seed(db_session, other_user, barcode="BAR-BOB")
    with pytest.raises(HTTPException) as exc_info:
        ItemService(db_session, user).lookup_by_barcode("BAR-BOB")
    assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# export / import
# ---------------------------------------------------------------------------


def test_export_records_serializes_dates_as_iso(db_session, user):
    when = datetime(2024, 1, 2, 3, 4, 5)
    _seed(
        db_session,
        user,
        purchase_date=when,
        warranty_expiration=when,
    )
    [record] = ItemService(db_session, user).export_records()
    assert record["purchase_date"].startswith("2024-01-02T")
    assert record["warranty_expiration"].startswith("2024-01-02T")


def test_import_records_creates_items_and_drops_unknown_fields(db_session, user):
    records = [
        {
            "name": "Imported",
            "category": "Cat",
            "location": "Loc",
            # These should be silently dropped — they're managed server-side.
            "id": str(_uuid.uuid4()),
            "owner_id": str(_uuid.uuid4()),
            "created_at": "2020-01-01T00:00:00",
        }
    ]
    result = ItemService(db_session, user).import_records(records)
    assert result["items_imported"] == 1
    assert result["errors"] is None

    [item] = (
        db_session.query(models.Item)
        .filter(models.Item.owner_id == user.id)
        .all()
    )
    assert item.name == "Imported"
    # Server-managed fields must have been regenerated, not taken from input.
    assert item.owner_id == user.id


def test_import_records_parses_iso_dates(db_session, user):
    records = [
        {
            "name": "A",
            "category": "C",
            "location": "L",
            "purchase_date": "2024-05-01T00:00:00",
            "warranty_expiration": "2025-05-01T00:00:00",
        }
    ]
    ItemService(db_session, user).import_records(records)
    [item] = (
        db_session.query(models.Item)
        .filter(models.Item.owner_id == user.id)
        .all()
    )
    assert item.purchase_date == datetime(2024, 5, 1)
    assert item.warranty_expiration == datetime(2025, 5, 1)


def test_import_records_partial_failure_does_not_abort(db_session, user):
    records = [
        {"name": "good", "category": "C", "location": "L"},
        # Missing required "category" — Item constructor will accept None,
        # but the NOT NULL constraint on category will fire on commit.
        # Instead force a failure with an obviously-bad date.
        {
            "name": "bad",
            "category": "C",
            "location": "L",
            "purchase_date": "not-a-date",
        },
        {"name": "also-good", "category": "C", "location": "L"},
    ]
    result = ItemService(db_session, user).import_records(records)
    # Two of three should have imported.
    assert result["items_imported"] == 2
    assert result["errors"] is not None
    assert any("bad" in e for e in result["errors"])


def test_import_records_decodes_custom_fields_json_string(db_session, user):
    records = [
        {
            "name": "A",
            "category": "C",
            "location": "L",
            "custom_fields": '{"color": "blue", "rating": 4}',
        }
    ]
    ItemService(db_session, user).import_records(records)
    [item] = (
        db_session.query(models.Item)
        .filter(models.Item.owner_id == user.id)
        .all()
    )
    assert item.custom_fields == {"color": "blue", "rating": 4}
