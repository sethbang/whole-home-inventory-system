"""Tests for Part E: post-upload thumbnail pipeline.

Covers the service helper (generate_thumbnail), the inline fallback
path in the images router, and the ARQ task wrapper. End-to-end
worker round-trip is smoke-tested separately in Part E's verification
notes since it requires a live Redis.
"""

from __future__ import annotations

import io
import os
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from PIL import Image

from app import models
from app.main import app
from app.services.images import (
    ImageService,
    THUMBNAIL_PREFIX,
    THUMBNAIL_SIZE,
)
from app.settings import settings


def _png_bytes(size: tuple[int, int] = (800, 600)) -> bytes:
    img = Image.new("RGB", size, color=(80, 140, 220))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _seed_item(db_session, user: models.User) -> models.Item:
    item = models.Item(name="Subject", owner_id=user.id)
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)
    return item


# ---------------------------------------------------------------------------
# Service helper
# ---------------------------------------------------------------------------


def test_generate_thumbnail_writes_file_and_stamps_row(db_session, user):
    item = _seed_item(db_session, user)
    service = ImageService(db=db_session, user=user)
    image = service.store_for_item(item.id, _png_bytes())

    # Row initially has no thumbnail (store_for_item doesn't generate one
    # — the router does that in Part E's fallback path).
    assert image.thumbnail_path is None
    assert image.thumbnail_generated_at is None

    ok = service.generate_thumbnail(image.id)
    assert ok is True
    db_session.refresh(image)

    assert image.thumbnail_path is not None
    assert image.thumbnail_path.startswith("uploads/")
    assert os.path.basename(image.thumbnail_path).startswith(THUMBNAIL_PREFIX)
    assert image.thumbnail_path.endswith(".webp")
    assert image.thumbnail_generated_at is not None

    # Disk file exists and is a valid WebP at the expected dimensions.
    on_disk = os.path.join(
        str(settings.upload_path), os.path.basename(image.thumbnail_path)
    )
    assert os.path.exists(on_disk)
    with Image.open(on_disk) as thumb:
        assert thumb.format == "WEBP"
        assert thumb.size == THUMBNAIL_SIZE


def test_generate_thumbnail_returns_false_for_missing_image(db_session, user):
    service = ImageService(db=db_session, user=user)
    assert service.generate_thumbnail(uuid.uuid4()) is False


def test_generate_thumbnail_returns_false_when_source_missing(db_session, user):
    """Race: task fires after the original was already deleted from disk."""
    item = _seed_item(db_session, user)
    service = ImageService(db=db_session, user=user)
    image = service.store_for_item(item.id, _png_bytes())

    source_path = os.path.join(str(settings.upload_path), image.filename)
    os.remove(source_path)  # yank the source file

    assert service.generate_thumbnail(image.id) is False


def test_delete_removes_thumbnail_file(db_session, user):
    item = _seed_item(db_session, user)
    service = ImageService(db=db_session, user=user)
    image = service.store_for_item(item.id, _png_bytes())
    service.generate_thumbnail(image.id)
    db_session.refresh(image)

    thumb_on_disk = os.path.join(
        str(settings.upload_path), os.path.basename(image.thumbnail_path)
    )
    assert os.path.exists(thumb_on_disk)

    service.delete(image.id)
    assert not os.path.exists(thumb_on_disk)


# ---------------------------------------------------------------------------
# Router — upload endpoint
# ---------------------------------------------------------------------------


def test_upload_runs_thumbnail_inline_when_no_worker(client, auth_headers, user, db_session):
    """Sync fallback: thumbnail fields populated before the response returns."""
    app.state.arq = None
    item = _seed_item(db_session, user)

    resp = client.post(
        f"/api/items/{item.id}/images",
        headers=auth_headers,
        files={"file": ("shot.png", _png_bytes(), "image/png")},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["thumbnail_path"] is not None
    assert body["thumbnail_path"].endswith(".webp")
    assert body["thumbnail_generated_at"] is not None


def test_upload_enqueues_thumbnail_when_worker_active(client, auth_headers, user, db_session):
    """Async path: upload returns immediately; thumbnail fields stay null until the task runs."""
    pool = MagicMock()
    pool.close = AsyncMock(return_value=None)
    pool.enqueue_job = AsyncMock(return_value=MagicMock(job_id="t-1"))
    app.state.arq = pool

    item = _seed_item(db_session, user)

    try:
        resp = client.post(
            f"/api/items/{item.id}/images",
            headers=auth_headers,
            files={"file": ("shot.png", _png_bytes(), "image/png")},
        )
    finally:
        app.state.arq = None

    assert resp.status_code == 200, resp.text
    body = resp.json()
    # Worker will populate these later; for now they're still null.
    assert body["thumbnail_path"] is None
    assert body["thumbnail_generated_at"] is None

    pool.enqueue_job.assert_awaited_once()
    args = pool.enqueue_job.await_args
    assert args.args[0] == "thumbnail_generate"
    assert args.kwargs["user_id"] == str(user.id)
    assert args.kwargs["image_id"] == body["id"]


def test_upload_falls_back_inline_when_enqueue_fails(client, auth_headers, user, db_session):
    """Broken Redis shouldn't stop thumbnails from being generated."""
    pool = MagicMock()
    pool.close = AsyncMock(return_value=None)
    pool.enqueue_job = AsyncMock(side_effect=RuntimeError("redis down"))
    app.state.arq = pool

    item = _seed_item(db_session, user)

    try:
        resp = client.post(
            f"/api/items/{item.id}/images",
            headers=auth_headers,
            files={"file": ("shot.png", _png_bytes(), "image/png")},
        )
    finally:
        app.state.arq = None

    assert resp.status_code == 200, resp.text
    body = resp.json()
    # Fallback ran inline — thumbnail is present despite the enqueue failure.
    assert body["thumbnail_path"] is not None
    assert body["thumbnail_generated_at"] is not None
