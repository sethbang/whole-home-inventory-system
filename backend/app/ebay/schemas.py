"""
Pydantic schemas for eBay integration.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from enum import Enum

class EbayCondition(str, Enum):
    NEW = "NEW"
    LIKE_NEW = "LIKE_NEW"
    VERY_GOOD = "VERY_GOOD"
    GOOD = "GOOD"
    ACCEPTABLE = "ACCEPTABLE"
    FOR_PARTS = "FOR_PARTS"

class EbayListingFormat(str, Enum):
    FIXED_PRICE = "FIXED_PRICE"
    AUCTION = "AUCTION"

class EbayDuration(str, Enum):
    DAYS_3 = "DAYS_3"
    DAYS_5 = "DAYS_5"
    DAYS_7 = "DAYS_7"
    DAYS_10 = "DAYS_10"
    DAYS_30 = "DAYS_30"
    GTC = "GTC"  # Good 'Til Cancelled

class EbayShippingService(str, Enum):
    USPS_FIRST_CLASS = "USPS_FIRST_CLASS"
    USPS_PRIORITY = "USPS_PRIORITY"
    USPS_GROUND = "USPS_GROUND"
    UPS_GROUND = "UPS_GROUND"
    FEDEX_GROUND = "FEDEX_GROUND"
    FREIGHT = "FREIGHT"
    LOCAL_PICKUP = "LOCAL_PICKUP"

class EbayReturnPeriod(str, Enum):
    DAYS_30 = "DAYS_30"
    DAYS_60 = "DAYS_60"
    NO_RETURNS = "NO_RETURNS"

class EbayPaymentMethod(str, Enum):
    PAYPAL = "PAYPAL"
    CREDIT_CARD = "CREDIT_CARD"
    BANK_TRANSFER = "BANK_TRANSFER"

class EbayFields(BaseModel):
    """Schema for eBay-specific fields stored in item.custom_fields"""
    category_id: Optional[str] = Field(None, description="eBay category ID")
    condition: Optional[EbayCondition] = Field(None, description="Item condition")
    listing_format: Optional[EbayListingFormat] = Field(None, description="Listing format (auction/fixed)")
    duration: Optional[EbayDuration] = Field(None, description="Listing duration")
    shipping_service: Optional[EbayShippingService] = Field(None, description="Shipping service")
    shipping_cost: Optional[float] = Field(None, description="Shipping cost")
    returns_accepted: Optional[bool] = Field(None, description="Whether returns are accepted")
    return_period: Optional[EbayReturnPeriod] = Field(None, description="Return period")
    payment_methods: Optional[List[EbayPaymentMethod]] = Field(None, description="Accepted payment methods")
    starting_price: Optional[float] = Field(None, description="Starting price for auctions")
    reserve_price: Optional[float] = Field(None, description="Reserve price for auctions")
    buy_it_now_price: Optional[float] = Field(None, description="Buy It Now price")
    quantity: Optional[int] = Field(1, description="Number of items to list")
    domestic_shipping_only: Optional[bool] = Field(True, description="Ship only within country")
    item_specifics: Optional[Dict[str, str]] = Field(None, description="Additional item specifics")

class EbayCategory(BaseModel):
    """Schema for eBay category information"""
    id: str = Field(..., description="eBay category ID")
    name: str = Field(..., description="Category name")
    subcategories: Optional[List['EbayCategory']] = Field(None, description="Subcategories")

class EbayExportRequest(BaseModel):
    """Schema for eBay export request"""
    item_ids: List[str] = Field(..., description="List of WHIS item IDs to export")
    default_fields: Optional[EbayFields] = Field(None, description="Default fields for all items")

class EbayExportResponse(BaseModel):
    """Schema for eBay export response"""
    success: bool = Field(..., description="Whether export was successful")
    file_url: Optional[str] = Field(None, description="URL to download export file")
    message: str = Field(..., description="Status message")
    errors: Optional[List[str]] = Field(None, description="List of errors if any")
    items_processed: int = Field(..., description="Number of items processed")

class EbayCategoryResponse(BaseModel):
    """Schema for eBay category lookup response"""
    categories: List[EbayCategory] = Field(..., description="List of available categories")
    suggested_category: Optional[EbayCategory] = Field(None, description="Suggested category based on item")

# Update forward reference for subcategories
EbayCategory.model_rebuild()