"""
Router for eBay integration endpoints.
"""

import io
import logging
from typing import Optional

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import database, models, security
from ..ebay import (
    EbayCategoryResponse,
    EbayExportRequest,
    EbayFields,
    get_all_categories,
    get_category_id,
    suggest_category,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ebay", tags=["ebay"])


@router.get("/categories", response_model=EbayCategoryResponse)
async def list_categories(
    item_id: Optional[str] = None,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_active_user),
) -> EbayCategoryResponse:
    """
    Get available eBay categories and optionally get a suggested category for an item.
    """
    categories = get_all_categories()

    suggested_category = None
    if item_id:
        item = db.execute(
            select(models.Item).where(
                models.Item.id == item_id,
                models.Item.owner_id == current_user.id,
            )
        ).scalar_one_or_none()

        if not item:
            raise HTTPException(status_code=404, detail="Item not found")

        category_id = suggest_category(item.name, item.notes)
        for category in categories:
            if category["id"] == category_id:
                suggested_category = category
                break

    return {"categories": categories, "suggested_category": suggested_category}


@router.post("/export")
async def export_to_ebay(
    request: EbayExportRequest,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_active_user),
) -> StreamingResponse:
    """
    Export selected items as an eBay-compatible CSV, streamed directly.

    v2.3: replaced the prior EbayExportResponse shape (which returned
    ``file_url=None`` with a TODO to wire up file storage) with a
    streaming CSV response, matching the pattern the new Facebook
    Marketplace exporter uses. Callers download the bytes instead of
    following a download URL.
    """
    if not request.item_ids:
        raise HTTPException(status_code=400, detail="No items selected")

    items = (
        db.execute(
            select(models.Item).where(
                models.Item.id.in_(request.item_ids),
                models.Item.owner_id == current_user.id,
            )
        )
        .scalars()
        .all()
    )

    if not items:
        raise HTTPException(status_code=404, detail="No items found")

    export_data = []
    for item in items:
        try:
            ebay_fields = (
                item.custom_fields.get("ebay", {}) if item.custom_fields else {}
            )
            ebay_fields = (
                {
                    **request.default_fields.model_dump(exclude_unset=True),
                    **ebay_fields,
                }
                if request.default_fields
                else ebay_fields
            )

            category_id = ebay_fields.get("category_id") or get_category_id(
                item.category
            )

            image_urls = [
                f"/items/{item.id}/images/{img.id}" for img in item.images[:12]
            ]

            row = {
                "Title": item.name[:80],
                "Description": (
                    f"{item.notes}\n\nBrand: {item.brand}"
                    if item.brand
                    else item.notes
                ),
                "Category ID": category_id,
                "Condition": ebay_fields.get("condition", "GOOD"),
                "Format": ebay_fields.get("listing_format", "FIXED_PRICE"),
                "Duration": ebay_fields.get("duration", "DAYS_7"),
                "Start Price": ebay_fields.get(
                    "starting_price", item.current_value
                ),
                "Buy It Now Price": ebay_fields.get(
                    "buy_it_now_price", item.current_value
                ),
                "Quantity": ebay_fields.get("quantity", 1),
                "Shipping Service": ebay_fields.get(
                    "shipping_service", "USPS_PRIORITY"
                ),
                "Shipping Cost": ebay_fields.get("shipping_cost", 0),
                "Returns Accepted": (
                    "Yes" if ebay_fields.get("returns_accepted", True) else "No"
                ),
                "Return Period": ebay_fields.get("return_period", "DAYS_30"),
                "Payment Methods": ",".join(
                    ebay_fields.get("payment_methods", ["PAYPAL"])
                ),
                "Pictures": "|".join(image_urls) if image_urls else "",
                "SKU": str(item.id),
            }

            if "item_specifics" in ebay_fields:
                for key, value in (ebay_fields["item_specifics"] or {}).items():
                    row[f"*{key}"] = value

            export_data.append(row)
        except Exception:
            # Don't leak Python exception details; log and skip the row.
            logger.exception("error processing item %s for eBay export", item.id)

    if not export_data:
        raise HTTPException(status_code=400, detail="No valid items to export")

    df = pd.DataFrame(export_data)
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="whis-ebay-export.csv"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


@router.post("/items/{item_id}/ebay-fields", response_model=EbayFields)
async def update_ebay_fields(
    item_id: str,
    ebay_fields: EbayFields,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_active_user),
) -> EbayFields:
    """Update eBay-specific fields for an item."""
    item = db.execute(
        select(models.Item).where(
            models.Item.id == item_id,
            models.Item.owner_id == current_user.id,
        )
    ).scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if not item.custom_fields:
        item.custom_fields = {}

    item.custom_fields = {
        **item.custom_fields,
        "ebay": ebay_fields.model_dump(exclude_unset=True),
    }

    try:
        db.commit()
        return EbayFields(**item.custom_fields["ebay"])
    except Exception:
        logger.exception("error updating eBay fields for item %s", item_id)
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update eBay fields")
