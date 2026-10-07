"""item_images.item_id FK gets ON DELETE CASCADE

The backup-restore service deletes a user's items with a bulk
``DELETE FROM items WHERE owner_id=...`` (``synchronize_session=False``),
which bypasses SQLAlchemy's ORM cascade. On SQLite the restore used
to succeed because SQLite doesn't enforce foreign keys by default;
on Postgres it failed with ``ForeignKeyViolation`` because
``item_images.item_id_fkey`` had no ``ON DELETE CASCADE``. This
migration promotes the FK to cascade at the DB level so the two
dialects behave identically and any future bulk-delete path stays
safe. The service code is also updated in lockstep to delete
``item_images`` rows before the parent ``items`` rows
(belt-and-suspenders), and the ORM model's ``ForeignKey``
declaration carries ``ondelete="CASCADE"`` for autogenerate
fidelity.

Revision ID: 20260423_0008
Revises: 20260422_0007
Create Date: 2026-04-23
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260423_0008"
down_revision: Union[str, None] = "20260422_0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _explicit_item_images_table(ondelete: str | None) -> sa.Table:
    """Build the target ``item_images`` definition with the desired FK mode.

    SQLite's ``batch_alter_table`` reflects the live schema to build the
    replacement table. That reflection can lose FK names / ondelete metadata
    which makes a pure ``drop_constraint`` + ``create_foreign_key`` inside
    the batch brittle. Passing an explicit ``copy_from=`` keeps the recreate
    dance deterministic.
    """
    fk_kwargs: dict = {}
    if ondelete:
        fk_kwargs["ondelete"] = ondelete
    return sa.Table(
        "item_images",
        sa.MetaData(),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column(
            "item_id",
            sa.String(length=36),
            sa.ForeignKey("items.id", **fk_kwargs),
            nullable=True,
        ),
        sa.Column("filename", sa.String(), nullable=True),
        sa.Column("file_path", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("thumbnail_path", sa.String(length=512), nullable=True),
        sa.Column("thumbnail_generated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def upgrade() -> None:
    dialect = op.get_bind().dialect.name
    if dialect == "sqlite":
        target = _explicit_item_images_table(ondelete="CASCADE")
        with op.batch_alter_table(
            "item_images", recreate="always", copy_from=target
        ):
            pass
    else:
        op.execute("ALTER TABLE item_images DROP CONSTRAINT item_images_item_id_fkey")
        op.execute(
            "ALTER TABLE item_images "
            "ADD CONSTRAINT item_images_item_id_fkey "
            "FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE"
        )


def downgrade() -> None:
    dialect = op.get_bind().dialect.name
    if dialect == "sqlite":
        target = _explicit_item_images_table(ondelete=None)
        with op.batch_alter_table(
            "item_images", recreate="always", copy_from=target
        ):
            pass
    else:
        op.execute("ALTER TABLE item_images DROP CONSTRAINT item_images_item_id_fkey")
        op.execute(
            "ALTER TABLE item_images "
            "ADD CONSTRAINT item_images_item_id_fkey "
            "FOREIGN KEY (item_id) REFERENCES items(id)"
        )
