"""Unit tests for ``services.images.ImageService``.

These tests drive the service directly (no FastAPI TestClient), giving fast
feedback on the business rules independent of HTTP wiring. HTTP-level checks
continue to live in ``tests/test_images.py``.
"""

from __future__ import annotations

import io
import os

import pytest
from fastapi import HTTPException
from PIL import Image

from app import models, security
from app.services.images import (
    ALLOWED_PIL_FORMATS,
    ImageService,
    validate_image_bytes,
)


def _png_bytes(size=(32, 32), color="red") -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color=color).save(buf, format="PNG")
    return buf.getvalue()


def _jpeg_bytes(size=(32, 32)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color="blue").save(buf, format="JPEG")
    return buf.getvalue()


def _webp_bytes(size=(32, 32)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color="green").save(buf, format="WEBP")
    return buf.getvalue()


@pytest.fixture
def other_user(db_session) -> models.User:
    """A second user owned by no one in the default fixture set."""
    user = models.User(
        email="bob@example.com",
        username="bob",
        hashed_password=security.get_password_hash("correct-horse-battery-staple"),
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def item(db_session, user) -> models.Item:
    item = models.Item(
        owner_id=user.id, name="Camera", category="Electronics", location="Office"
    )
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)
    return item


# ---------------------------------------------------------------------------
# validate_image_bytes
# ---------------------------------------------------------------------------


def test_validate_accepts_png_jpeg_webp():
    assert validate_image_bytes(_png_bytes()) == "PNG"
    assert validate_image_bytes(_jpeg_bytes()) == "JPEG"
    assert validate_image_bytes(_webp_bytes()) == "WEBP"


def test_validate_allowed_set_matches_extension_map():
    """Every format we accept must also have a file extension mapping."""
    from app.services.images import EXT_BY_FORMAT

    assert set(EXT_BY_FORMAT.keys()) == ALLOWED_PIL_FORMATS


def test_validate_rejects_empty_bytes():
    with pytest.raises(HTTPException) as exc_info:
        validate_image_bytes(b"")
    assert exc_info.value.status_code == 400
    assert "empty" in exc_info.value.detail.lower()


def test_validate_rejects_non_image_bytes():
    with pytest.raises(HTTPException) as exc_info:
        validate_image_bytes(b"not-even-close-to-a-valid-image")
    assert exc_info.value.status_code == 400


def test_validate_rejects_oversize(monkeypatch):
    from app import settings as settings_module

    monkeypatch.setattr(settings_module.settings, "MAX_UPLOAD_BYTES", 128)
    big = _png_bytes(size=(256, 256))
    assert len(big) > 128
    with pytest.raises(HTTPException) as exc_info:
        validate_image_bytes(big)
    assert exc_info.value.status_code == 413


def test_validate_rejects_oversize_dimensions(monkeypatch):
    from app import settings as settings_module

    monkeypatch.setattr(settings_module.settings, "MAX_IMAGE_DIMENSION", 16)
    img = _png_bytes(size=(32, 32))  # 32 > 16
    with pytest.raises(HTTPException) as exc_info:
        validate_image_bytes(img)
    assert exc_info.value.status_code == 400
    assert "dimensions" in exc_info.value.detail.lower()


def test_validate_rejects_gif_format():
    """GIF isn't in our allowlist; a valid GIF must still be refused."""
    buf = io.BytesIO()
    Image.new("RGB", (16, 16), "red").save(buf, format="GIF")
    with pytest.raises(HTTPException) as exc_info:
        validate_image_bytes(buf.getvalue())
    assert exc_info.value.status_code == 400
    assert "unsupported" in exc_info.value.detail.lower()


# ---------------------------------------------------------------------------
# ImageService.store_for_item
# ---------------------------------------------------------------------------


def test_store_creates_db_row_and_disk_file(db_session, user, item):
    svc = ImageService(db_session, user)
    result = svc.store_for_item(item.id, _png_bytes())

    assert result.item_id == item.id
    assert result.filename.endswith(".png")
    upload_dir = os.environ["UPLOAD_DIR"]
    assert os.path.exists(os.path.join(upload_dir, result.filename))


