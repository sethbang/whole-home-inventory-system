"""items full-text search (v3.0)

Replaces the 5-column ILIKE fan-out in ``ItemService.list()`` with
proper full-text search. The service layer learns the dialect at
query time and dispatches to the right backend:

* **SQLite** — FTS5 virtual table ``items_fts`` fed by three triggers
  (insert / update / delete). ``porter unicode61`` tokenization.
* **Postgres** — ``items.search_tsv`` (tsvector) column with a GIN
  index, maintained by a BEFORE INSERT OR UPDATE trigger.

The DDL itself lives in ``app.fts`` so the test conftest can reuse it
without running migrations per session. This file is a thin shim.

Revision ID: 20260422_0004
Revises: 20260422_0003
Create Date: 2026-04-22
"""

from typing import Sequence, Union

from alembic import op

from app.fts import (
    install_postgres_fts,
    install_sqlite_fts,
    uninstall_postgres_fts,
    uninstall_sqlite_fts,
)

revision: str = "20260422_0004"
down_revision: Union[str, None] = "20260422_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    dialect = conn.dialect.name
    if dialect == "sqlite":
        install_sqlite_fts(conn)
    elif dialect == "postgresql":
        install_postgres_fts(conn)
    else:
        raise RuntimeError(
            f"items_fts migration has no implementation for dialect {dialect!r}"
        )


def downgrade() -> None:
    conn = op.get_bind()
    dialect = conn.dialect.name
    if dialect == "sqlite":
        uninstall_sqlite_fts(conn)
    elif dialect == "postgresql":
        uninstall_postgres_fts(conn)
