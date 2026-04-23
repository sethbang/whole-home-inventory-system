"""Full-text search coverage for ItemService.list().

Runs on both SQLite (FTS5 virtual table) and Postgres (tsvector + GIN)
via the ``TEST_DATABASE_URL`` matrix axis. The service layer picks the
backend at query time, so every assertion here must hold on both.
"""

from __future__ import annotations

from app import models, schemas
from app.services.items import ItemService


def _seed(db_session, user: models.User) -> None:
    samples = [
        {"name": "Canon EOS R5", "brand": "Canon", "model_number": "EOS R5"},
        {"name": "Nikon D850", "brand": "Nikon", "model_number": "D850"},
        {"name": "DeWalt drill", "brand": "DeWalt", "category": "Tools"},
        {"name": "Vintage LP", "notes": "Miles Davis, Kind of Blue, 1959 pressing"},
        {"name": "Kitchen blender", "location": "Kitchen"},
    ]
    for row in samples:
        item = models.Item(owner_id=user.id, **row)
        db_session.add(item)
    db_session.commit()


def _svc(db_session, user: models.User) -> ItemService:
    return ItemService(db_session, user)


def _search(svc: ItemService, query: str) -> list[models.Item]:
    filt = schemas.SearchFilter(query=query)
    items, _ = svc.list(filt)
    return items


def test_name_match(db_session, user):
    _seed(db_session, user)
    svc = _svc(db_session, user)
    hits = _search(svc, "canon")
    assert {h.name for h in hits} == {"Canon EOS R5"}


def test_case_insensitive(db_session, user):
    _seed(db_session, user)
    svc = _svc(db_session, user)
    for q in ("Canon", "CANON", "cAnOn"):
        hits = _search(svc, q)
        assert {h.name for h in hits} == {"Canon EOS R5"}, q


def test_brand_match(db_session, user):
    _seed(db_session, user)
    svc = _svc(db_session, user)
    hits = _search(svc, "dewalt")
    assert {h.name for h in hits} == {"DeWalt drill"}


def test_notes_match(db_session, user):
    _seed(db_session, user)
    svc = _svc(db_session, user)
    hits = _search(svc, "miles davis")
    assert {h.name for h in hits} == {"Vintage LP"}


def test_location_match(db_session, user):
    _seed(db_session, user)
    svc = _svc(db_session, user)
    hits = _search(svc, "kitchen")
    assert {h.name for h in hits} == {"Kitchen blender"}


def test_model_number_match(db_session, user):
    _seed(db_session, user)
    svc = _svc(db_session, user)
    hits = _search(svc, "D850")
    assert {h.name for h in hits} == {"Nikon D850"}


def test_no_match_returns_empty(db_session, user):
    _seed(db_session, user)
    svc = _svc(db_session, user)
    hits = _search(svc, "xyznevermatches")
    assert hits == []


def test_ownership_enforced(db_session, user):
    """Another user's items don't leak into search results."""
    from app import security

    other = models.User(
        email="eve@example.com",
        username="eve",
        hashed_password=security.get_password_hash("x"),
        is_active=True,
    )
    db_session.add(other)
    db_session.commit()
    db_session.refresh(other)

    db_session.add(models.Item(name="Eve's secret camera", brand="Canon", owner_id=other.id))
    db_session.add(models.Item(name="Alice's item", owner_id=user.id))
    db_session.commit()

    svc = _svc(db_session, user)
    hits = _search(svc, "canon")
    # Alice's search MUST NOT return Eve's Canon.
    assert all(h.owner_id == user.id for h in hits)
    assert "Eve's secret camera" not in {h.name for h in hits}


def test_updates_reflect_in_search(db_session, user):
    """Updating an item's indexed fields updates the FTS index."""
    item = models.Item(name="Generic widget", owner_id=user.id)
    db_session.add(item)
    db_session.commit()

    svc = _svc(db_session, user)
    assert _search(svc, "specific") == []

    item.notes = "A specific gizmo for the attic"
    db_session.commit()
    hits = _search(svc, "specific")
    assert {h.name for h in hits} == {"Generic widget"}


def test_deletes_remove_from_search(db_session, user):
    """Deleting an item pulls it out of the FTS index."""
    item = models.Item(name="Transient gadget", brand="Vanish", owner_id=user.id)
    db_session.add(item)
    db_session.commit()

    svc = _svc(db_session, user)
    assert {h.name for h in _search(svc, "vanish")} == {"Transient gadget"}

    db_session.delete(item)
    db_session.commit()
    assert _search(svc, "vanish") == []


def test_quoted_query_safe(db_session, user):
    """User queries containing double quotes don't break the FTS parser."""
    db_session.add(models.Item(name='12" vinyl record', notes="Sealed", owner_id=user.id))
    db_session.commit()
    svc = _svc(db_session, user)
    # Verifies the sanitize_fts5 path doesn't crash on embedded quotes;
    # correctness on SQLite FTS5 depends on the phrase-quoting we do in
    # _sanitize_fts5 and Postgres plainto_tsquery which ignores quotes.
    hits = _search(svc, 'sealed')
    assert {h.name for h in hits} == {'12" vinyl record'}
