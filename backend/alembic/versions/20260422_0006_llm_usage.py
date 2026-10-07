"""llm_usage table (v3.1)

Per-(user, date, feature) rollup of LLM token + cost usage. The
budget guard reads this to enforce daily spend caps.

Revision ID: 20260422_0006
Revises: 20260422_0005
Create Date: 2026-04-22
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "20260422_0006"
down_revision: Union[str, None] = "20260422_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _existing_tables() -> set[str]:
    return set(inspect(op.get_bind()).get_table_names())


def _existing_indexes(table: str) -> set[str]:
    bind = op.get_bind()
    if table not in inspect(bind).get_table_names():
        return set()
    return {idx["name"] for idx in inspect(bind).get_indexes(table)}


def upgrade() -> None:
    if "llm_usage" not in _existing_tables():
        op.create_table(
            "llm_usage",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("usage_date", sa.DateTime(), nullable=False),
            sa.Column("feature", sa.String(length=32), nullable=False),
            sa.Column(
                "tokens_in", sa.Integer(), nullable=False, server_default="0"
            ),
            sa.Column(
                "tokens_out", sa.Integer(), nullable=False, server_default="0"
            ),
            sa.Column(
                "cost_usd", sa.Float(), nullable=False, server_default="0.0"
            ),
            sa.Column(
                "request_count",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    # Composite index — the hot query is
    # "sum cost_usd WHERE user_id = ? AND usage_date = ? AND feature = ?"
    if "ix_llm_usage_user_date_feature" not in _existing_indexes("llm_usage"):
        op.create_index(
            "ix_llm_usage_user_date_feature",
            "llm_usage",
            ["user_id", "usage_date", "feature"],
            unique=True,
        )


def downgrade() -> None:
    if "ix_llm_usage_user_date_feature" in _existing_indexes("llm_usage"):
        op.drop_index("ix_llm_usage_user_date_feature", table_name="llm_usage")
    if "llm_usage" in _existing_tables():
        op.drop_table("llm_usage")
