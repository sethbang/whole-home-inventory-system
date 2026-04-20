import type {
  EbayCategoryResponse,
  EbayExportRequest,
  EbayExportResponse,
  EbayFields,
} from '../types/ebay';
import { apiClient } from './http';

export const ebay = {
  getCategories: async (itemId?: string): Promise<EbayCategoryResponse> => {
    const response = await apiClient.get<EbayCategoryResponse>(
      '/api/ebay/categories',
      { params: itemId ? { item_id: itemId } : undefined },
    );
    return response.data;
  },
  updateFields: async (
    itemId: string,
    fields: EbayFields,
  ): Promise<EbayFields> => {
    const response = await apiClient.post<EbayFields>(
      `/api/ebay/items/${itemId}/ebay-fields`,
      fields,
    );
    return response.data;
  },
  exportItems: async (
    request: EbayExportRequest,
  ): Promise<EbayExportResponse> => {
    const response = await apiClient.post<EbayExportResponse>(
      '/api/ebay/export',
      request,
    );
    return response.data;
  },
};

export type {
  EbayCategory,
  EbayCategoryResponse,
  EbayExportRequest,
  EbayExportResponse,
  EbayFields,
} from '../types/ebay';
