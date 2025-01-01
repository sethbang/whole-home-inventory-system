"""
eBay integration package for WHIS.
"""

from .schemas import (
    EbayCondition,
    EbayListingFormat,
    EbayDuration,
    EbayShippingService,
    EbayReturnPeriod,
    EbayPaymentMethod,
    EbayFields,
    EbayCategory,
    EbayExportRequest,
    EbayExportResponse,
    EbayCategoryResponse,
)

from .category_mapping import (
    get_category_id,
    get_all_categories,
    suggest_category,
)

__all__ = [
    'EbayCondition',
    'EbayListingFormat',
    'EbayDuration',
    'EbayShippingService',
    'EbayReturnPeriod',
    'EbayPaymentMethod',
    'EbayFields',
    'EbayCategory',
    'EbayExportRequest',
    'EbayExportResponse',
    'EbayCategoryResponse',
    'get_category_id',
    'get_all_categories',
    'suggest_category',
]