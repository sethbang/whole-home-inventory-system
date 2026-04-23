"""v3.0 Part D: ARQ-enqueued paths for backup create + restore.

The stub_arq_pool fixture attaches a mock pool to app.state so the
router's "if pool is not None" branch fires. The pool's enqueue_job
returns a stub Job whose job_id we assert against.
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock

import pytest

from app import models
from app.main import app


@pytest.fixture
def stub_arq_pool_with_enqueue():
    """Pool that returns a canned ``job_id`` from enqueue_job."""
    pool = MagicMock()
    pool.close = AsyncMock(return_value=None)
    fake_job = MagicMock()
    fake_job.job_id = "stub-job-id-42"
    pool.enqueue_job = AsyncMock(return_value=fake_job)
    app.state.arq = pool
    try:
        yield pool
    finally:
        app.state.arq = None


@pytest.fixture
def stub_arq_pool_enqueue_fails():
    """Pool that raises from enqueue_job — triggers the sync fallback."""
    pool = MagicMock()
    pool.close = AsyncMock(return_value=None)
    pool.enqueue_job = AsyncMock(side_effect=RuntimeError("redis unavailable"))
    app.state.arq = pool
    try:
        yield pool
    finally:
        app.state.arq = None


# ---------------------------------------------------------------------------
# POST /backups
# ---------------------------------------------------------------------------


def test_backup_create_returns_job_reference_when_pool_active(
    client, auth_headers, stub_arq_pool_with_enqueue, user
):
    resp = client.post("/api/backups", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body == {"kind": "job", "job_id": "stub-job-id-42"}

    # Worker was asked to process a backup for the right user.
    stub_arq_pool_with_enqueue.enqueue_job.assert_awaited_once()
    call = stub_arq_pool_with_enqueue.enqueue_job.await_args
    assert call.args[0] == "backup_create"
    assert call.kwargs["user_id"] == str(user.id)


def test_backup_create_falls_back_to_sync_when_pool_missing(
    client, auth_headers, user, db_session
):
    """Default posture (no pool) still produces a Backup row inline."""
    app.state.arq = None
    resp = client.post("/api/backups", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # Sync path returns a Backup resource; no discriminator.
    assert "kind" not in body
    assert body["owner_id"] == str(user.id)
    assert body["status"] == "completed"


def test_backup_create_falls_back_when_enqueue_raises(
    client, auth_headers, user, stub_arq_pool_enqueue_fails
):
    """Broken Redis shouldn't block a user from creating a backup."""
    resp = client.post("/api/backups", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "kind" not in body
    assert body["status"] == "completed"
    stub_arq_pool_enqueue_fails.enqueue_job.assert_awaited_once()


# ---------------------------------------------------------------------------
# POST /backups/{id}/restore
# ---------------------------------------------------------------------------


def _seed_existing_backup(db_session, user):
    """Create a real zip on disk that points at a real Backup row."""
    import io
    import json
    import zipfile

    from app.services.backups import _backup_dir

    backup_dir = _backup_dir()
    os.makedirs(backup_dir, exist_ok=True)
    zip_path = os.path.join(backup_dir, f"backup-async-{user.id}.zip")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "data.json",
            json.dumps(
                {"items": [], "version": "1.0", "created_at": "2026-04-22T00:00:00"}
            ),
        )
    with open(zip_path, "wb") as f:
        f.write(buf.getvalue())

    backup = models.Backup(
        owner_id=user.id,
        filename=os.path.basename(zip_path),
        file_path=zip_path,
        size_bytes=os.path.getsize(zip_path),
        item_count=0,
        image_count=0,
        status="completed",
    )
    db_session.add(backup)
    db_session.commit()
    db_session.refresh(backup)
    return backup


def test_backup_restore_dry_run_never_enqueues(
    client, auth_headers, user, db_session, stub_arq_pool_with_enqueue
):
    """Dry-run is cheap — always runs inline, even with a pool active."""
    backup = _seed_existing_backup(db_session, user)
    resp = client.post(
        f"/api/backups/{backup.id}/restore",
        headers=auth_headers,
        params={"dry_run": "true"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["dry_run"] is True
    stub_arq_pool_with_enqueue.enqueue_job.assert_not_awaited()


def test_backup_restore_commit_returns_job_reference_when_pool_active(
    client, auth_headers, user, db_session, stub_arq_pool_with_enqueue
):
    backup = _seed_existing_backup(db_session, user)
    resp = client.post(
        f"/api/backups/{backup.id}/restore",
        headers=auth_headers,
        params={"dry_run": "false"},
        json={"confirm_item_count": 0},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body == {"kind": "job", "job_id": "stub-job-id-42"}

    stub_arq_pool_with_enqueue.enqueue_job.assert_awaited_once()
    call = stub_arq_pool_with_enqueue.enqueue_job.await_args
    assert call.args[0] == "backup_restore"
    assert call.kwargs["user_id"] == str(user.id)
    assert call.kwargs["backup_id"] == str(backup.id)
    assert call.kwargs["confirm_item_count"] == 0


def test_backup_restore_validates_before_enqueuing(
    client, auth_headers, user, db_session, stub_arq_pool_with_enqueue
):
    """A stale confirm_item_count must fail fast, not buried in a worker job."""
    backup = _seed_existing_backup(db_session, user)
    resp = client.post(
        f"/api/backups/{backup.id}/restore",
        headers=auth_headers,
        params={"dry_run": "false"},
        json={"confirm_item_count": 999},  # wrong; actual is 0
    )
    assert resp.status_code == 409
    # Router short-circuits on validation — no job is enqueued.
    stub_arq_pool_with_enqueue.enqueue_job.assert_not_awaited()


def test_backup_restore_commit_sync_fallback(
    client, auth_headers, user, db_session
):
    app.state.arq = None
    backup = _seed_existing_backup(db_session, user)
    resp = client.post(
        f"/api/backups/{backup.id}/restore",
        headers=auth_headers,
        params={"dry_run": "false"},
        json={"confirm_item_count": 0},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "kind" not in body
    assert body["success"] is True
    assert body["dry_run"] is False
