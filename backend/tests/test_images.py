import io

from PIL import Image


def _png_bytes(size=(32, 32)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color="red").save(buf, format="PNG")
    return buf.getvalue()


def _new_item(client, auth_headers) -> str:
    resp = client.post(
        "/api/items/",
        json={"name": "Camera", "category": "Electronics", "location": "Office"},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


def test_upload_png_succeeds(client, auth_headers):
    item_id = _new_item(client, auth_headers)
    resp = client.post(
        f"/api/items/{item_id}/images",
        files={"file": ("photo.png", _png_bytes(), "image/png")},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["filename"].endswith(".png")


def test_upload_non_image_rejected(client, auth_headers):
    item_id = _new_item(client, auth_headers)
    resp = client.post(
        f"/api/items/{item_id}/images",
        files={"file": ("evil.png", b"not-a-real-image-payload", "image/png")},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert "image" in resp.json()["detail"].lower()


def test_upload_empty_rejected(client, auth_headers):
    item_id = _new_item(client, auth_headers)
    resp = client.post(
        f"/api/items/{item_id}/images",
        files={"file": ("empty.png", b"", "image/png")},
        headers=auth_headers,
    )
    assert resp.status_code == 400


def test_upload_oversize_rejected(client, auth_headers, monkeypatch):
    from app import settings as _settings

    monkeypatch.setattr(_settings.settings, "MAX_UPLOAD_BYTES", 128)
    item_id = _new_item(client, auth_headers)
    big = _png_bytes(size=(512, 512))
    assert len(big) > 128
    resp = client.post(
        f"/api/items/{item_id}/images",
        files={"file": ("big.png", big, "image/png")},
        headers=auth_headers,
    )
    assert resp.status_code == 413
