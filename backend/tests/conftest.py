"""Shared pytest fixtures for the WHIS backend.

Test env:
- Forces BYPASS_AUTH=false so the real auth paths are exercised.
- Forces a deterministic SECRET_KEY so JWTs round-trip.
- Points DATABASE_URL at an in-memory SQLite with a StaticPool so every
  dependency-overridden session sees the same tables.
"""

from __future__ import annotations

import os

os.environ.setdefault("BYPASS_AUTH", "false")
os.environ.setdefault("SECRET_KEY", "pytest-secret-key-not-a-placeholder-00000000")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("UPLOAD_DIR", "")
os.environ.setdefault("BACKUP_DIR", "")
os.environ.setdefault("MAX_UPLOAD_BYTES", "5242880")
os.environ.setdefault("LOG_LEVEL", "WARNING")

import tempfile  # noqa: E402

_upload_tmp = tempfile.mkdtemp(prefix="whis-uploads-")
_backup_tmp = tempfile.mkdtemp(prefix="whis-backups-")
os.environ["UPLOAD_DIR"] = _upload_tmp
os.environ["BACKUP_DIR"] = _backup_tmp

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app import database, models, security  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def engine():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    models.Base.metadata.create_all(bind=eng)
    return eng


@pytest.fixture(scope="session")
def testing_session_local(engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db_session(testing_session_local):
    session = testing_session_local()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def client(testing_session_local, engine):
    """TestClient with the DB dependency overridden to the in-memory engine."""

    def _get_db_override():
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[database.get_db] = _get_db_override
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    # Wipe data between tests so fixtures start clean.
    with engine.begin() as conn:
        for table in reversed(models.Base.metadata.sorted_tables):
            conn.execute(table.delete())


@pytest.fixture
def user(db_session) -> models.User:
    user = models.User(
        email="alice@example.com",
        username="alice",
        hashed_password=security.get_password_hash("correct-horse-battery-staple"),
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(user) -> dict[str, str]:
    token = security.create_access_token(data={"sub": user.username})
    return {"Authorization": f"Bearer {token}"}
