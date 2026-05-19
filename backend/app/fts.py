"""Full-text search scaffolding (v3.0).

One source of truth for the FTS DDL — consumed by the
``20260422_0004_items_fts`` Alembic migration for production upgrades
and by the test ``conftest.py`` so tests exercise the real FTS code
paths without re-running migrations on every session.

The indexed column list deliberately lives here (not in the migration
file) so the service layer can import it without reaching into the
versions directory.
"""

from __future__ import annotations

from sqlalchemy.engine import Connection

# Columns covered by FTS. Mirrors the old ILIKE fan-out in
# ``ItemService.list()`` (pre-v3.0).
FTS_COLUMNS: tuple[str, ...] = (
    "name",
    "brand",
    "model_number",
    "notes",
    "category",
    "location",
)


def _sqlite_columns_csv() -> str:
    return ", ".join(FTS_COLUMNS)


def _sqlite_new_values_csv() -> str:
    return ", ".join(f"coalesce(new.{c},'')" for c in FTS_COLUMNS)


def _sqlite_items_values_csv() -> str:
    return ", ".join(f"coalesce({c},'')" for c in FTS_COLUMNS)


def _pg_concat(prefix: str = "") -> str:
    """Build ``coalesce(p.col,'') || ' ' || coalesce(p.col2,'')…`` for PG."""
    qualifier = f"{prefix}." if prefix else ""
    return " || ' ' || ".join(
        f"coalesce({qualifier}{c},'')" for c in FTS_COLUMNS
    )


def install_sqlite_fts(conn: Connection) -> None:
    """Create items_fts virtual table + three sync triggers on SQLite.

    Idempotent: uses IF NOT EXISTS. Backfills existing rows so a
    migration run against a populated DB is lossless.
    """
    cols_csv = _sqlite_columns_csv()
    items_values = _sqlite_items_values_csv()
    new_values = _sqlite_new_values_csv()

    conn.exec_driver_sql(
        f"""
        CREATE VIRTUAL TABLE IF NOT EXISTS items_fts USING fts5(
            item_id UNINDEXED,
            {cols_csv},
            tokenize = 'porter unicode61'
        )
        """
    )
    # Backfill only works if items_fts is currently empty (avoid
    # duplicating rows on a second run). SELECT COUNT first.
    existing = conn.exec_driver_sql("SELECT count(*) FROM items_fts").scalar()
    if not existing:
        conn.exec_driver_sql(
            f"""
            INSERT INTO items_fts (item_id, {cols_csv})
            SELECT id, {items_values} FROM items
            """
        )

    conn.exec_driver_sql(
        f"""
        CREATE TRIGGER IF NOT EXISTS items_fts_ai
        AFTER INSERT ON items BEGIN
            INSERT INTO items_fts (item_id, {cols_csv})
            VALUES (new.id, {new_values});
        END
        """
    )
    conn.exec_driver_sql(
        """
        CREATE TRIGGER IF NOT EXISTS items_fts_ad
        AFTER DELETE ON items BEGIN
            DELETE FROM items_fts WHERE item_id = old.id;
        END
        """
    )
    conn.exec_driver_sql(
        f"""
        CREATE TRIGGER IF NOT EXISTS items_fts_au
        AFTER UPDATE ON items BEGIN
            DELETE FROM items_fts WHERE item_id = old.id;
            INSERT INTO items_fts (item_id, {cols_csv})
            VALUES (new.id, {new_values});
        END
        """
    )


def uninstall_sqlite_fts(conn: Connection) -> None:
    conn.exec_driver_sql("DROP TRIGGER IF EXISTS items_fts_au")
    conn.exec_driver_sql("DROP TRIGGER IF EXISTS items_fts_ad")
    conn.exec_driver_sql("DROP TRIGGER IF EXISTS items_fts_ai")
    conn.exec_driver_sql("DROP TABLE IF EXISTS items_fts")


def install_postgres_fts(conn: Connection) -> None:
    """Add items.search_tsv + GIN index + maintenance trigger on PG."""
    conn.exec_driver_sql(
        "ALTER TABLE items ADD COLUMN IF NOT EXISTS search_tsv tsvector"
    )
    # Backfill (idempotent — `to_tsvector` on already-populated rows is
    # cheap and overwriting with the same value is a no-op).
    conn.exec_driver_sql(
        f"UPDATE items SET search_tsv = to_tsvector('english', {_pg_concat()})"
    )
    conn.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_items_search_tsv "
        "ON items USING GIN (search_tsv)"
    )
    conn.exec_driver_sql(
        f"""
        CREATE OR REPLACE FUNCTION items_search_tsv_update() RETURNS trigger AS $$
        BEGIN
            new.search_tsv := to_tsvector('english', {_pg_concat('new')});
            RETURN new;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    conn.exec_driver_sql(
        "DROP TRIGGER IF EXISTS items_search_tsv_trg ON items"
    )
    conn.exec_driver_sql(
        """
        CREATE TRIGGER items_search_tsv_trg
        BEFORE INSERT OR UPDATE ON items
        FOR EACH ROW EXECUTE FUNCTION items_search_tsv_update()
        """
    )


def uninstall_postgres_fts(conn: Connection) -> None:
    conn.exec_driver_sql("DROP TRIGGER IF EXISTS items_search_tsv_trg ON items")
    conn.exec_driver_sql("DROP FUNCTION IF EXISTS items_search_tsv_update()")
    conn.exec_driver_sql("DROP INDEX IF EXISTS ix_items_search_tsv")
    conn.exec_driver_sql("ALTER TABLE items DROP COLUMN IF EXISTS search_tsv")
