def test_item_crud_round_trip(client, auth_headers):
    create = client.post(
        "/api/items/",
        json={"name": "Drill", "category": "Tools", "location": "Garage"},
        headers=auth_headers,
    )
    assert create.status_code == 200, create.text
    item_id = create.json()["id"]

    listed = client.get("/api/items", headers=auth_headers)
    assert listed.status_code == 200
    assert any(i["id"] == item_id for i in listed.json()["items"])

    fetched = client.get(f"/api/items/{item_id}", headers=auth_headers)
    assert fetched.status_code == 200
    assert fetched.json()["name"] == "Drill"

    updated = client.put(
        f"/api/items/{item_id}",
        json={"name": "Cordless Drill", "category": "Tools", "location": "Garage"},
        headers=auth_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Cordless Drill"

    deleted = client.delete(f"/api/items/{item_id}", headers=auth_headers)
    assert deleted.status_code == 200

    gone = client.get(f"/api/items/{item_id}", headers=auth_headers)
    assert gone.status_code == 404


def test_list_requires_auth(client):
    resp = client.get("/api/items")
    assert resp.status_code == 401


def test_locations_counts_returns_per_room_counts_for_owner_only(
    client, db_session, auth_headers
):
    """Browse-page sidebar contract.

    Verifies four behaviors at once:
      * counts are grouped by location for the calling user
      * other users' items are excluded
      * empty / null locations are dropped
      * results are sorted by location name
    """
    from app import models, security

    # Seed three items for the auth'd user across two rooms, plus one
    # item with no location to confirm it's filtered out.
    for name, location in [
        ("Hammer", "Garage"),
        ("Wrench", "Garage"),
        ("Toaster", "Kitchen"),
        ("Mystery", ""),
    ]:
        client.post(
            "/api/items/",
            json={"name": name, "category": "Tools", "location": location},
            headers=auth_headers,
        )

    # Seed a different user's item directly so the scoping check is real.
    other = models.User(
        email="bob@example.com",
        username="bob",
        hashed_password=security.get_password_hash("ignored-for-this-test"),
        is_active=True,
    )
    db_session.add(other)
    db_session.commit()
    db_session.refresh(other)
    db_session.add(
        models.Item(
            name="Bob's Drill",
            category="Tools",
            location="Garage",
            owner_id=other.id,
        )
    )
    db_session.commit()

    resp = client.get("/api/locations/counts", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    rows = resp.json()
    assert rows == [
        {"location": "Garage", "count": 2},
        {"location": "Kitchen", "count": 1},
    ]


def test_locations_counts_requires_auth(client):
    resp = client.get("/api/locations/counts")
    assert resp.status_code == 401


def test_post_without_trailing_slash_redirects_then_creates(client, auth_headers):
    """Regression: clients that POST to `/api/items` (no slash) used to
    hit `BaseHTTPMiddleware`'s "called twice on the same scope" path —
    the trailing-slash retry middleware did `await call_next(request)` a
    second time, which raises `anyio.ClosedResourceError` and surfaced
    to the browser as a generic 500. The middleware now emits a 307
    redirect to the canonical slash form instead.
    """
    no_slash = client.post(
        "/api/items",
        json={"name": "RedirectMe", "category": "Tools", "location": "Garage"},
        headers=auth_headers,
        follow_redirects=False,
    )
    assert no_slash.status_code == 307, no_slash.text
    assert no_slash.headers["location"] == "/api/items/"

    # Following the redirect must succeed end-to-end with the same body
    # and method preserved (307 keeps the verb, unlike 302).
    followed = client.post(
        "/api/items",
        json={"name": "RedirectMe", "category": "Tools", "location": "Garage"},
        headers=auth_headers,
        follow_redirects=True,
    )
    assert followed.status_code == 200, followed.text
    assert followed.json()["name"] == "RedirectMe"
