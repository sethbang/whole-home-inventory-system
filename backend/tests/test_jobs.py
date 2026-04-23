"""Tests for the ARQ pool + GET /api/jobs/{job_id} endpoint.

The actual workers aren't booted under pytest — we test the request
path by plugging a stub pool onto ``app.state.arq`` and monkey-patching
the ``Job`` class so status/result calls return canned answers. This
exercises: the 503-when-not-configured path, the 404 on unknown/other-
user jobs, the ownership guard, and the status mapping.
"""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from arq.jobs import DeserializationError, JobStatus as ArqJobStatus

from app.jobs.client import _redis_settings_from_url
from app.main import app


@pytest.fixture
def stub_arq_pool():
    """Attach a stub ARQ pool to app.state for the duration of a test.

    The pool only needs to be truthy (routes check `is None`) and own a
    ``close()`` async method so FastAPI's lifespan teardown doesn't
    explode after the TestClient's ``with`` block exits.
    """
    pool = MagicMock()
    pool.close = AsyncMock(return_value=None)
    app.state.arq = pool
    try:
        yield pool
    finally:
        app.state.arq = None


def test_redis_settings_parses_plain_url():
    s = _redis_settings_from_url("redis://localhost:6379/0")
    assert s.host == "localhost"
    assert s.port == 6379
    assert s.database == 0
    assert s.ssl is False
    assert s.password is None


def test_redis_settings_parses_auth_and_tls():
    s = _redis_settings_from_url("rediss://:secret@redis.internal:6380/3")
    assert s.host == "redis.internal"
    assert s.port == 6380
    assert s.database == 3
    assert s.password == "secret"
    assert s.ssl is True


def test_redis_settings_rejects_bad_scheme():
    with pytest.raises(ValueError):
        _redis_settings_from_url("http://redis.internal:6379/0")


def test_redis_settings_rejects_non_integer_db():
    with pytest.raises(ValueError):
        _redis_settings_from_url("redis://localhost:6379/not-a-number")


def test_jobs_endpoint_503_when_unconfigured(client, auth_headers):
    """Default dev stack has no ARQ pool — endpoint surfaces 503."""
    app.state.arq = None
    resp = client.get("/api/jobs/any-id", headers=auth_headers)
    assert resp.status_code == 503
    assert "REDIS_URL" in resp.json()["detail"]


def test_jobs_endpoint_404_on_unknown_job(client, auth_headers, stub_arq_pool):
    with patch("app.routers.jobs.Job") as MockJob:
        mock = MockJob.return_value
        mock.status = AsyncMock(return_value=ArqJobStatus.not_found)

        resp = client.get("/api/jobs/missing", headers=auth_headers)
    assert resp.status_code == 404


