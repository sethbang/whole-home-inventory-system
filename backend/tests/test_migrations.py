"""Alembic migration round-trip tests.

Verifies each migration can upgrade a fresh DB to head and then downgrade
back to the previous revision without error, leaving the schema in the
expected shape. Runs against a file-based SQLite DB per test (not the
in-memory DB the rest of the suite uses) so ``batch_alter_table`` can
actually execute.

These tests are slower than the in-memory suite (real disk + subprocess)
but they catch a whole class of "the migration broke for fresh-install
users" bugs that unit tests can't.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect

BACKEND_DIR = Path(__file__).resolve().parent.parent


def _run_alembic(
    args: list[str], *, db_url: str, env: dict[str, str] | None = None
) -> None:
    """Invoke ``alembic`` via subprocess so env vars and config are isolated."""
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    full_env.update(
        {
            "DATABASE_URL": db_url,
            "SECRET_KEY": "pytest-migration-roundtrip-secret-00000000",
            "BYPASS_AUTH": "false",
            "UPLOAD_DIR": full_env.get("UPLOAD_DIR", "/tmp/whis-uploads"),
            "BACKUP_DIR": full_env.get("BACKUP_DIR", "/tmp/whis-backups"),
        }
    )
    result = subprocess.run(
        [sys.executable, "-m", "alembic"] + args,
        cwd=str(BACKEND_DIR),
        env=full_env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        pytest.fail(
            f"alembic {' '.join(args)} failed:\n"
            f"STDOUT:\n{result.stdout}\n"
            f"STDERR:\n{result.stderr}"
        )


def _item_columns(db_url: str) -> set[str]:
    engine = create_engine(db_url)
    try:
        cols = {col["name"] for col in inspect(engine).get_columns("items")}
        return cols
    finally:
        engine.dispose()


def _table_exists(db_url: str, name: str) -> bool:
    engine = create_engine(db_url)
    try:
        return name in inspect(engine).get_table_names()
    finally:
        engine.dispose()


@pytest.fixture
def fresh_db(tmp_path):
    db_file = tmp_path / "migration_test.db"
    url = f"sqlite:///{db_file}"
    yield url


# ---------------------------------------------------------------------------
# Round-trip: baseline -> pricing_prewire -> baseline
# ---------------------------------------------------------------------------


PRICING_COLUMNS = {
    "estimated_value_low",
    "estimated_value_median",
    "estimated_value_high",
    "price_last_checked",
    "price_provider",
}


def test_upgrade_head_creates_pricing_surface(fresh_db):
    _run_alembic(["upgrade", "head"], db_url=fresh_db)

    # items table should have all five pricing columns.
    cols = _item_columns(fresh_db)
    assert PRICING_COLUMNS.issubset(cols), (
        f"missing pricing columns after upgrade: {PRICING_COLUMNS - cols}"
    )

    # price_cache table should exist.
    assert _table_exists(fresh_db, "price_cache")


def test_downgrade_to_baseline_removes_pricing_surface(fresh_db):
    _run_alembic(["upgrade", "head"], db_url=fresh_db)

    # Sanity: we're at head and have the pricing surface.
    assert PRICING_COLUMNS.issubset(_item_columns(fresh_db))
    assert _table_exists(fresh_db, "price_cache")

    _run_alembic(["downgrade", "20260420_0001"], db_url=fresh_db)

    # Downgrade should drop price_cache + the five items columns.
    cols = _item_columns(fresh_db)
    assert PRICING_COLUMNS.isdisjoint(cols), (
        f"pricing columns still present after downgrade: {PRICING_COLUMNS & cols}"
    )
    assert not _table_exists(fresh_db, "price_cache")


def test_full_roundtrip_preserves_core_tables(fresh_db):
    """Upgrade, downgrade, upgrade — core tables must be stable across it all."""
    _run_alembic(["upgrade", "head"], db_url=fresh_db)
    _run_alembic(["downgrade", "20260420_0001"], db_url=fresh_db)
    _run_alembic(["upgrade", "head"], db_url=fresh_db)

    # All four core tables plus price_cache must be present.
    engine = create_engine(fresh_db)
    try:
        tables = set(inspect(engine).get_table_names())
    finally:
        engine.dispose()
    assert {"users", "items", "item_images", "backups", "price_cache"}.issubset(tables)
