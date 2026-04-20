"""Pydantic schemas for Facebook Marketplace integration.

Mirrors the shape of ``app.ebay.schemas.EbayFields`` so the frontend can
reuse the same controlled-component pattern. The persisted shape lives
under ``item.custom_fields.facebook``.
"""

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class FbCondition(str, Enum):
    """FB Marketplace's condition taxonomy.

    FB uses a coarser grid than eBay. We map our own conditions to the
    FB values at copy-paste/CSV-generation time rather than requiring
    users to re-enter the same information under two keys.
    """

    NEW = "NEW"
    USED_LIKE_NEW = "USED_LIKE_NEW"
    USED_GOOD = "USED_GOOD"
    USED_FAIR = "USED_FAIR"


class FbAvailability(str, Enum):
    IN_STOCK = "in stock"
    OUT_OF_STOCK = "out of stock"


class FbFields(BaseModel):
    """Facebook-specific fields stored in ``item.custom_fields.facebook``."""

    price: Optional[float] = Field(None, description="Listing price, USD")
    condition: Optional[FbCondition] = Field(None, description="FB condition")
    category: Optional[str] = Field(
        None,
        description=(
            "Free-form FB Marketplace category name (e.g. 'Electronics', "
            "'Home Goods'). No canonical ID scheme like eBay — FB uses strings."
        ),
    )
    availability: Optional[FbAvailability] = Field(
        FbAvailability.IN_STOCK, description="Stock state"
    )
    description_override: Optional[str] = Field(
        None,
        description=(
            "If set, replaces the item's main description when rendering the "
            "copy-paste block / catalog row. Use when the marketplace-facing "
            "description differs from the private inventory note."
        ),
    )
    item_specifics: Optional[Dict[str, str]] = Field(
        None, description="Marketplace-specific key/value metadata"
    )


class FbCopyPasteBlock(BaseModel):
    """Server-rendered copy-paste bundle for the FB web form.

    The frontend copies ``block`` to the clipboard and pulls the ZIP
    from ``images_zip_url`` when the user wants to upload images.
    """

    title: str = Field(..., description="FB-compliant title (≤100 chars)")
    description: str = Field(..., description="Full listing description")
    price: Optional[float] = Field(None, description="Listing price")
    suggested_category: Optional[str] = Field(
        None, description="Suggested FB category string"
    )
    tags: List[str] = Field(default_factory=list, description="Keyword tags")
    block: str = Field(
        ...,
        description="Full rendered text block ready for clipboard paste",
    )


class FbCatalogExportRequest(BaseModel):
    item_ids: List[str] = Field(..., description="WHIS item IDs to include")
    default_fields: Optional[FbFields] = Field(
        None, description="Default FB fields applied when an item lacks its own"
    )


class FbCatalogExportResponse(BaseModel):
    success: bool
    message: str
    items_processed: int
    errors: Optional[List[str]] = None
