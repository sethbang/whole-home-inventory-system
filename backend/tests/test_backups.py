"""Backup endpoint tests: zip validation, N+1 elimination, dry-run/confirm, no leak."""

from __future__ import annotations

import io
import json
import os
import zipfile
from datetime import datetime

import pytest
from sqlalchemy import event

from app import models


def _build_backup_zip(items=None, extra_files=None) -> bytes:
    """Build an in-memory backup zip with the shape the restore endpoint expects."""
    payload = {
        "items": items or [],
        "created_at": datetime.utcnow().isoformat(),
        "version": "1.0",
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("data.json", json.dumps(payload))
        for name, content in (extra_files or {}).items():
            zf.writestr(name, content)
    return buf.getvalue()


def _upload_backup(client, auth_headers, zip_bytes, filename="backup.zip"):
    return client.post(
        "/api/backups/upload",
        files={"file": (filename, zip_bytes, "application/zip")},
        headers=auth_headers,
    )


def _persist_backup_record(db_session, user, zip_bytes, backup_dir):
    """Shortcut: put a real file on disk and insert a Backup row pointing at it."""
    backup_path = os.path.join(backup_dir, f"test_backup_{user.id}.zip")
    with open(backup_path, "wb") as fh:
        fh.write(zip_bytes)

    record = models.Backup(
        owner_id=user.id,
        filename=os.path.basename(backup_path),
        file_path=backup_path,
        size_bytes=os.path.getsize(backup_path),
        item_count=0,
        image_count=0,
        status="completed",
    )
    db_session.add(record)
    db_session.commit()
    db_session.refresh(record)
    return record


# ---------------------------------------------------------------------------
# Zip upload validation
# ---------------------------------------------------------------------------


def test_upload_rejects_non_zip_extension(client, auth_headers):
    resp = client.post(
        "/api/backups/upload",
        files={"file": ("backup.tar", b"not even trying", "application/octet-stream")},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert "zip" in resp.json()["detail"].lower()


def test_upload_rejects_renamed_non_zip(client, auth_headers):
    """File ends in .zip but isn't a zip. Must be rejected on magic bytes."""
    resp = _upload_backup(
        client, auth_headers, b"\x7fELF-pretending-to-be-a-zip", filename="evil.zip"
    )
    assert resp.status_code == 400
    assert "zip" in resp.json()["detail"].lower()


def test_upload_rejects_corrupted_zip(client, auth_headers):
    """Structurally recognized as a zip but a member is corrupted."""
    zip_bytes = _build_backup_zip()
    # Flip a byte inside the file payload to break CRC.
    corrupted = bytearray(zip_bytes)
    corrupted[40] ^= 0xFF
    resp = _upload_backup(
        client, auth_headers, bytes(corrupted), filename="corrupt.zip"
    )
    assert resp.status_code == 400


def test_upload_rejects_decompression_bomb(client, auth_headers, monkeypatch):
    """A zip whose uncompressed size exceeds the cap must be refused with 413."""
    from app.services import backups as backups_module

    monkeypatch.setattr(backups_module, "MAX_BACKUP_DECOMPRESSED_BYTES", 1024)
    # Build a zip with data.json containing >1KB of deflated-small content.
    big_items = [
        {"name": "x" * 200, "category": "C", "location": "L", "images": []}
    ] * 200
    zip_bytes = _build_backup_zip(items=big_items)

    resp = _upload_backup(client, auth_headers, zip_bytes, filename="bomb.zip")
    assert resp.status_code == 413


def test_upload_rejects_missing_data_json(client, auth_headers):
    """Zip is valid but doesn't contain the required data.json file."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("other.txt", "hello")
    resp = _upload_backup(client, auth_headers, buf.getvalue(), filename="no-data.zip")
    assert resp.status_code == 400


def test_upload_accepts_valid_zip(client, auth_headers):
    zip_bytes = _build_backup_zip(items=[])
    resp = _upload_backup(client, auth_headers, zip_bytes, filename="good.zip")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "completed"
    assert body["item_count"] == 0


# ---------------------------------------------------------------------------
# Error-detail leakage
# ---------------------------------------------------------------------------


def test_restore_does_not_leak_exception_details(
    client, auth_headers, user, db_session, monkeypatch
):
    """An internal exception during restore returns the generic message only."""
    # Create a valid backup record whose file will exist on disk.
    backup_dir = os.environ["BACKUP_DIR"]
    zip_bytes = _build_backup_zip(
        items=[
            {
                "name": "A",
                "category": "C",
                "location": "L",
                "brand": None,
                "model_number": None,
                "serial_number": None,
                "purchase_date": None,
                "purchase_price": None,
                "current_value": None,
                "warranty_expiration": None,
                "notes": None,
                "custom_fields": None,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "images": [],
            }
        ]
    )
    record = _persist_backup_record(db_session, user, zip_bytes, backup_dir)

    # Force an unexpected crash inside the restore path.
    from app.services import backups as backups_module

    def _blow_up(*args, **kwargs):
        raise RuntimeError("INTERNAL-SECRET-DO-NOT-LEAK-12345")

    monkeypatch.setattr(backups_module, "inspect_backup_zip", _blow_up)

    resp = client.post(
        f"/api/backups/{record.id}/restore?dry_run=true",
        headers=auth_headers,
    )
    assert resp.status_code == 500
    body_text = resp.text
    assert "INTERNAL-SECRET-DO-NOT-LEAK-12345" not in body_text
    assert "RuntimeError" not in body_text
    assert "Restore failed" in body_text


def test_upload_does_not_leak_exception_details(client, auth_headers, monkeypatch):
    from app.services import backups as backups_module

    def _blow_up(*args, **kwargs):
        raise RuntimeError("SENSITIVE-UPLOAD-DETAIL-98765")

    monkeypatch.setattr(backups_module, "inspect_backup_zip", _blow_up)

    resp = _upload_backup(client, auth_headers, _build_backup_zip(), filename="ok.zip")
    assert resp.status_code == 500
    assert "SENSITIVE-UPLOAD-DETAIL-98765" not in resp.text
    assert "RuntimeError" not in resp.text


# ---------------------------------------------------------------------------
# Destructive-restore gating (dry-run + confirm)
# ---------------------------------------------------------------------------


def _serialize_item(item: models.Item) -> dict:
    return {
        "id": str(item.id),
        "name": item.name,
        "category": item.category,
        "location": item.location,
        "brand": item.brand,
        "model_number": item.model_number,
        "serial_number": item.serial_number,
        "purchase_date": item.purchase_date.isoformat() if item.purchase_date else None,
        "purchase_price": item.purchase_price,
        "current_value": item.current_value,
        "warranty_expiration": item.warranty_expiration.isoformat()
        if item.warranty_expiration
        else None,
        "notes": item.notes,
        "custom_fields": item.custom_fields,
        "created_at": item.created_at.isoformat(),
        "updated_at": item.updated_at.isoformat(),
        "images": [],
    }


def test_restore_default_is_dry_run(client, auth_headers, user, db_session):
    """With no query params, restore MUST return a preview and not delete anything."""
    backup_dir = os.environ["BACKUP_DIR"]

    live_item = models.Item(
        owner_id=user.id,
        name="live",
        category="C",
        location="L",
    )
    db_session.add(live_item)
    db_session.commit()
    db_session.refresh(live_item)

    zip_bytes = _build_backup_zip(items=[_serialize_item(live_item)])
    record = _persist_backup_record(db_session, user, zip_bytes, backup_dir)

    resp = client.post(
        f"/api/backups/{record.id}/restore",
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["dry_run"] is True
    assert body["current_item_count"] == 1
    assert body["backup_item_count"] == 1

    # Item must still be present.
    assert (
        db_session.query(models.Item).filter(models.Item.owner_id == user.id).count()
        == 1
    )


def test_restore_commit_requires_confirm_count(client, auth_headers, user, db_session):
    backup_dir = os.environ["BACKUP_DIR"]
    zip_bytes = _build_backup_zip(items=[])
    record = _persist_backup_record(db_session, user, zip_bytes, backup_dir)

    resp = client.post(
        f"/api/backups/{record.id}/restore?dry_run=false",
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert "confirm_item_count" in resp.json()["detail"]


def test_restore_commit_rejects_stale_confirm(client, auth_headers, user, db_session):
    backup_dir = os.environ["BACKUP_DIR"]

    for name in ("one", "two", "three"):
        db_session.add(
            models.Item(owner_id=user.id, name=name, category="C", location="L")
        )
    db_session.commit()

    zip_bytes = _build_backup_zip(items=[])
    record = _persist_backup_record(db_session, user, zip_bytes, backup_dir)

    resp = client.post(
        f"/api/backups/{record.id}/restore?dry_run=false",
        headers=auth_headers,
        json={"confirm_item_count": 1},  # wrong — there are 3
    )
    assert resp.status_code == 409
    # User's items must still be intact.
    assert (
        db_session.query(models.Item).filter(models.Item.owner_id == user.id).count()
        == 3
    )


def test_restore_commit_with_correct_confirm_proceeds(
    client, auth_headers, user, db_session
):
    backup_dir = os.environ["BACKUP_DIR"]

    for name in ("one", "two"):
        db_session.add(
            models.Item(owner_id=user.id, name=name, category="C", location="L")
        )
    db_session.commit()

    # Backup contains a different single item.
    zip_bytes = _build_backup_zip(
        items=[
            {
                "name": "fresh",
                "category": "C",
                "location": "L",
                "brand": None,
                "model_number": None,
                "serial_number": None,
                "purchase_date": None,
                "purchase_price": None,
                "current_value": None,
                "warranty_expiration": None,
                "notes": None,
                "custom_fields": None,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "images": [],
            }
        ]
    )
    record = _persist_backup_record(db_session, user, zip_bytes, backup_dir)

    resp = client.post(
        f"/api/backups/{record.id}/restore?dry_run=false",
        headers=auth_headers,
        json={"confirm_item_count": 2},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["dry_run"] is False
    assert body["items_restored"] == 1

    # Must have swapped the old 2 items for the 1 from the backup.
    db_session.expire_all()
    remaining = [
        i.name
        for i in db_session.query(models.Item)
        .filter(models.Item.owner_id == user.id)
        .all()
    ]
    assert remaining == ["fresh"]


def test_backup_create_and_restore_round_trip_with_images(
    client, auth_headers, user, db_session
):
    """End-to-end regression guard for two linked bugs caught in the v3.1 validation pass:

    * Backup create used to resolve ``ItemImage.file_path`` (a relative
      URL-style path like ``uploads/foo.jpg``) directly from CWD instead
      of ``settings.upload_path`` — so images were silently dropped from
      archives. Round-trip zips came out 670 bytes regardless of content.
    * Commit-restore used bulk ``DELETE FROM items`` with
      ``synchronize_session=False`` which bypasses ORM cascade; on
      Postgres (where FKs are enforced) the DELETE raised
      ``ForeignKeyViolation`` as long as any ``item_images`` row
      referenced the item. SQLite hid it because its FKs are off by
      default.

    This test exercises the full create → verify zip contents → wipe →
    restore → verify round trip with real files on disk.
    """
    upload_dir = os.environ["UPLOAD_DIR"]

    # Seed 2 items, 1 with an image on disk, 1 without.
    item_with_image = models.Item(
        owner_id=user.id, name="with-image", category="C", location="L"
    )
    item_blank = models.Item(
        owner_id=user.id, name="blank", category="C", location="L"
    )
    db_session.add_all([item_with_image, item_blank])
    db_session.flush()

    # Minimal JPEG — real magic-byte prefix so any validation layer is happy.
    jpeg_bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00" + (b"\x00" * 64) + b"\xff\xd9"
    image_filename = f"roundtrip_{item_with_image.id}.jpg"
    on_disk_path = os.path.join(upload_dir, image_filename)
    with open(on_disk_path, "wb") as fh:
        fh.write(jpeg_bytes)

    db_session.add(
        models.ItemImage(
            item_id=item_with_image.id,
            filename=image_filename,
            # file_path mirrors what the live upload handler stamps — a
            # relative URL for the frontend, not an on-disk locator.
            file_path=f"uploads/{image_filename}",
        )
    )
    db_session.commit()

    # Step 1 — create backup.
    resp = client.post("/api/backups", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    backup = resp.json()
    backup_id = backup["id"]
    backup_path = backup["file_path"]
    assert backup["item_count"] == 2
    assert backup["image_count"] == 1, "DB-side image count should include the one image"

    # Step 2 — verify the zip actually contains the image bytes. This is
    # the F5 regression guard — a pre-fix backup archive was <1 KB for any
    # item set because the image was silently skipped.
    with zipfile.ZipFile(backup_path, "r") as zf:
        names = zf.namelist()
        assert f"images/{image_filename}" in names, (
            f"image not packaged into backup; names={names}"
        )
        with zf.open(f"images/{image_filename}") as fh:
            assert fh.read() == jpeg_bytes
        with zf.open("data.json") as fh:
            data = json.loads(fh.read().decode())
    packaged_image_count = sum(len(it.get("images") or []) for it in data["items"])
    assert packaged_image_count == 1, (
        f"item_data.images lost its image reference; data={data}"
    )

    # Step 3 — wipe the image file from disk + wipe DB via commit_restore.
    # Restore should cleanly delete the old rows (item_images first, then
    # items — F3 regression guard) and repopulate from the archive.
    os.remove(on_disk_path)
    resp = client.post(
        f"/api/backups/{backup_id}/restore?dry_run=false",
        headers=auth_headers,
        json={"confirm_item_count": 2},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["items_restored"] == 2
    assert body["images_restored"] == 1

    # Step 4 — verify state: 2 restored items, 1 restored image row + file.
    db_session.expire_all()
    restored_items = (
        db_session.query(models.Item).filter(models.Item.owner_id == user.id).all()
    )
    assert {i.name for i in restored_items} == {"with-image", "blank"}

    restored_image_count = (
        db_session.query(models.ItemImage)
        .join(models.Item, models.Item.id == models.ItemImage.item_id)
        .filter(models.Item.owner_id == user.id)
        .count()
    )
    assert restored_image_count == 1

    assert os.path.exists(on_disk_path), (
        "restored image file should be back on disk at the original location"
    )
    with open(on_disk_path, "rb") as fh:
        assert fh.read() == jpeg_bytes


# ---------------------------------------------------------------------------
# N+1 elimination
# ---------------------------------------------------------------------------


@pytest.fixture
def query_counter(engine):
    """Captures every SQL statement executed on the test engine."""
    stmts: list[str] = []

    def _before(conn, cursor, statement, parameters, context, executemany):
        stmts.append(statement)

    event.listen(engine, "before_cursor_execute", _before)
    yield stmts
    event.remove(engine, "before_cursor_execute", _before)


def test_backup_create_does_not_n_plus_one(
    client, auth_headers, user, db_session, query_counter
):
    """20 items × 3 images must not turn into 20 separate image SELECTs."""
    for i in range(20):
        item = models.Item(
            owner_id=user.id,
            name=f"item {i}",
            category="C",
            location="L",
        )
        db_session.add(item)
        db_session.flush()
        for j in range(3):
            db_session.add(
                models.ItemImage(
                    item_id=item.id,
                    filename=f"img_{i}_{j}.png",
                    file_path=f"uploads/img_{i}_{j}.png",
                )
            )
    db_session.commit()

    query_counter.clear()
    resp = client.post("/api/backups", headers=auth_headers)
    assert resp.status_code == 200, resp.text

    image_selects = [
        s for s in query_counter if "FROM item_images" in s and "SELECT" in s.upper()
    ]
    # With eager loading we expect at most 1 image SELECT (the selectinload
    # batch). Without it we'd see 20+.
    assert len(image_selects) <= 2, (
        f"Suspected N+1: saw {len(image_selects)} image SELECTs "
        f"for 20 items with 3 images each"
    )
