import type { Item, ItemListResponse, SearchFilters } from '../types/items';
import { apiClient } from './http';

/** Dev helper for the "random item" button on AddItem. Isolated so
 * production code doesn't accidentally pull its generator into the bundle. */
const generateDummyItem = (): Partial<Item> => {
  const categories = ['Electronics', 'Furniture', 'Kitchen', 'Tools', 'Clothing'];
  const locations = ['Living Room', 'Kitchen', 'Garage', 'Bedroom', 'Office'];
  const brands = ['Samsung', 'Apple', 'Sony', 'LG', 'Dell'];

  const randomDate = () => {
    const date = new Date();
    date.setDate(date.getDate() - Math.floor(Math.random() * 365));
    return date.toISOString();
  };

  return {
    name: `Test Item ${Math.floor(Math.random() * 1000)}`,
    category: categories[Math.floor(Math.random() * categories.length)],
    location: locations[Math.floor(Math.random() * locations.length)],
    brand: brands[Math.floor(Math.random() * brands.length)],
    model_number: `MODEL-${Math.floor(Math.random() * 10000)}`,
    serial_number: `SN-${Math.floor(Math.random() * 100000)}`,
    purchase_date: randomDate(),
    purchase_price: Math.floor(Math.random() * 1000),
    current_value: Math.floor(Math.random() * 800),
    warranty_expiration: randomDate(),
    notes: 'This is a test item generated in dev mode',
    custom_fields: {},
  };
};

export const items = {
  list: async (filters: SearchFilters = {}): Promise<ItemListResponse> => {
    const response = await apiClient.get<ItemListResponse>('/api/items', {
      params: filters,
    });
    return response.data;
  },
  get: async (id: string): Promise<Item> => {
    const response = await apiClient.get<Item>(`/api/items/${id}`);
    return response.data;
  },
  create: async (data: Partial<Item>, isDev = false): Promise<Item> => {
    const itemData = isDev ? generateDummyItem() : data;
    const response = await apiClient.post<Item>('/api/items', itemData);
    return response.data;
  },
  update: async (id: string, data: Partial<Item>): Promise<Item> => {
    const response = await apiClient.put<Item>(`/api/items/${id}`, data);
    return response.data;
  },
  delete: async (id: string): Promise<void> => {
    await apiClient.delete(`/api/items/${id}`);
  },
  bulkDelete: async (
    itemIds: string[],
  ): Promise<{ status: string; deleted_count: number }> => {
    const response = await apiClient.post<{
      status: string;
      deleted_count: number;
    }>('/api/items/bulk-delete', { item_ids: itemIds });
    return response.data;
  },
  getCategories: async (): Promise<string[]> => {
    const response = await apiClient.get<string[]>('/api/categories');
    return response.data;
  },
  getLocations: async (): Promise<string[]> => {
    const response = await apiClient.get<string[]>('/api/locations');
    return response.data;
  },
  lookupBarcode: async (barcode: string): Promise<Item | null> => {
    try {
      const response = await apiClient.get<Item>(`/api/items/barcode/${barcode}`);
      return response.data;
    } catch (error) {
      // ApiError from the interceptor — 404 means "no item", anything else
      // propagates up.
      if (
        typeof error === 'object' &&
        error !== null &&
        'statusCode' in error &&
        (error as { statusCode: number }).statusCode === 404
      ) {
        return null;
      }
      throw error;
    }
  },
};

export type { Item, ItemListResponse, SearchFilters };
