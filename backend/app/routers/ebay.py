"""
Router for eBay integration endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from .. import models, schemas, security, database
from ..ebay import (
    EbayFields, EbayCategory, EbayExportRequest, EbayExportResponse,
    EbayCategoryResponse, get_category_id, get_all_categories, suggest_category
)
import pandas as pd
import io
from datetime import datetime

router = APIRouter(prefix="/ebay", tags=["ebay"])

@router.get("/categories", response_model=EbayCategoryResponse)
async def list_categories(
    item_id: Optional[str] = None,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_active_user_or_none)
) -> EbayCategoryResponse:
    """
    Get available eBay categories and optionally get a suggested category for an item.
    """
    if not current_user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required"
        )

    # Get all available categories
    categories = get_all_categories()
    
    # If item_id is provided, get category suggestion
    suggested_category = None
    if item_id:
        item = db.query(models.Item).filter(
            models.Item.id == item_id,
            models.Item.owner_id == current_user.id
        ).first()
        
        if not item:
            raise HTTPException(
                status_code=404,
                detail="Item not found"
            )
        
        # Get suggested category based on item details
        category_id = suggest_category(item.name, item.notes)
        for category in categories:
            if category["id"] == category_id:
                suggested_category = category
                break
    
    return {
        "categories": categories,
        "suggested_category": suggested_category
    }

@router.post("/export", response_model=EbayExportResponse)
async def export_to_ebay(
    request: EbayExportRequest,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_active_user_or_none)
) -> EbayExportResponse:
    """
    Export selected items to eBay-compatible CSV format.
    """
    if not current_user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required"
        )

    # Get all requested items
    items = db.query(models.Item).filter(
        models.Item.id.in_(request.item_ids),
        models.Item.owner_id == current_user.id
    ).all()

    if not items:
        raise HTTPException(
            status_code=404,
            detail="No items found"
        )

    # Prepare data for export
    export_data = []
    errors = []
    
    for item in items:
        try:
            # Get or create eBay fields from custom_fields
            ebay_fields = item.custom_fields.get("ebay", {}) if item.custom_fields else {}
            ebay_fields = {**request.default_fields.dict(exclude_unset=True), **ebay_fields} if request.default_fields else ebay_fields
            
            # Get category ID
            category_id = ebay_fields.get("category_id") or get_category_id(item.category)
            
            # Prepare image URLs
            image_urls = [f"/items/{item.id}/images/{img.id}" for img in item.images[:12]]  # eBay allows up to 12 images
            
            # Create row for CSV
            row = {
                "Title": item.name[:80],  # eBay title limit is 80 characters
                "Description": f"{item.notes}\n\nBrand: {item.brand}" if item.brand else item.notes,
                "Category ID": category_id,
                "Condition": ebay_fields.get("condition", "GOOD"),
                "Format": ebay_fields.get("listing_format", "FIXED_PRICE"),
                "Duration": ebay_fields.get("duration", "DAYS_7"),
                "Start Price": ebay_fields.get("starting_price", item.current_value),
                "Buy It Now Price": ebay_fields.get("buy_it_now_price", item.current_value),
                "Quantity": ebay_fields.get("quantity", 1),
                "Shipping Service": ebay_fields.get("shipping_service", "USPS_PRIORITY"),
                "Shipping Cost": ebay_fields.get("shipping_cost", 0),
                "Returns Accepted": "Yes" if ebay_fields.get("returns_accepted", True) else "No",
                "Return Period": ebay_fields.get("return_period", "DAYS_30"),
                "Payment Methods": ",".join(ebay_fields.get("payment_methods", ["PAYPAL"])),
                "Pictures": "|".join(image_urls) if image_urls else "",
                "SKU": str(item.id),  # Use WHIS item ID as SKU for tracking
            }
            
            # Add any item specifics
            if "item_specifics" in ebay_fields:
                for key, value in ebay_fields["item_specifics"].items():
                    row[f"*{key}"] = value
            
            export_data.append(row)
            
        except Exception as e:
            errors.append(f"Error processing item {item.name}: {str(e)}")
    
    if not export_data:
        raise HTTPException(
            status_code=400,
            detail="No valid items to export"
        )
    
    try:
        # Create CSV file
        df = pd.DataFrame(export_data)
        buffer = io.StringIO()
        df.to_csv(buffer, index=False)
        
        # TODO: Save file and generate download URL
        # For now, we'll return success without file URL
        
        return {
            "success": True,
            "message": f"Successfully processed {len(export_data)} items",
            "items_processed": len(export_data),
            "errors": errors if errors else None,
            "file_url": None  # TODO: Implement file storage and return URL
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating export file: {str(e)}"
        )

@router.post("/items/{item_id}/ebay-fields", response_model=EbayFields)
async def update_ebay_fields(
    item_id: str,
    ebay_fields: EbayFields,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_active_user_or_none)
) -> EbayFields:
    """
    Update eBay-specific fields for an item.
    """
    if not current_user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required"
        )

    # Get the item
    item = db.query(models.Item).filter(
        models.Item.id == item_id,
        models.Item.owner_id == current_user.id
    ).first()
    
    if not item:
        raise HTTPException(
            status_code=404,
            detail="Item not found"
        )
    
    # Update custom_fields with eBay data
    if not item.custom_fields:
        item.custom_fields = {}
    
    item.custom_fields["ebay"] = ebay_fields.dict(exclude_unset=True)
    
    try:
        db.commit()
        return EbayFields(**item.custom_fields["ebay"])
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error updating eBay fields: {str(e)}"
        )