"""HTTP-level tests for the Facebook Marketplace router."""

from __future__ import annotations

import csv
import io
import zipfile

import pytest

from app import models


@pytest.fixture
def seeded_item(db_session, user):
    item = models.Item(
        owner_id=user.id,
        name="Cordless Drill",
        category="Tools",
        location="Garage",
        brand="Milwaukee",
        model_number="M18",
        notes="Barely used.",
        current_value=60.0,
    )
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)
    return item


# ---------------------------------------------------------------------------
# GET /categories
# ---------------------------------------------------------------------------


def test_list_categories_requires_auth(client):
    resp = client.get("/api/facebook/categories")
    assert resp.status_code == 401


def test_list_categories_returns_curated_list(client, auth_headers):
    resp = client.get("/api/facebook/categories", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "categories" in body
    # Miscellaneous must always be there as the fallback bucket.
    assert "Miscellaneous" in body["categories"]
    # A couple of known entries to sanity-check the mapping didn't drift.
    assert "Tools" in body["categories"]
    assert "Furniture" in body["categories"]


# ---------------------------------------------------------------------------
# POST /items/{id}/fb-fields
# ---------------------------------------------------------------------------


def test_update_fb_fields_persists_under_custom_fields(
    client, auth_headers, seeded_item
):
    resp = client.post(
        f"/api/facebook/items/{seeded_item.id}/fb-fields",
        headers=auth_headers,
        json={"price": 49.99, "condition": "USED_LIKE_NEW"},
    )
    assert resp.status_code == 200, resp.text
    # Response echoes the FbFields shape.
    assert resp.json()["price"] == 49.99
    assert resp.json()["condition"] == "USED_LIKE_NEW"


def test_update_fb_fields_cross_user_is_404(
    client, auth_headers, seeded_item, db_session, user
):
    import uuid

    # Swap ownership so the request is now cross-user.
    seeded_item.owner_id = uuid.uuid4()
    db_session.commit()
    resp = client.post(
        f"/api/facebook/items/{seeded_item.id}/fb-fields",
        headers=auth_headers,
        json={"price": 1.0},
    )
    assert resp.status_code == 404


def test_update_fb_fields_rejects_invalid_enum(client, auth_headers, seeded_item):
    resp = client.post(
        f"/api/facebook/items/{seeded_item.id}/fb-fields",
        headers=auth_headers,
        json={"condition": "KLINGON"},
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /items/{id}/copy-paste
# ---------------------------------------------------------------------------


def test_copy_paste_returns_block(client, auth_headers, seeded_item):
    resp = client.post(
        f"/api/facebook/items/{seeded_item.id}/copy-paste",
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["title"] == "Cordless Drill"
    assert body["price"] == 60.0
    assert "Tools" in body["suggested_category"]
    assert "Cordless Drill" in body["block"]
    assert "$60.00" in body["block"]


def test_copy_paste_reads_persisted_fb_fields(
    client, auth_headers, seeded_item, db_session
):
    seeded_item.custom_fields = {
        "facebook": {"price": 29.99, "description_override": "Pickup only."}
    }
    db_session.commit()
    resp = client.post(
        f"/api/facebook/items/{seeded_item.id}/copy-paste",
        headers=auth_headers,
    )
    body = resp.json()
    assert body["price"] == 29.99
    assert body["description"] == "Pickup only."


# ---------------------------------------------------------------------------
# GET /items/{id}/images.zip
# ---------------------------------------------------------------------------


def test_images_zip_empty_is_400(client, auth_headers, seeded_item):
    resp = client.get(
        f"/api/facebook/items/{seeded_item.id}/images.zip",
        headers=auth_headers,
    )
    assert resp.status_code == 400


def test_images_zip_streams_attached_images(
    client, auth_headers, seeded_item, db_session
):
    import os

    from PIL import Image

    upload_dir = os.environ["UPLOAD_DIR"]
    filename = "test-img-1.png"
    on_disk = os.path.join(upload_dir, filename)
    Image.new("RGB", (8, 8), color="red").save(on_disk, format="PNG")

    db_session.add(
        models.ItemImage(
            item_id=seeded_item.id,
            filename=filename,
            file_path=on_disk,
        )
    )
    db_session.commit()

    resp = client.get(
        f"/api/facebook/items/{seeded_item.id}/images.zip",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/zip"
    assert "attachment" in resp.headers["content-disposition"]

    with zipfile.ZipFile(io.BytesIO(resp.content), "r") as zf:
        assert filename in zf.namelist()


# ---------------------------------------------------------------------------
# POST /export
# ---------------------------------------------------------------------------


def test_export_requires_item_ids(client, auth_headers):
    resp = client.post(
        "/api/facebook/export",
        headers=auth_headers,
        json={"item_ids": []},
    )
    assert resp.status_code == 400


def test_export_no_matching_items_is_404(client, auth_headers):
    import uuid as _uuid

    resp = client.post(
        "/api/facebook/export",
        headers=auth_headers,
        json={"item_ids": [str(_uuid.uuid4())]},
    )
    assert resp.status_code == 404


def test_export_returns_catalog_csv(client, auth_headers, seeded_item):
    resp = client.post(
        "/api/facebook/export",
        headers=auth_headers,
        json={"item_ids": [str(seeded_item.id)]},
    )
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"].startswith("text/csv")
    assert "attachment" in resp.headers["content-disposition"]

    rows = list(csv.DictReader(io.StringIO(resp.text)))
    assert len(rows) == 1
    assert rows[0]["title"] == "Cordless Drill"
    assert rows[0]["price"] == "60.00 USD"
    assert rows[0]["brand"] == "Milwaukee"
    assert rows[0]["fb_product_category"] == "Tools"
