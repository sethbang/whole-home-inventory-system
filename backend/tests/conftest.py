"""Shared pytest fixtures for the WHIS backend.

Test env:
- Forces BYPASS_AUTH=false so the real auth paths are exercised.
- Forces a deterministic SECRET_KEY so JWTs round-trip.
- DATABASE_URL is driven by ``TEST_DATABASE_URL``; defaults to an
  in-memory SQLite with a StaticPool so every dependency-overridden
  session sees the same tables. Set ``TEST_DATABASE_URL`` to a
  Postgres URL (``postgresql+psycopg://...``) to exercise the PG leg.
"""

from __future__ import annotations

import os

_TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "sqlite:///:memory:")

os.environ.setdefault("BYPASS_AUTH", "false")
os.environ.setdefault("SECRET_KEY", "pytest-secret-key-not-a-placeholder-00000000")
os.environ["DATABASE_URL"] = _TEST_DATABASE_URL
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
from app.fts import install_postgres_fts, install_sqlite_fts  # noqa: E402
from app.main import app  # noqa: E402


def _is_sqlite() -> bool:
    return _TEST_DATABASE_URL.startswith("sqlite")


@pytest.fixture(scope="session")
def engine():
    if _is_sqlite():
        # StaticPool keeps the in-memory DB alive across connections, and
        # check_same_thread=False lets the FastAPI threadpool hand the same
        # connection across event-loop tasks.
        eng = create_engine(
            _TEST_DATABASE_URL,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    else:
        # Server-backed dialect (Postgres in CI). pool_pre_ping catches
        # connections the server has dropped underneath us.
        eng = create_engine(_TEST_DATABASE_URL, pool_pre_ping=True)
    # drop_all then create_all so re-runs against a shared Postgres
    # instance start clean. On SQLite's :memory: the drop is a no-op.
    models.Base.metadata.drop_all(bind=eng)
    models.Base.metadata.create_all(bind=eng)
    # create_all() doesn't build the FTS scaffolding (virtual tables +
    # triggers on SQLite, tsvector column + GIN + trigger on Postgres)
    # — that's Alembic migration territory. Layer it on top so tests
    # exercise the real FTS code path in ItemService.list().
    with eng.begin() as conn:
        if _is_sqlite():
            install_sqlite_fts(conn)
        elif _TEST_DATABASE_URL.startswith("postgresql"):
            install_postgres_fts(conn)
    return eng


@pytest.fixture(scope="session")
def testing_session_local(engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db_session(testing_session_local, engine):
    """Per-test DB session.

    The ``rollback()`` at teardown only covers in-flight transactions; tests
    that ``commit()`` (e.g. via a fixture like ``user``) leave data behind in
    the shared DB. We also wipe all tables after every test so fixtures
    start clean — same contract as the ``client`` fixture.
    """
    session = testing_session_local()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
        with engine.begin() as conn:
            for table in reversed(models.Base.metadata.sorted_tables):
                conn.execute(table.delete())


@pytest.fixture
def client(testing_session_local, engine):
    """TestClient with the DB dependency overridden to the test engine."""

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
