import { apiClient } from './client';

export interface EbayCategory {
  id: string;
  name: string;
  subcategories?: EbayCategory[];
}

export interface EbayFields {
  category_id?: string;
  condition?: string;
  listing_format?: string;
  duration?: string;
  shipping_service?: string;
  shipping_cost?: number;
  returns_accepted?: boolean;
  return_period?: string;
  payment_methods?: string[];
  starting_price?: number;
  reserve_price?: number;
  buy_it_now_price?: number;
  quantity?: number;
  domestic_shipping_only?: boolean;
  item_specifics?: Record<string, string>;
}

export interface EbayCategoryResponse {
  categories: EbayCategory[];
  suggested_category?: EbayCategory;
}

export interface EbayExportRequest {
  item_ids: string[];
  default_fields?: EbayFields;
}

export interface EbayExportResponse {
  success: boolean;
  file_url?: string;
  message: string;
  errors?: string[];
  items_processed: number;
}

export const ebay = {
  // Get all categories and optionally get suggested category for an item
  getCategories: async (itemId?: string): Promise<EbayCategoryResponse> => {
    const response = await apiClient.get<EbayCategoryResponse>('/api/ebay/categories', {
      params: itemId ? { item_id: itemId } : undefined
    });
    return response.data;
  },

  // Update eBay fields for an item
  updateFields: async (itemId: string, fields: EbayFields): Promise<EbayFields> => {
    const response = await apiClient.post<EbayFields>(`/api/ebay/items/${itemId}/ebay-fields`, fields);
    return response.data;
  },

  // Export items to eBay CSV format
  exportItems: async (request: EbayExportRequest): Promise<EbayExportResponse> => {
    const response = await apiClient.post<EbayExportResponse>('/api/ebay/export', request);
    return response.data;
  },
};