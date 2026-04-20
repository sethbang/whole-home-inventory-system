"""Rate-limiting tests.

slowapi is wired up with per-route limits on login, backup create,
backup restore, and items export. These tests hit each limit to prove
that throttling kicks in and returns a generic 429 (no policy leak),
and that the limiter's user-aware key func is working.

Note: slowapi's default ``Limiter`` stores counters on the Limiter
instance's in-memory storage, which persists across requests within a
process. Tests use a ``clean_limiter`` fixture to reset counters
between tests so the cross-test interaction stays predictable.
"""

from __future__ import annotations

import pytest

from app import models, security
from app.rate_limit import limiter, rate_limit_key


@pytest.fixture(autouse=True)
def clean_limiter():
    """Reset in-memory limit counters between tests."""
    limiter.reset()
    yield
    limiter.reset()


# ---------------------------------------------------------------------------
# rate_limit_key behavior
# ---------------------------------------------------------------------------


def test_rate_limit_key_prefers_user_when_token_valid(user):
    """With a valid bearer token the key should be user:<username>."""
    from starlette.requests import Request as StarletteRequest

    token = security.create_access_token(data={"sub": user.username})
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/whatever",
        "headers": [(b"authorization", f"Bearer {token}".encode())],
        "client": ("10.0.0.1", 1234),
    }
    req = StarletteRequest(scope)
    assert rate_limit_key(req) == f"user:{user.username}"


def test_rate_limit_key_falls_back_to_ip_on_invalid_token():
    """Invalid token must NOT raise and must fall through to IP-keyed."""
    from starlette.requests import Request as StarletteRequest

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/whatever",
        "headers": [(b"authorization", b"Bearer not.a.valid.jwt")],
        "client": ("10.0.0.1", 1234),
    }
    req = StarletteRequest(scope)
    key = rate_limit_key(req)
    assert key.startswith("ip:")


def test_rate_limit_key_is_ip_for_unauth_requests():
    from starlette.requests import Request as StarletteRequest

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/whatever",
        "headers": [],
        "client": ("203.0.113.42", 80),
    }
    req = StarletteRequest(scope)
    assert rate_limit_key(req) == "ip:203.0.113.42"


# ---------------------------------------------------------------------------
# Login throttle (5/min/IP)
# ---------------------------------------------------------------------------


def test_login_throttles_after_five_attempts(client):
    # 5 failed attempts are allowed, the 6th is rate-limited regardless
    # of whether it would otherwise succeed or fail.
    for _ in range(5):
        resp = client.post(
            "/api/token",
            data={"username": "nobody", "password": "x"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert resp.status_code == 401

    resp = client.post(
        "/api/token",
        data={"username": "nobody", "password": "x"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 429
    # Must be the generic scrubbed message — no policy leak.
    body = resp.json()
    assert "429" not in body.get("detail", "") and "1/min" not in body.get("detail", "")
    assert "try again later" in body["detail"].lower()


# ---------------------------------------------------------------------------
# Items export throttle (10/hour/user)
# ---------------------------------------------------------------------------


def test_items_export_throttles_after_ten_requests(client, auth_headers):
    for _ in range(10):
        resp = client.get("/api/items/export/data?format=json", headers=auth_headers)
        assert resp.status_code == 200

    resp = client.get("/api/items/export/data?format=json", headers=auth_headers)
    assert resp.status_code == 429


def test_items_export_counters_are_per_user(client, user, auth_headers, db_session):
    """Two users on the same IP must NOT share each other's export budget."""
    # Alice burns through her 10.
    for _ in range(10):
        resp = client.get("/api/items/export/data?format=json", headers=auth_headers)
        assert resp.status_code == 200

    # Bob (different user) should still have a fresh budget.
    bob = models.User(
        email="bob@example.com",
        username="bob",
        hashed_password=security.get_password_hash("correct-horse-battery-staple"),
        is_active=True,
    )
    db_session.add(bob)
    db_session.commit()
    db_session.refresh(bob)
    bob_token = security.create_access_token(data={"sub": bob.username})
    bob_headers = {"Authorization": f"Bearer {bob_token}"}

    resp = client.get("/api/items/export/data?format=json", headers=bob_headers)
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Backup restore throttle (3/hour/user)
# ---------------------------------------------------------------------------


def test_backup_restore_throttles_after_three_requests(
    client, auth_headers, user, db_session
):
    import io
    import json
    import os
    import zipfile
    from datetime import datetime

    # Seed a real backup so restore can find it.
    backup_dir = os.environ["BACKUP_DIR"]
    payload = {
        "items": [],
        "created_at": datetime.utcnow().isoformat(),
        "version": "1.0",
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("data.json", json.dumps(payload))
    zip_bytes = buf.getvalue()

    path = os.path.join(backup_dir, f"rate_backup_{user.id}.zip")
    with open(path, "wb") as fh:
        fh.write(zip_bytes)

    record = models.Backup(
        owner_id=user.id,
        filename=os.path.basename(path),
        file_path=path,
        size_bytes=os.path.getsize(path),
        item_count=0,
        image_count=0,
        status="completed",
    )
    db_session.add(record)
    db_session.commit()
    db_session.refresh(record)

    # 3 previews allowed, 4th rate-limited.
    for _ in range(3):
        resp = client.post(
            f"/api/backups/{record.id}/restore?dry_run=true",
            headers=auth_headers,
        )
        assert resp.status_code == 200

    resp = client.post(
        f"/api/backups/{record.id}/restore?dry_run=true",
        headers=auth_headers,
    )
    assert resp.status_code == 429
