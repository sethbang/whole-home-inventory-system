"""Router for Facebook Marketplace integration endpoints.

Five endpoints, mirroring the eBay router's shape:

- GET  /api/facebook/categories                     — dropdown options
- POST /api/facebook/items/{id}/fb-fields            — persist FbFields
- POST /api/facebook/items/{id}/copy-paste           — render block
- GET  /api/facebook/items/{id}/images.zip           — stream images zip
- POST /api/facebook/export                          — bulk catalog CSV

Since Meta doesn't expose a public Marketplace listing API for
individual sellers, all of this is "assist" tooling — we generate
copy-pasteable text and downloadable bundles the user hands to FB's
web form or Commerce Manager.
"""

from __future__ import annotations

import io
import logging
import os
import zipfile

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .. import database, models, security
from ..facebook.category_mapping import all_fb_categories
from ..facebook.formatter import (
    FB_CATALOG_COLUMNS,
    build_catalog_csv_row,
    build_copy_paste_block,
)
from ..facebook.schemas import (
    FbCatalogExportRequest,
    FbCopyPasteBlock,
    FbFields,
)
from ..settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/facebook", tags=["facebook"])


def _fb_fields_from_item(item: models.Item) -> FbFields | None:
    raw = (item.custom_fields or {}).get("facebook")
    if not raw:
        return None
    # coerce_from_raw would be overkill here — the strict schema applies
    # at the POST boundary. Trust our own stored shape.
    return FbFields(**raw)


def _owned_item(db: Session, user: models.User, item_id: str) -> models.Item:
    stmt = (
        select(models.Item)
        .options(selectinload(models.Item.images))
        .where(models.Item.id == item_id, models.Item.owner_id == user.id)
    )
    item = db.execute(stmt).scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


# ---------------------------------------------------------------------------
# GET /categories
# ---------------------------------------------------------------------------


@router.get("/categories")
async def list_categories(
    current_user: models.User = Depends(security.get_current_active_user),
) -> dict:
    """Return the curated list of Facebook Marketplace categories."""
    return {"categories": all_fb_categories()}


# ---------------------------------------------------------------------------
# POST /items/{id}/fb-fields
# ---------------------------------------------------------------------------


@router.post("/items/{item_id}/fb-fields", response_model=FbFields)
async def update_fb_fields(
    item_id: str,
    fb_fields: FbFields,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_active_user),
) -> FbFields:
    """Persist FbFields into ``item.custom_fields.facebook``."""
    item = _owned_item(db, current_user, item_id)
    if item.custom_fields is None:
        item.custom_fields = {}
    item.custom_fields = {
        **item.custom_fields,
        "facebook": fb_fields.model_dump(exclude_unset=True),
    }
    try:
        db.commit()
    except Exception:
        logger.exception("error persisting Facebook fields for item %s", item_id)
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update Facebook fields")
    return FbFields(**item.custom_fields["facebook"])


# ---------------------------------------------------------------------------
# POST /items/{id}/copy-paste
# ---------------------------------------------------------------------------


@router.post("/items/{item_id}/copy-paste", response_model=FbCopyPasteBlock)
async def generate_copy_paste_block(
    item_id: str,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_active_user),
) -> FbCopyPasteBlock:
    """Render the item as an FbCopyPasteBlock for the web-form workflow."""
    item = _owned_item(db, current_user, item_id)
    fb_fields = _fb_fields_from_item(item)
    return build_copy_paste_block(item, fb_fields)


# ---------------------------------------------------------------------------
# GET /items/{id}/images.zip
# ---------------------------------------------------------------------------


@router.get("/items/{item_id}/images.zip")
async def download_images_zip(
    item_id: str,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_active_user),
) -> StreamingResponse:
    """Stream a zip of the item's images for FB's bulk upload form."""
    item = _owned_item(db, current_user, item_id)

    if not item.images:
        raise HTTPException(
            status_code=400, detail="This item has no images to download"
        )

    upload_dir = str(settings.upload_path)
    max_bytes = settings.MAX_UPLOAD_BYTES * 20

    buf = io.BytesIO()
    total = 0
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for image in item.images:
            on_disk = os.path.join(upload_dir, image.filename)
            if not os.path.exists(on_disk):
                logger.warning(
                    "image missing on disk while zipping: %s", image.filename
                )
                continue
            size = os.path.getsize(on_disk)
            total += size
            if total > max_bytes:
                raise HTTPException(
                    status_code=413,
                    detail="Image set exceeds maximum zip size",
                )
            zf.write(on_disk, arcname=image.filename)

    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="item-{item_id}-images.zip"'
        },
    )


# ---------------------------------------------------------------------------
# POST /export
# ---------------------------------------------------------------------------


@router.post("/export")
async def export_catalog_csv(
    request: FbCatalogExportRequest,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_active_user),
) -> StreamingResponse:
    """Stream a CSV matching Meta's Commerce Manager catalog feed spec."""
    if not request.item_ids:
        raise HTTPException(status_code=400, detail="No items selected")

    stmt = (
        select(models.Item)
        .options(selectinload(models.Item.images))
        .where(
            models.Item.id.in_(request.item_ids),
            models.Item.owner_id == current_user.id,
        )
    )
    items = list(db.execute(stmt).scalars().all())

    if not items:
        raise HTTPException(status_code=404, detail="No items found")

    rows: list[dict] = []
    for item in items:
        fb_fields = _fb_fields_from_item(item)
        rows.append(
            build_catalog_csv_row(item, fb_fields, defaults=request.default_fields)
        )

    df = pd.DataFrame(rows, columns=FB_CATALOG_COLUMNS)
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="whis-facebook-catalog.csv"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )
