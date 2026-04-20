"""baseline schema

Creates the initial WHIS schema (users, items, item_images, backups) matching
app.models. Safe to run against an existing database previously bootstrapped
via ``Base.metadata.create_all()``: each object is created only if it does
not already exist.

Revision ID: 20260420_0001
Revises:
Create Date: 2026-04-20
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import sqlite

revision: str = "20260420_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _existing_tables() -> set[str]:
    bind = op.get_bind()
    return set(inspect(bind).get_table_names())


def _existing_indexes(table: str) -> set[str]:
    bind = op.get_bind()
    if table not in inspect(bind).get_table_names():
        return set()
    return {idx["name"] for idx in inspect(bind).get_indexes(table)}


def _ensure_index(name: str, table: str, columns: list[str], *, unique: bool = False) -> None:
    if name not in _existing_indexes(table):
        op.create_index(name, table, columns, unique=unique)


def upgrade() -> None:
    tables = _existing_tables()

    if "users" not in tables:
        op.create_table(
            "users",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("email", sa.String(), nullable=True),
            sa.Column("username", sa.String(), nullable=True),
            sa.Column("hashed_password", sa.String(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
    _ensure_index("ix_users_email", "users", ["email"], unique=True)
    _ensure_index("ix_users_username", "users", ["username"], unique=True)

    if "items" not in tables:
        op.create_table(
            "items",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("name", sa.String(), nullable=True),
            sa.Column("category", sa.String(), nullable=True),
            sa.Column("location", sa.String(), nullable=True),
            sa.Column("brand", sa.String(), nullable=True),
            sa.Column("model_number", sa.String(), nullable=True),
            sa.Column("serial_number", sa.String(), nullable=True),
            sa.Column("barcode", sa.String(), nullable=True),
            sa.Column("purchase_date", sa.DateTime(), nullable=True),
            sa.Column("purchase_price", sa.Float(), nullable=True),
            sa.Column("current_value", sa.Float(), nullable=True),
            sa.Column("warranty_expiration", sa.DateTime(), nullable=True),
            sa.Column("notes", sa.String(), nullable=True),
            sa.Column("custom_fields", sqlite.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.Column("owner_id", sa.String(length=36), nullable=True),
            sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    _ensure_index("ix_items_name", "items", ["name"])
    _ensure_index("ix_items_category", "items", ["category"])
    _ensure_index("ix_items_location", "items", ["location"])
    _ensure_index("ix_items_barcode", "items", ["barcode"])

    if "item_images" not in tables:
        op.create_table(
            "item_images",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("item_id", sa.String(length=36), nullable=True),
            sa.Column("filename", sa.String(), nullable=True),
            sa.Column("file_path", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["item_id"], ["items.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    if "backups" not in tables:
        op.create_table(
            "backups",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("owner_id", sa.String(length=36), nullable=True),
            sa.Column("filename", sa.String(), nullable=True),
            sa.Column("file_path", sa.String(), nullable=True),
            sa.Column("size_bytes", sa.Integer(), nullable=True),
            sa.Column("item_count", sa.Integer(), nullable=True),
            sa.Column("image_count", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("status", sa.String(), nullable=True),
            sa.Column("error_message", sa.String(), nullable=True),
            sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )


def downgrade() -> None:
    op.drop_table("backups")
    op.drop_table("item_images")
    op.drop_index("ix_items_barcode", table_name="items")
    op.drop_index("ix_items_location", table_name="items")
    op.drop_index("ix_items_category", table_name="items")
    op.drop_index("ix_items_name", table_name="items")
    op.drop_table("items")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
