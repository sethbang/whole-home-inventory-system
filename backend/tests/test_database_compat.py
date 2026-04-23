"""Cross-dialect compatibility smoke tests.

Runs on whatever DB backs ``TEST_DATABASE_URL``. When CI runs the
Postgres matrix leg, these tests are the canary for any future model
change that accidentally depends on SQLite-specific behavior.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from app import models


def test_uuid_primary_key_round_trips(db_session):
    """Inserted UUIDs come back as ``uuid.UUID`` instances, v4."""
    u = models.User(
        email="round-trip@example.com",
        username="round-trip",
        hashed_password="x",
        is_active=True,
    )
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)

    fetched = (
        db_session.query(models.User)
        .filter_by(username="round-trip")
        .one()
    )
    assert isinstance(fetched.id, uuid.UUID)
    assert fetched.id.version == 4
    assert fetched.id == u.id


def test_json_custom_fields_round_trip(db_session, user):
    """Nested + mixed-type JSON survives a write/read cycle."""
    payload = {
        "warranty": {"expires": "2027-01-01", "provider": "SquareTrade"},
        "tags": ["camera", "professional"],
        "serial_lookup": {"depth": 3, "verified": True, "notes": None},
    }
    item = models.Item(name="Canon EOS R5", owner_id=user.id, custom_fields=payload)
    db_session.add(item)
    db_session.commit()

    fetched = db_session.query(models.Item).filter_by(name="Canon EOS R5").one()
    assert fetched.custom_fields == payload


def test_datetime_round_trip(db_session, user):
    """Naive-UTC datetimes survive the storage layer unchanged."""
    moment = datetime(2026, 4, 22, 12, 34, 56)
    item = models.Item(
        name="DateTest",
        owner_id=user.id,
        created_at=moment,
        purchase_date=moment,
        warranty_expiration=moment,
    )
    db_session.add(item)
    db_session.commit()

    fetched = db_session.query(models.Item).filter_by(name="DateTest").one()
    # Postgres preserves microsecond precision; SQLite's default DateTime
    # stores to second resolution. Compare at second precision so both
    # dialects pass.
    assert fetched.created_at.replace(microsecond=0) == moment
    assert fetched.purchase_date.replace(microsecond=0) == moment
    assert fetched.warranty_expiration.replace(microsecond=0) == moment


def test_foreign_key_cascade(db_session, user):
    """item_images cascade-delete when the parent item is removed."""
    item = models.Item(name="parent", owner_id=user.id)
    db_session.add(item)
    db_session.commit()

    image = models.ItemImage(
        item_id=item.id,
        filename="x.jpg",
        file_path="/tmp/x.jpg",
    )
    db_session.add(image)
    db_session.commit()
    image_id = image.id

    db_session.delete(item)
    db_session.commit()

    remaining = (
        db_session.query(models.ItemImage).filter_by(id=image_id).one_or_none()
    )
    assert remaining is None, "ItemImage should cascade-delete with its parent Item"
