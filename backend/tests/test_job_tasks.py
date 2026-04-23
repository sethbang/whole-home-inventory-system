"""Tests for ARQ task wrappers in ``app/jobs/tasks/`` (F10b regression).

The wrappers translate service-layer ``HTTPException`` into a serializable
``{ok: False, error, status_code}`` dict so the result survives ARQ's
pickle-based result store. Without this, polling ``GET /api/jobs/{id}``
crashed with ``DeserializationError`` because Starlette's ``HTTPException``
``__init__`` is kwargs-only and doesn't round-trip cleanly.

These tests drive each task with a stubbed service to assert the
translation happens, and that successful results pass through unchanged.
"""

from __future__ import annotations

import asyncio
import io
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from PIL import Image

from app import models, security


def _png_bytes(size=(32, 32)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color="red").save(buf, format="PNG")
    return buf.getvalue()


def _b64_png() -> str:
    import base64

    return base64.b64encode(_png_bytes()).decode("ascii")


@pytest.fixture
def task_user(db_session) -> models.User:
    """A user the task can resolve from its own SessionLocal-opened session.

    Tasks open their own DB session via SessionLocal, not the test fixture
    session. Committing the user lets a fresh session find them.
    """
    u = models.User(
        email="task@example.com",
        username="task",
        hashed_password=security.get_password_hash("Password1!"),
        is_active=True,
    )
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


@pytest.fixture
def patch_task_session(testing_session_local):
    """Point vision/pricing task SessionLocal at the test engine.

    The task code calls ``SessionLocal()`` from ``app.database`` directly,
    which is bound to a different in-memory SQLite DB than the test
    fixtures (each in-memory SQLite is per-connection). Patching the
    module-level reference inside each task module redirects it to the
    sessionmaker that the test fixtures use.
    """
    with patch("app.jobs.tasks.vision.SessionLocal", testing_session_local), patch(
        "app.jobs.tasks.pricing.SessionLocal", testing_session_local
    ):
        yield


# ---------------------------------------------------------------------------
# vision_identify
# ---------------------------------------------------------------------------


def test_vision_identify_translates_http_exception(task_user, patch_task_session):
    """402-style HTTPException from the service must serialize, not pickle."""
    from app.jobs.tasks import vision as vision_task

    fake_service = MagicMock()
    fake_service.identify_async = AsyncMock(
        side_effect=HTTPException(status_code=402, detail="Daily vision budget exceeded")
    )

    with patch.object(vision_task, "VisionService", return_value=fake_service):
        result = asyncio.run(
            vision_task.vision_identify(
                ctx={},
                user_id=str(task_user.id),
                images_b64=[_b64_png()],
            )
        )

    assert result == {
        "ok": False,
        "error": "Daily vision budget exceeded",
        "status_code": 402,
    }


def test_vision_identify_returns_unknown_user_dict(task_user, patch_task_session):
    """Unknown user_id must surface as a serializable error, not a raise."""
    from app.jobs.tasks import vision as vision_task

    result = asyncio.run(
        vision_task.vision_identify(
            ctx={},
            user_id="00000000-0000-0000-0000-000000000000",
            images_b64=[_b64_png()],
        )
    )
    assert result == {
        "ok": False,
        "error": "user_not_found",
        "status_code": 404,
    }


def test_vision_identify_passes_through_success(task_user, patch_task_session):
    """Happy path returns the serialized VisionResult dict unchanged."""
    from app.jobs.tasks import vision as vision_task

    fake_result = MagicMock()
    fake_result.model_dump = MagicMock(return_value={"suggestion": {"name": "Camera"}})

    fake_service = MagicMock()
    fake_service.identify_async = AsyncMock(return_value=fake_result)

    with patch.object(vision_task, "VisionService", return_value=fake_service):
        result = asyncio.run(
            vision_task.vision_identify(
                ctx={},
                user_id=str(task_user.id),
                images_b64=[_b64_png()],
            )
        )

    assert result == {"suggestion": {"name": "Camera"}}


# ---------------------------------------------------------------------------
# pricing_refresh
# ---------------------------------------------------------------------------


def test_pricing_refresh_translates_http_exception(task_user, patch_task_session):
    from app.jobs.tasks import pricing as pricing_task

    fake_service = MagicMock()
    fake_service.estimate_async = AsyncMock(
        side_effect=HTTPException(status_code=503, detail="Pricing is disabled")
    )

    with patch.object(pricing_task, "PricingService", return_value=fake_service):
        result = asyncio.run(
            pricing_task.pricing_refresh(
                ctx={},
                user_id=str(task_user.id),
                metadata={"name": "x"},
                force_refresh=True,
            )
        )

    assert result == {
        "ok": False,
        "error": "Pricing is disabled",
        "status_code": 503,
    }


# ---------------------------------------------------------------------------
# backup_create / backup_restore
# ---------------------------------------------------------------------------


def test_backup_create_translates_http_exception(task_user):
    from app.jobs.tasks import backups as backups_task

    fake_service = MagicMock()
    fake_service.create = MagicMock(
        side_effect=HTTPException(status_code=507, detail="Insufficient storage")
    )
    fake_session = MagicMock()
    fake_session.close = MagicMock()

    with patch.object(
        backups_task, "_open_service", return_value=(fake_service, fake_session)
    ):
        result = asyncio.run(
            backups_task.backup_create(ctx={}, user_id=str(task_user.id))
        )

    assert result == {
        "ok": False,
        "error": "Insufficient storage",
        "status_code": 507,
    }
    fake_session.close.assert_called_once()


def test_backup_restore_translates_http_exception(task_user):
    from app.jobs.tasks import backups as backups_task

    fake_service = MagicMock()
    fake_service.commit_restore = MagicMock(
        side_effect=HTTPException(status_code=409, detail="Item count mismatch")
    )
    fake_session = MagicMock()
    fake_session.close = MagicMock()

    with patch.object(
        backups_task, "_open_service", return_value=(fake_service, fake_session)
    ):
        result = asyncio.run(
            backups_task.backup_restore(
                ctx={},
                user_id=str(task_user.id),
                backup_id="b-123",
                confirm_item_count=5,
            )
        )

    assert result == {
        "ok": False,
        "error": "Item count mismatch",
        "status_code": 409,
    }
    fake_session.close.assert_called_once()
