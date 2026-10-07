import type { ItemImage } from './types';
import { apiClient } from './http';

export const images = {
  upload: async (itemId: string, file: File): Promise<ItemImage> => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await apiClient.post<ItemImage>(
      `/api/items/${itemId}/images`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      },
    );
    return response.data;
  },
  list: async (itemId: string): Promise<ItemImage[]> => {
    const response = await apiClient.get<ItemImage[]>(`/api/items/${itemId}/images`);
    return response.data;
  },
  delete: async (imageId: string): Promise<void> => {
    await apiClient.delete(`/api/images/${imageId}`);
  },
};

export type { ItemImage };
