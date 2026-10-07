"""Unit tests for ``services.backups.BackupService``.

These tests drive the service directly with a real ``db_session`` (no
TestClient) so the business rules can be exercised without HTTP wiring.
HTTP-level coverage stays in ``tests/test_backups.py``.
"""

from __future__ import annotations

import io
import json
import os
import zipfile

import pytest
from fastapi import HTTPException

from app import models, security
from app.services.backups import (
    BackupService,
    inspect_backup_zip,
)
from app.utctime import utcnow


def _build_backup_zip(items=None) -> bytes:
    payload = {
        "items": items or [],
        "created_at": utcnow().isoformat(),
        "version": "1.0",
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("data.json", json.dumps(payload))
    return buf.getvalue()


def _item_dict(**overrides):
    base = {
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
        "created_at": utcnow().isoformat(),
        "updated_at": utcnow().isoformat(),
        "images": [],
    }
    base.update(overrides)
    return base


def _persist_backup_record(db_session, user, zip_bytes):
    backup_dir = os.environ["BACKUP_DIR"]
    backup_path = os.path.join(backup_dir, f"svc_backup_{user.id}.zip")
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


@pytest.fixture
def other_user(db_session) -> models.User:
    u = models.User(
        email="bob@example.com",
        username="bob",
        hashed_password=security.get_password_hash("correct-horse-battery-staple"),
        is_active=True,
    )
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


# ---------------------------------------------------------------------------
# inspect_backup_zip — module-level validator
# ---------------------------------------------------------------------------


def test_inspect_accepts_valid_zip(tmp_path):
    zip_bytes = _build_backup_zip()
    p = tmp_path / "ok.zip"
    p.write_bytes(zip_bytes)
    total = inspect_backup_zip(str(p))
    assert total > 0


def test_inspect_rejects_renamed_non_zip(tmp_path):
    p = tmp_path / "evil.zip"
    p.write_bytes(b"\x7fELF-pretending-to-be-a-zip")
    with pytest.raises(HTTPException) as exc_info:
        inspect_backup_zip(str(p))
    assert exc_info.value.status_code == 400


def test_inspect_rejects_decompression_bomb(tmp_path, monkeypatch):
    from app.services import backups as backups_module

    monkeypatch.setattr(backups_module, "MAX_BACKUP_DECOMPRESSED_BYTES", 64)
    big_items = [_item_dict(name="x" * 200)] * 100
    zip_bytes = _build_backup_zip(items=big_items)
    p = tmp_path / "bomb.zip"
    p.write_bytes(zip_bytes)
    with pytest.raises(HTTPException) as exc_info:
        inspect_backup_zip(str(p))
    assert exc_info.value.status_code == 413


# ---------------------------------------------------------------------------
# BackupService.create
# ---------------------------------------------------------------------------


def test_create_produces_completed_backup(db_session, user):
    # Give the user some items.
    for name in ("a", "b", "c"):
        db_session.add(
            models.Item(owner_id=user.id, name=name, category="C", location="L")
        )
    db_session.commit()

    svc = BackupService(db_session, user)
    backup = svc.create()

    assert backup.status == "completed"
    assert backup.item_count == 3
    assert backup.image_count == 0
    assert os.path.exists(backup.file_path)


def test_create_only_includes_own_items(db_session, user, other_user):
    db_session.add(
        models.Item(owner_id=user.id, name="alice-item", category="C", location="L")
    )
    db_session.add(
        models.Item(owner_id=other_user.id, name="bob-item", category="C", location="L")
    )
    db_session.commit()

    alice_backup = BackupService(db_session, user).create()
    assert alice_backup.item_count == 1

    # Verify by opening the zip and inspecting data.json.
    with zipfile.ZipFile(alice_backup.file_path, "r") as zf, zf.open("data.json") as f:
        data = json.loads(f.read())
    names = [i["name"] for i in data["items"]]
    assert names == ["alice-item"]


# ---------------------------------------------------------------------------
# BackupService.list
# ---------------------------------------------------------------------------


def test_list_returns_only_own_backups(db_session, user, other_user):
    _persist_backup_record(db_session, user, _build_backup_zip())
    _persist_backup_record(db_session, other_user, _build_backup_zip())

    alice_list = BackupService(db_session, user).list()
    assert len(alice_list) == 1
    assert alice_list[0].owner_id == user.id


def test_list_filters_incomplete_records(db_session, user):
    # A record missing required fields should not appear in list().
    ghost = models.Backup(owner_id=user.id, status="in_progress")
    db_session.add(ghost)
    db_session.commit()

    _persist_backup_record(db_session, user, _build_backup_zip())

    listed = BackupService(db_session, user).list()
    assert len(listed) == 1


# ---------------------------------------------------------------------------
# BackupService.preview_restore / commit_restore
# ---------------------------------------------------------------------------


def test_preview_restore_is_non_destructive(db_session, user):
    for name in ("alpha", "beta"):
        db_session.add(
            models.Item(owner_id=user.id, name=name, category="C", location="L")
        )
    db_session.commit()

    zip_bytes = _build_backup_zip(items=[_item_dict(name="imported")])
    record = _persist_backup_record(db_session, user, zip_bytes)

    svc = BackupService(db_session, user)
    preview = svc.preview_restore(record.id)

    assert preview["dry_run"] is True
    assert preview["current_item_count"] == 2
    assert preview["backup_item_count"] == 1
    # Nothing was deleted.
    remaining = [
        i.name
        for i in db_session.query(models.Item)
        .filter(models.Item.owner_id == user.id)
        .all()
    ]
    assert set(remaining) == {"alpha", "beta"}


def test_commit_restore_requires_confirm(db_session, user):
    record = _persist_backup_record(db_session, user, _build_backup_zip())
    svc = BackupService(db_session, user)
    with pytest.raises(HTTPException) as exc_info:
        svc.commit_restore(record.id, confirm_item_count=None)
    assert exc_info.value.status_code == 400


def test_commit_restore_rejects_stale_confirm(db_session, user):
    for name in ("one", "two", "three"):
        db_session.add(
            models.Item(owner_id=user.id, name=name, category="C", location="L")
        )
    db_session.commit()

    record = _persist_backup_record(db_session, user, _build_backup_zip())

    svc = BackupService(db_session, user)
    with pytest.raises(HTTPException) as exc_info:
        svc.commit_restore(record.id, confirm_item_count=1)
    assert exc_info.value.status_code == 409

    # User's items must still exist.
    assert (
        db_session.query(models.Item).filter(models.Item.owner_id == user.id).count()
        == 3
    )


def test_commit_restore_with_correct_confirm(db_session, user):
    for name in ("one", "two"):
        db_session.add(
            models.Item(owner_id=user.id, name=name, category="C", location="L")
        )
    db_session.commit()

    zip_bytes = _build_backup_zip(items=[_item_dict(name="fresh")])
    record = _persist_backup_record(db_session, user, zip_bytes)

    svc = BackupService(db_session, user)
    result = svc.commit_restore(record.id, confirm_item_count=2)

    assert result["items_restored"] == 1
    db_session.expire_all()
    remaining = [
        i.name
        for i in db_session.query(models.Item)
        .filter(models.Item.owner_id == user.id)
        .all()
    ]
    assert remaining == ["fresh"]


def test_restore_cross_user_is_404(db_session, user, other_user):
    record = _persist_backup_record(db_session, user, _build_backup_zip())

    other_svc = BackupService(db_session, other_user)
    with pytest.raises(HTTPException) as exc_info:
        other_svc.preview_restore(record.id)
    assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# BackupService.upload
# ---------------------------------------------------------------------------


def test_upload_rejects_non_zip_extension(db_session, user, tmp_path):
    svc = BackupService(db_session, user)
    staged = tmp_path / "backup.tar"
    staged.write_bytes(b"not even trying")
    with pytest.raises(HTTPException) as exc_info:
        svc.upload("backup.tar", str(staged))
    assert exc_info.value.status_code == 400


def test_upload_accepts_valid_zip(db_session, user, tmp_path):
    svc = BackupService(db_session, user)
    staged = tmp_path / "good.zip"
    staged.write_bytes(_build_backup_zip(items=[_item_dict()]))
    backup = svc.upload("good.zip", str(staged))
    assert backup.item_count == 1
    assert backup.status == "completed"


def test_upload_rejects_renamed_non_zip(db_session, user, tmp_path):
    svc = BackupService(db_session, user)
    staged = tmp_path / "evil.zip"
    staged.write_bytes(b"\x7fELF")
    with pytest.raises(HTTPException) as exc_info:
        svc.upload("evil.zip", str(staged))
    assert exc_info.value.status_code == 400
    # Staged file should have been cleaned up by the service.
    backup_dir = os.environ["BACKUP_DIR"]
    assert not os.path.exists(os.path.join(backup_dir, "evil.zip"))


# ---------------------------------------------------------------------------
# BackupService.delete / get_download_path
# ---------------------------------------------------------------------------


def test_delete_removes_row_and_file(db_session, user):
    record = _persist_backup_record(db_session, user, _build_backup_zip())
    file_path = record.file_path
    assert os.path.exists(file_path)

    BackupService(db_session, user).delete(record.id)
    assert db_session.get(models.Backup, record.id) is None
    assert not os.path.exists(file_path)


def test_delete_cross_user_is_404(db_session, user, other_user):
    record = _persist_backup_record(db_session, user, _build_backup_zip())
    with pytest.raises(HTTPException) as exc_info:
        BackupService(db_session, other_user).delete(record.id)
    assert exc_info.value.status_code == 404
    # Alice's backup must still exist.
    assert db_session.get(models.Backup, record.id) is not None


def test_get_download_path_returns_path_for_own_backup(db_session, user):
    record = _persist_backup_record(db_session, user, _build_backup_zip())
    backup, path = BackupService(db_session, user).get_download_path(record.id)
    assert backup.id == record.id
    assert path.exists()


def test_get_download_path_cross_user_is_404(db_session, user, other_user):
    record = _persist_backup_record(db_session, user, _build_backup_zip())
    with pytest.raises(HTTPException) as exc_info:
        BackupService(db_session, other_user).get_download_path(record.id)
    assert exc_info.value.status_code == 404


def test_get_download_path_when_file_missing_is_404(db_session, user):
    record = _persist_backup_record(db_session, user, _build_backup_zip())
    os.remove(record.file_path)
    with pytest.raises(HTTPException) as exc_info:
        BackupService(db_session, user).get_download_path(record.id)
    assert exc_info.value.status_code == 404
