"""pricing pre-wire (v2.2)

Adds the schema surface the v3.1 pricing feature will populate:

* Five nullable columns on ``items`` for the normalized resale estimate
  returned by ``PriceProvider`` implementations. Dedicated columns
  (instead of burying them in ``custom_fields``) so the UI can sort /
  filter by value and "last checked" without JSON-column gymnastics.

* A ``price_cache`` table keyed by a normalized identity hash so repeat
  lookups for the same item (across sessions / restarts) don't hammer
  eBay's API. Stores the serialized ``PriceEstimate`` payload as JSON
  so the schema doesn't need another migration when we add fields.

Done in v2.2 so v3.1's feature PR isn't also a schema-migration PR.

Revision ID: 20260420_0002
Revises: 20260420_0001
Create Date: 2026-04-20
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "20260420_0002"
down_revision: Union[str, None] = "20260420_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# New pricing columns added to ``items``. Name -> SQLAlchemy type.
_PRICING_COLUMNS: dict[str, sa.types.TypeEngine] = {
    "estimated_value_low": sa.Float(),
    "estimated_value_median": sa.Float(),
    "estimated_value_high": sa.Float(),
    "price_last_checked": sa.DateTime(),
    "price_provider": sa.String(length=32),
}


def _items_columns() -> set[str]:
    bind = op.get_bind()
    return {col["name"] for col in inspect(bind).get_columns("items")}


def _existing_tables() -> set[str]:
    bind = op.get_bind()
    return set(inspect(bind).get_table_names())


def upgrade() -> None:
    # --- items.* pricing columns -------------------------------------------
    existing = _items_columns()
    with op.batch_alter_table("items") as batch_op:
        for name, col_type in _PRICING_COLUMNS.items():
            if name not in existing:
                batch_op.add_column(sa.Column(name, col_type, nullable=True))

    # --- price_cache table --------------------------------------------------
    if "price_cache" not in _existing_tables():
        op.create_table(
            "price_cache",
            sa.Column("identity_hash", sa.String(length=64), primary_key=True),
            sa.Column("provider", sa.String(length=32), nullable=False),
            sa.Column("payload", sa.JSON(), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.func.current_timestamp(),
            ),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
        )
        op.create_index(
            "ix_price_cache_expires_at",
            "price_cache",
            ["expires_at"],
        )


def downgrade() -> None:
    # Drop the cache table first — nothing depends on items' new columns yet.
    if "price_cache" in _existing_tables():
        op.drop_index("ix_price_cache_expires_at", table_name="price_cache")
        op.drop_table("price_cache")

    existing = _items_columns()
    # batch_alter_table is required for SQLite-friendly column drops.
    with op.batch_alter_table("items") as batch_op:
        for name in _PRICING_COLUMNS:
            if name in existing:
                batch_op.drop_column(name)