def test_jobs_endpoint_returns_queued_status(client, auth_headers, user, stub_arq_pool):
    with patch("app.routers.jobs.Job") as MockJob:
        mock = MockJob.return_value
        mock.status = AsyncMock(return_value=ArqJobStatus.queued)
        mock.info = AsyncMock(
            return_value=SimpleNamespace(
                kwargs={"user_id": str(user.id)},
                enqueue_time=datetime(2026, 4, 22, 10, 0, 0, tzinfo=timezone.utc),
                start_time=None,
            )
        )

        resp = client.get("/api/jobs/abc123", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["job_id"] == "abc123"
    assert body["status"] == "queued"
    assert body["result"] is None
    assert body["error"] is None


def test_jobs_endpoint_rejects_cross_user_job(client, auth_headers, stub_arq_pool):
    """A job belonging to another user returns 404 (not 403) to avoid leaking existence."""
    with patch("app.routers.jobs.Job") as MockJob:
        mock = MockJob.return_value
        mock.status = AsyncMock(return_value=ArqJobStatus.queued)
        mock.info = AsyncMock(
            return_value=SimpleNamespace(
                kwargs={"user_id": "11111111-1111-1111-1111-111111111111"},
                enqueue_time=None,
                start_time=None,
            )
        )

        resp = client.get("/api/jobs/not-mine", headers=auth_headers)
    assert resp.status_code == 404


def test_jobs_endpoint_returns_complete_result(client, auth_headers, user, stub_arq_pool):
    with patch("app.routers.jobs.Job") as MockJob:
        mock = MockJob.return_value
        mock.status = AsyncMock(return_value=ArqJobStatus.complete)
        mock.info = AsyncMock(
            return_value=SimpleNamespace(
                kwargs={"user_id": str(user.id)},
                enqueue_time=datetime(2026, 4, 22, 10, 0, 0, tzinfo=timezone.utc),
                start_time=datetime(2026, 4, 22, 10, 0, 5, tzinfo=timezone.utc),
            )
        )
        mock.result_info = AsyncMock(
            return_value=SimpleNamespace(
                success=True,
                result={"backup_id": "b-123", "size_bytes": 10240},
                finish_time=datetime(2026, 4, 22, 10, 0, 35, tzinfo=timezone.utc),
            )
        )

        resp = client.get("/api/jobs/done", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "complete"
    assert body["result"] == {"backup_id": "b-123", "size_bytes": 10240}
    assert body["error"] is None


def test_jobs_endpoint_surfaces_failure(client, auth_headers, user, stub_arq_pool):
    with patch("app.routers.jobs.Job") as MockJob:
        mock = MockJob.return_value
        mock.status = AsyncMock(return_value=ArqJobStatus.complete)
        mock.info = AsyncMock(
            return_value=SimpleNamespace(
                kwargs={"user_id": str(user.id)},
                enqueue_time=None,
                start_time=None,
            )
        )
        mock.result_info = AsyncMock(
            return_value=SimpleNamespace(
                success=False,
                result=RuntimeError("disk full"),
                finish_time=datetime(2026, 4, 22, 10, 0, 35, tzinfo=timezone.utc),
            )
        )

        resp = client.get("/api/jobs/failed", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "failed"
    assert body["result"] is None
    assert "disk full" in body["error"]


def test_jobs_endpoint_unwraps_http_exception_envelope(
    client, auth_headers, user, stub_arq_pool
):
    """Tasks that catch HTTPException return ``{ok: False, status_code, error}``
    instead of re-raising (F10b). The router promotes that shape into a
    ``failed`` JobDetail with the status code prefixed onto the error string,
    so the polling client gets the same surface as a real exception result.
    """
    with patch("app.routers.jobs.Job") as MockJob:
        mock = MockJob.return_value
        mock.status = AsyncMock(return_value=ArqJobStatus.complete)
        mock.info = AsyncMock(
            return_value=SimpleNamespace(
                kwargs={"user_id": str(user.id)},
                enqueue_time=None,
                start_time=None,
            )
        )
        mock.result_info = AsyncMock(
            return_value=SimpleNamespace(
                success=True,
                result={
                    "ok": False,
                    "error": "Daily vision budget exceeded",
                    "status_code": 402,
                },
                finish_time=datetime(2026, 4, 22, 10, 0, 35, tzinfo=timezone.utc),
            )
        )

        resp = client.get("/api/jobs/budget", headers=auth_headers)

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "failed"
    assert body["result"] is None
    assert body["error"] == "402: Daily vision budget exceeded"


def test_jobs_endpoint_handles_deserialization_error(
    client, auth_headers, user, stub_arq_pool
):
    """If ARQ can't unpickle the task result, surface as a failed JobDetail
    instead of crashing the polling endpoint with a 500. Defense in depth
    for any future un-picklable exception type the task layer doesn't
    explicitly catch.
    """
    with patch("app.routers.jobs.Job") as MockJob:
        mock = MockJob.return_value
        mock.status = AsyncMock(return_value=ArqJobStatus.complete)
        mock.info = AsyncMock(
            return_value=SimpleNamespace(
                kwargs={"user_id": str(user.id)},
                enqueue_time=None,
                start_time=None,
            )
        )
        mock.result_info = AsyncMock(
            side_effect=DeserializationError("unable to deserialize job result")
        )

        resp = client.get("/api/jobs/poisoned", headers=auth_headers)

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "failed"
    assert body["result"] is None
    assert "un-deserializable" in body["error"]
