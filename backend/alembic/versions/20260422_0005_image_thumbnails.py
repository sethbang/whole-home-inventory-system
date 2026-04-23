"""image thumbnails (v3.0)

Adds ``thumbnail_path`` + ``thumbnail_generated_at`` to ``item_images``.
The ARQ ``thumbnail_generate`` task populates both fields after the
upload request has already returned. When the worker isn't active
(default dev stack), the upload path runs the same helper inline —
behavior is identical, it just ties up the request thread.

Revision ID: 20260422_0005
Revises: 20260422_0004
Create Date: 2026-04-22
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "20260422_0005"
down_revision: Union[str, None] = "20260422_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _item_images_columns() -> set[str]:
    bind = op.get_bind()
    return {col["name"] for col in inspect(bind).get_columns("item_images")}


def upgrade() -> None:
    existing = _item_images_columns()
    with op.batch_alter_table("item_images") as batch_op:
        if "thumbnail_path" not in existing:
            batch_op.add_column(
                sa.Column("thumbnail_path", sa.String(length=512), nullable=True)
            )
        if "thumbnail_generated_at" not in existing:
            batch_op.add_column(
                sa.Column("thumbnail_generated_at", sa.DateTime(), nullable=True)
            )


def downgrade() -> None:
    existing = _item_images_columns()
    with op.batch_alter_table("item_images") as batch_op:
        if "thumbnail_generated_at" in existing:
            batch_op.drop_column("thumbnail_generated_at")
        if "thumbnail_path" in existing:
            batch_op.drop_column("thumbnail_path")
