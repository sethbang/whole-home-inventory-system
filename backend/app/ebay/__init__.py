"""
eBay integration package for WHIS.
"""

from .category_mapping import (
    get_all_categories,
    get_category_id,
    suggest_category,
)
from .schemas import (
    EbayCategory,
    EbayCategoryResponse,
    EbayCondition,
    EbayDuration,
    EbayExportRequest,
    EbayExportResponse,
    EbayFields,
    EbayListingFormat,
    EbayPaymentMethod,
    EbayReturnPeriod,
    EbayShippingService,
)

__all__ = [
    "EbayCondition",
    "EbayListingFormat",
    "EbayDuration",
    "EbayShippingService",
    "EbayReturnPeriod",
    "EbayPaymentMethod",
    "EbayFields",
    "EbayCategory",
    "EbayExportRequest",
    "EbayExportResponse",
    "EbayCategoryResponse",
    "get_category_id",
    "get_all_categories",
    "suggest_category",
]
