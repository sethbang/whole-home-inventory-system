import type {
  FbCatalogExportRequest,
  FbCategoriesResponse,
  FbCopyPasteBlock,
  FbFieldsData,
} from '../types/facebook';
import { downloadGet, downloadPost } from './download';
import { apiClient } from './http';

export const facebook = {
  getCategories: async (): Promise<FbCategoriesResponse> => {
    const response = await apiClient.get<FbCategoriesResponse>(
      '/api/facebook/categories',
    );
    return response.data;
  },
  updateFields: async (
    itemId: string,
    fields: FbFieldsData,
  ): Promise<FbFieldsData> => {
    const response = await apiClient.post<FbFieldsData>(
      `/api/facebook/items/${itemId}/fb-fields`,
      fields,
    );
    return response.data;
  },
  copyPasteBlock: async (itemId: string): Promise<FbCopyPasteBlock> => {
    const response = await apiClient.post<FbCopyPasteBlock>(
      `/api/facebook/items/${itemId}/copy-paste`,
    );
    return response.data;
  },
  downloadImagesZip: async (itemId: string): Promise<void> => {
    await downloadGet(`/api/facebook/items/${itemId}/images.zip`, {
      fallback: `item-${itemId}-images.zip`,
    });
  },
  exportItems: async (request: FbCatalogExportRequest): Promise<void> => {
    await downloadPost('/api/facebook/export', request, {
      fallback: 'whis-facebook-catalog.csv',
    });
  },
};

export type {
  FbAvailability,
  FbCatalogExportRequest,
  FbCategoriesResponse,
  FbCondition,
  FbCopyPasteBlock,
  FbFieldsData,
} from '../types/facebook';
