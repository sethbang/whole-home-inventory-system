"""llm_config singleton table + users.is_admin flag (v3.2)

Adds the operator-editable LLM configuration table behind
``/api/llm-config`` and promotes the ``users`` table with an
``is_admin`` boolean used to gate that surface.

Both changes are idempotent and dialect-aware: a freshly-bootstrapped
database picks them up via ``alembic upgrade head``; an existing
deployment that already has the new column or table (e.g. from a
``models.Base.metadata.create_all`` shortcut in tests) skips the
ALTER without error.

Revision ID: 20260503_0009
Revises: 20260423_0008
Create Date: 2026-05-03
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.sql import expression

revision: str = "20260503_0009"
down_revision: Union[str, None] = "20260423_0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _existing_tables() -> set[str]:
    return set(inspect(op.get_bind()).get_table_names())


def _existing_columns(table: str) -> set[str]:
    bind = op.get_bind()
    if table not in inspect(bind).get_table_names():
        return set()
    return {col["name"] for col in inspect(bind).get_columns(table)}


def upgrade() -> None:
    # 1. users.is_admin
    if "is_admin" not in _existing_columns("users"):
        with op.batch_alter_table("users") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "is_admin",
                    sa.Boolean(),
                    nullable=False,
                    server_default=expression.false(),
                )
            )
        # Backfill: promote the earliest user (by created_at) to admin so
        # an existing single-household install keeps working without a
        # manual SQL step. Multi-user installs may have already given
        # admin to someone via the new register flow on a fresh DB; the
        # backfill is a no-op there because that user is already admin.
        # We use a parameterless raw SQL because Postgres + SQLite
        # both speak ``ORDER BY created_at LIMIT 1``.
        bind = op.get_bind()
        first_user = bind.execute(
            sa.text("SELECT id FROM users ORDER BY created_at ASC LIMIT 1")
        ).fetchone()
        if first_user is not None:
            bind.execute(
                sa.text("UPDATE users SET is_admin = :v WHERE id = :id"),
                {"v": True, "id": first_user[0]},
            )

    # 2. llm_config singleton
    if "llm_config" not in _existing_tables():
        op.create_table(
            "llm_config",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("base_url", sa.String(), nullable=True),
            sa.Column("api_key_ciphertext", sa.String(), nullable=True),
            sa.Column("model", sa.String(), nullable=True),
            sa.Column("vision_model", sa.String(), nullable=True),
            sa.Column("pricing_model", sa.String(), nullable=True),
            sa.Column("timeout_seconds", sa.Integer(), nullable=True),
            sa.Column("response_healing", sa.Boolean(), nullable=True),
            sa.Column("vision_enabled", sa.Boolean(), nullable=True),
            sa.Column("pricing_enabled", sa.Boolean(), nullable=True),
            sa.Column("vision_daily_cap_usd", sa.Float(), nullable=True),
            sa.Column("pricing_daily_cap_usd", sa.Float(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("updated_by", sa.String(length=36), nullable=True),
            sa.ForeignKeyConstraint(["updated_by"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )


def downgrade() -> None:
    if "llm_config" in _existing_tables():
        op.drop_table("llm_config")
    if "is_admin" in _existing_columns("users"):
        with op.batch_alter_table("users") as batch_op:
            batch_op.drop_column("is_admin")
