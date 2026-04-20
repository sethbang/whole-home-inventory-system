"""Barcode lookup authorization tests.

The barcode endpoint is a strict-auth endpoint: anonymous callers must not be
able to probe for items by barcode, and an authenticated caller must never see
barcodes that belong to another user.
"""

from __future__ import annotations

from app import models, security


def _make_item(db_session, owner, **overrides):
    defaults = {
        "name": "Drill",
        "category": "Tools",
        "location": "Garage",
        "barcode": "0123456789012",
        "owner_id": owner.id,
    }
    defaults.update(overrides)
    item = models.Item(**defaults)
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)
    return item


def test_barcode_lookup_requires_auth(client, user, db_session):
    _make_item(db_session, user, barcode="BAR-ALICE-1")

    resp = client.get("/api/items/barcode/BAR-ALICE-1")
    assert resp.status_code == 401


def test_barcode_lookup_returns_own_item(client, user, auth_headers, db_session):
    item = _make_item(db_session, user, barcode="BAR-ALICE-2")

    resp = client.get("/api/items/barcode/BAR-ALICE-2", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == str(item.id)


def test_barcode_lookup_does_not_leak_across_users(client, user, auth_headers, db_session):
    """Alice asking for Bob's barcode must see 404, not Bob's item."""
    bob = models.User(
        email="bob@example.com",
        username="bob",
        hashed_password=security.get_password_hash("correct-horse-battery-staple"),
        is_active=True,
    )
    db_session.add(bob)
    db_session.commit()
    db_session.refresh(bob)

    _make_item(db_session, bob, barcode="BAR-BOB-1", name="Bob's Drill")

    resp = client.get("/api/items/barcode/BAR-BOB-1", headers=auth_headers)
    assert resp.status_code == 404


def test_barcode_lookup_404_for_unknown(client, auth_headers):
    resp = client.get("/api/items/barcode/does-not-exist-99999", headers=auth_headers)
    assert resp.status_code == 404
