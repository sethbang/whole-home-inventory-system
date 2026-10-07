"""price_cache composite PK (v3.1)

v2.2 provisioned price_cache with ``identity_hash`` as the sole
primary key. v3.1's pricing service keys by ``(identity_hash, provider)``
so the same hash can host one entry per provider (eBay vs LLM vs
future providers). The table has no production rows yet — pricing
ships in v3.1 — so the PK swap is safe to do without data migration.

Implementation notes:

* SQLite doesn't name primary keys, so ``drop_constraint`` won't
  find anything by name. We use ``batch_alter_table(recreate="always")``
  which rebuilds the table and applies ``create_primary_key`` in
  the process.
* Postgres does name the PK (``price_cache_pkey`` by convention).
  We use the simpler drop + recreate path there.

Revision ID: 20260422_0007
Revises: 20260422_0006
Create Date: 2026-04-22
"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy import inspect

revision: str = "20260422_0007"
down_revision: Union[str, None] = "20260422_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _pk_columns() -> tuple[str, ...]:
    bind = op.get_bind()
    pk = inspect(bind).get_pk_constraint("price_cache")
    return tuple(pk.get("constrained_columns", []))


def _is_composite() -> bool:
    return _pk_columns() == ("identity_hash", "provider")


def upgrade() -> None:
    if _is_composite():
        return

    dialect = op.get_bind().dialect.name
    if dialect == "sqlite":
        # batch_alter_table(recreate="always") copies the table into a
        # temp, drops the original, renames the temp back. The reflected
        # schema picks up the new PK we declare below.
        with op.batch_alter_table("price_cache", recreate="always") as batch_op:
            batch_op.create_primary_key(
                "price_cache_pkey",
                ["identity_hash", "provider"],
            )
    else:
        # Postgres: drop the named constraint + recreate composite.
        op.execute("ALTER TABLE price_cache DROP CONSTRAINT price_cache_pkey")
        op.execute(
            "ALTER TABLE price_cache "
            "ADD CONSTRAINT price_cache_pkey "
            "PRIMARY KEY (identity_hash, provider)"
        )


def downgrade() -> None:
    if _pk_columns() == ("identity_hash",):
        return

    dialect = op.get_bind().dialect.name
    if dialect == "sqlite":
        with op.batch_alter_table("price_cache", recreate="always") as batch_op:
            batch_op.create_primary_key("price_cache_pkey", ["identity_hash"])
    else:
        op.execute("ALTER TABLE price_cache DROP CONSTRAINT price_cache_pkey")
        op.execute(
            "ALTER TABLE price_cache "
            "ADD CONSTRAINT price_cache_pkey "
            "PRIMARY KEY (identity_hash)"
        )