def test_store_rejects_cross_user_item(db_session, user, other_user, item):
    """Bob cannot attach images to Alice's items."""
    svc = ImageService(db_session, other_user)
    with pytest.raises(HTTPException) as exc_info:
        svc.store_for_item(item.id, _png_bytes())
    assert exc_info.value.status_code == 404  # don't leak existence


def test_store_rejects_unknown_item(db_session, user):
    import uuid as _uuid

    svc = ImageService(db_session, user)
    with pytest.raises(HTTPException) as exc_info:
        svc.store_for_item(_uuid.uuid4(), _png_bytes())
    assert exc_info.value.status_code == 404


def test_store_propagates_validation_failure(db_session, user, item):
    svc = ImageService(db_session, user)
    with pytest.raises(HTTPException) as exc_info:
        svc.store_for_item(item.id, b"not-an-image")
    assert exc_info.value.status_code == 400

    # No DB row should have been created.
    images_for_item = (
        db_session.query(models.ItemImage)
        .filter(models.ItemImage.item_id == item.id)
        .all()
    )
    assert images_for_item == []


# ---------------------------------------------------------------------------
# ImageService.list_for_item
# ---------------------------------------------------------------------------


def test_list_for_item_returns_own_images(db_session, user, item):
    svc = ImageService(db_session, user)
    svc.store_for_item(item.id, _png_bytes())
    svc.store_for_item(item.id, _jpeg_bytes())

    listed = svc.list_for_item(item.id)
    assert len(listed) == 2
    assert {img.filename.split(".")[-1] for img in listed} == {"jpg", "png"}


def test_list_for_item_rejects_cross_user(db_session, user, other_user, item):
    svc = ImageService(db_session, user)
    svc.store_for_item(item.id, _png_bytes())

    other_svc = ImageService(db_session, other_user)
    with pytest.raises(HTTPException) as exc_info:
        other_svc.list_for_item(item.id)
    assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# ImageService.delete
# ---------------------------------------------------------------------------


def test_delete_removes_row_and_file(db_session, user, item):
    svc = ImageService(db_session, user)
    img = svc.store_for_item(item.id, _png_bytes())
    upload_dir = os.environ["UPLOAD_DIR"]
    on_disk = os.path.join(upload_dir, img.filename)
    assert os.path.exists(on_disk)

    svc.delete(img.id)
    assert not os.path.exists(on_disk)
    assert db_session.get(models.ItemImage, img.id) is None


def test_delete_rejects_cross_user(db_session, user, other_user, item):
    svc = ImageService(db_session, user)
    img = svc.store_for_item(item.id, _png_bytes())

    other_svc = ImageService(db_session, other_user)
    with pytest.raises(HTTPException) as exc_info:
        other_svc.delete(img.id)
    assert exc_info.value.status_code == 404

    # Alice's image must still exist on disk and in the DB.
    upload_dir = os.environ["UPLOAD_DIR"]
    assert os.path.exists(os.path.join(upload_dir, img.filename))
    assert db_session.get(models.ItemImage, img.id) is not None


def test_delete_missing_image_is_404(db_session, user):
    import uuid as _uuid

    svc = ImageService(db_session, user)
    with pytest.raises(HTTPException) as exc_info:
        svc.delete(_uuid.uuid4())
    assert exc_info.value.status_code == 404


def test_delete_survives_missing_disk_file(db_session, user, item):
    """If the disk file vanished out-of-band, delete still removes the DB row."""
    svc = ImageService(db_session, user)
    img = svc.store_for_item(item.id, _png_bytes())
    upload_dir = os.environ["UPLOAD_DIR"]
    os.remove(os.path.join(upload_dir, img.filename))

    svc.delete(img.id)
    assert db_session.get(models.ItemImage, img.id) is None
