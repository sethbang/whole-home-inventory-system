"""postgres compat (v3.0)

Promotes dialect-specific types that only make sense on Postgres:

* ``items.custom_fields`` — JSON → JSONB. JSONB supports indexing,
  operator-based containment queries, and is the type every Postgres app
  should reach for unless it explicitly needs text-preserving JSON.
* ``price_cache.payload`` — same JSON → JSONB lift for consistency.
* GIN index on ``items.custom_fields`` so future in-JSON filters are
  index-backed out of the box.

No-op on SQLite (the two JSON columns are already TEXT-backed; there's no
equivalent type promotion to do). UUID columns remain ``varchar(36)`` on
both dialects — at household scale the native ``uuid`` type's indexing
benefit doesn't pay for the ALTER-COLUMN-TYPE + FK-dance complexity, and
our ``UUID`` ``TypeDecorator`` already round-trips real ``uuid.UUID``
objects either way.

Revision ID: 20260422_0003
Revises: 20260420_0002
Create Date: 2026-04-22
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "20260422_0003"
down_revision: Union[str, None] = "20260420_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _dialect_name() -> str:
    return op.get_bind().dialect.name


def _existing_indexes(table: str) -> set[str]:
    bind = op.get_bind()
    if table not in inspect(bind).get_table_names():
        return set()
    return {idx["name"] for idx in inspect(bind).get_indexes(table)}


def upgrade() -> None:
    if _dialect_name() != "postgresql":
        return

    # JSON → JSONB. The USING clause is mandatory; JSON::JSONB is a
    # cheap cast (Postgres already stores JSONB-compatible text).
    op.execute(
        "ALTER TABLE items "
        "ALTER COLUMN custom_fields TYPE JSONB "
        "USING custom_fields::jsonb"
    )
    op.execute(
        "ALTER TABLE price_cache "
        "ALTER COLUMN payload TYPE JSONB "
        "USING payload::jsonb"
    )

    # GIN index on items.custom_fields. Idempotent guard so re-running
    # against an already-migrated DB is safe.
    if "ix_items_custom_fields_gin" not in _existing_indexes("items"):
        op.execute(
            "CREATE INDEX ix_items_custom_fields_gin "
            "ON items USING GIN (custom_fields)"
        )


def downgrade() -> None:
    if _dialect_name() != "postgresql":
        return

    if "ix_items_custom_fields_gin" in _existing_indexes("items"):
        op.execute("DROP INDEX ix_items_custom_fields_gin")

    op.execute(
        "ALTER TABLE price_cache "
        "ALTER COLUMN payload TYPE JSON "
        "USING payload::json"
    )
    op.execute(
        "ALTER TABLE items "
        "ALTER COLUMN custom_fields TYPE JSON "
        "USING custom_fields::json"
    )
