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
