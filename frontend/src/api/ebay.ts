import type {
  EbayCategoryResponse,
  EbayExportRequest,
  EbayFields,
} from '../types/ebay';
import { downloadPost } from './download';
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
  /**
   * v2.3: server now streams the CSV directly instead of returning
   * ``file_url=null`` with a TODO. The client triggers a browser
   * download via a Blob URL — no return value since the bytes never
   * hit JavaScript state.
   */
  exportItems: async (request: EbayExportRequest): Promise<void> => {
    await downloadPost('/api/ebay/export', request, {
      fallback: 'whis-ebay-export.csv',
    });
  },
};

export type {
  EbayCategory,
  EbayCategoryResponse,
  EbayExportRequest,
  EbayExportResponse,
  EbayFields,
} from '../types/ebay';
