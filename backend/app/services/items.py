"""Item service — the largest extraction of the v2.2 service-layer work.

Combines item CRUD, filtered list/search, export-to-records, record-to-DB
import, bulk delete, distinct category/location lookups, and barcode
lookup. Every query has been rewritten from the SQLAlchemy 1.x
``db.query(...).filter(...)`` chain style to the 2.x
``db.execute(select(...).where(...))`` style so the codebase is ready for
SQLAlchemy 3.x (where ``.query()`` is removed).

Every method enforces ownership against ``self.user``. Raises
``HTTPException`` on invalid inputs, matching the pattern established by
ImageService and BackupService in v2.2.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session

from .. import models, schemas

logger = logging.getLogger(__name__)


# FTS5 reserves a handful of characters for query syntax. We're only
# exposing plain-string search to the UI, so the safest thing is to
# wrap the whole query in double quotes and escape any embedded
# double quotes. This sidesteps the full MATCH grammar — no operators,
# no column filters, no prefix searches from the user's perspective.
def _sanitize_fts5(query: str) -> str:
    escaped = query.replace('"', '""').strip()
    if not escaped:
        return '""'
    return f'"{escaped}"'


# Fields on Item that may be updated via the import endpoint. Keeps us from
# accidentally letting a crafted CSV set server-managed fields like id/
# owner_id/created_at/updated_at.
IMPORTABLE_FIELDS: set[str] = {
    "name",
    "category",
    "location",
    "brand",
    "model_number",
    "serial_number",
    "barcode",
    "purchase_date",
    "purchase_price",
    "current_value",
    "warranty_expiration",
    "notes",
    "custom_fields",
}


class ItemService:
    def __init__(self, db: Session, user: models.User):
        self.db = db
        self.user = user

    # -- internal helpers ---------------------------------------------------

    def _owned_item(self, item_id: uuid.UUID) -> models.Item:
        stmt = select(models.Item).where(
            models.Item.id == item_id,
            models.Item.owner_id == self.user.id,
        )
        item = self.db.execute(stmt).scalar_one_or_none()
        if item is None:
            raise HTTPException(status_code=404, detail="Item not found")
        return item

    # -- CRUD --------------------------------------------------------------

    def create(self, item_data: schemas.ItemCreate) -> models.Item:
        db_item = models.Item(**item_data.model_dump(), owner_id=self.user.id)
        self.db.add(db_item)
        self.db.commit()
        self.db.refresh(db_item)
        return db_item

    def get(self, item_id: uuid.UUID) -> models.Item:
        return self._owned_item(item_id)

    def update(self, item_id: uuid.UUID, updates: schemas.ItemUpdate) -> models.Item:
        db_item = self._owned_item(item_id)
        update_data = updates.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_item, field, value)
        self.db.commit()
        self.db.refresh(db_item)
        return db_item

    def delete(self, item_id: uuid.UUID) -> None:
        db_item = self._owned_item(item_id)
        self.db.delete(db_item)
        self.db.commit()

    def bulk_delete(self, item_ids: list[uuid.UUID]) -> int:
        """Delete every listed item that belongs to self.user. Returns count."""
        if not item_ids:
            return 0
        stmt = (
            delete(models.Item)
            .where(
                models.Item.id.in_(item_ids),
                models.Item.owner_id == self.user.id,
            )
            .execution_options(synchronize_session=False)
        )
        result = self.db.execute(stmt)
        self.db.commit()
        return result.rowcount or 0

    # -- search / list ------------------------------------------------------

    def list(
        self, search_filter: schemas.SearchFilter
    ) -> tuple[list[models.Item], int]:
        """Return (page_of_items, total_count_matching_filter)."""
        base = select(models.Item).where(models.Item.owner_id == self.user.id)

        if search_filter.query:
            dialect = self.db.get_bind().dialect.name
            if dialect == "sqlite":
                # FTS5 virtual table lookup. Scoped to the current owner
                # via a subquery on items_fts.item_id.
                fts_match = text(
                    "items.id IN ("
                    "SELECT item_id FROM items_fts WHERE items_fts MATCH :q"
                    ")"
                ).bindparams(q=_sanitize_fts5(search_filter.query))
                base = base.where(fts_match)
            elif dialect == "postgresql":
                # Stored tsvector + GIN index. plainto_tsquery handles
                # tokenization + stop-word removal for us.
                pg_match = text(
                    "search_tsv @@ plainto_tsquery('english', :q)"
                ).bindparams(q=search_filter.query)
                base = base.where(pg_match)
            else:
                # Every dialect we build for has an FTS path; fall back
                # to the legacy ILIKE fan-out for completeness (raises
                # a warning so the gap is visible).
                logger.warning(
                    "no FTS path for dialect %s; using legacy ILIKE fan-out",
                    dialect,
                )
                like = f"%{search_filter.query}%"
                base = base.where(
                    models.Item.name.ilike(like)
                    | models.Item.brand.ilike(like)
                    | models.Item.model_number.ilike(like)
                    | models.Item.notes.ilike(like)
                    | models.Item.category.ilike(like)
                    | models.Item.location.ilike(like)
                )
        if search_filter.category:
            base = base.where(models.Item.category == search_filter.category)
        if search_filter.location:
            base = base.where(models.Item.location == search_filter.location)
        if search_filter.min_value is not None:
            base = base.where(models.Item.current_value >= search_filter.min_value)
        if search_filter.max_value is not None:
            base = base.where(models.Item.current_value <= search_filter.max_value)

        # Count BEFORE applying pagination/order. A separate SELECT COUNT is
        # still the canonical shape in SQLAlchemy 2.x.
        count_stmt = select(func.count()).select_from(base.subquery())
        total = int(self.db.execute(count_stmt).scalar_one() or 0)

        if search_filter.sort_by and hasattr(models.Item, search_filter.sort_by):
            order_by = getattr(models.Item, search_filter.sort_by)
            if search_filter.sort_desc:
                order_by = order_by.desc()
            base = base.order_by(order_by)

        paged = base.offset((search_filter.page - 1) * search_filter.page_size).limit(
            search_filter.page_size
        )
        items = list(self.db.execute(paged).scalars().all())
        return items, total

    # -- distinct lookups ---------------------------------------------------

    def categories(self) -> list[str]:
        stmt = (
            select(models.Item.category)
            .where(models.Item.owner_id == self.user.id)
            .distinct()
        )
        rows = self.db.execute(stmt).scalars().all()
        return [row for row in rows if row]

    def locations(self) -> list[str]:
        stmt = (
            select(models.Item.location)
            .where(models.Item.owner_id == self.user.id)
            .distinct()
        )
        rows = self.db.execute(stmt).scalars().all()
        return [row for row in rows if row]

    # -- barcode -----------------------------------------------------------

    def lookup_by_barcode(self, barcode: str) -> models.Item:
        stmt = select(models.Item).where(
            models.Item.barcode == barcode,
            models.Item.owner_id == self.user.id,
        )
        item = self.db.execute(stmt).scalar_one_or_none()
        if item is None:
            raise HTTPException(
                status_code=404, detail="No item found with this barcode"
            )
        return item

    # -- export / import ---------------------------------------------------

    def export_records(self) -> list[dict[str, Any]]:
        """Serialize every item to a flat dict suitable for CSV/JSON export.

        The router handles the final CSV/JSON encoding — keeping that wire-
        format concern out of the service means we can reuse this from a
        future CLI entrypoint or background-job export without coupling to
        FastAPI's ``StreamingResponse``.
        """
        stmt = select(models.Item).where(models.Item.owner_id == self.user.id)
        items = list(self.db.execute(stmt).scalars().all())

        records: list[dict[str, Any]] = []
        for item in items:
            records.append(
                {
                    "name": item.name,
                    "category": item.category,
                    "location": item.location,
                    "brand": item.brand,
                    "model_number": item.model_number,
                    "serial_number": item.serial_number,
                    "barcode": item.barcode,
                    "purchase_date": (
                        item.purchase_date.isoformat() if item.purchase_date else None
                    ),
                    "purchase_price": item.purchase_price,
                    "current_value": item.current_value,
                    "warranty_expiration": (
                        item.warranty_expiration.isoformat()
                        if item.warranty_expiration
                        else None
                    ),
                    "notes": item.notes,
                    "custom_fields": item.custom_fields,
                }
            )
        return records

    def import_records(self, records: list[dict[str, Any]]) -> dict[str, Any]:
        """Create Items from a list of dicts. Partial success is allowed.

        Unknown fields in the input are silently dropped (not an error —
        imports commonly carry audit columns like id/created_at that we
        regenerate server-side). Per-row failures are collected into
        ``errors`` rather than aborting the whole import.
        """
        errors: list[str] = []
        items_imported = 0

        for raw in records:
            try:
                # Parse ISO date strings back into datetimes.
                if raw.get("purchase_date"):
                    raw["purchase_date"] = datetime.fromisoformat(raw["purchase_date"])
                if raw.get("warranty_expiration"):
                    raw["warranty_expiration"] = datetime.fromisoformat(
                        raw["warranty_expiration"]
                    )

                safe = {k: v for k, v in raw.items() if k in IMPORTABLE_FIELDS}
                if "custom_fields" in safe and isinstance(safe["custom_fields"], str):
                    try:
                        safe["custom_fields"] = json.loads(safe["custom_fields"])
                    except json.JSONDecodeError:
                        safe["custom_fields"] = None

                # Coerce legacy custom_fields shapes into the v2.3 strict
                # schema — unknown top-level keys land under user_defined
                # rather than failing the whole row. Stored as a plain
                # dict so SQLAlchemy can hand it straight to the JSON
                # column.
                if safe.get("custom_fields"):
                    coerced = schemas.CustomFieldsSchema.coerce_from_raw(
                        safe["custom_fields"]
                    )
                    safe["custom_fields"] = (
                        coerced.model_dump(exclude_none=True)
                        if coerced is not None
                        else None
                    )

                db_item = models.Item(**safe, owner_id=self.user.id)
                self.db.add(db_item)
                items_imported += 1
            except Exception:
                logger.exception(
                    "error importing record: %s", raw.get("name", "<unknown>")
                )
                # Don't leak exception text to the caller; surface just the
                # item label so the frontend can show a per-row status.
                errors.append(f"Error importing item {raw.get('name', '<unknown>')}")

        self.db.commit()
        return {
            "success": True,
            "message": f"Successfully imported {items_imported} items",
            "items_imported": items_imported,
            "errors": errors or None,
        }
