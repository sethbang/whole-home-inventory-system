import axios from 'axios';
import type { EbayFieldsData } from '../components/EbayFields';

// In development, use relative URLs that will be handled by Vite's proxy
const API_URL = '';

export const apiClient = axios.create({
  baseURL: API_URL,
  withCredentials: true,
  // Disable SSL certificate validation in development
  ...(import.meta.env.DEV && {
    httpsAgent: {
      rejectUnauthorized: false
    }
  })
});

// Development flag to bypass authentication (must match AuthContext)
const BYPASS_AUTH = true;

// Add auth token to requests if available
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('whis_token');
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle auth errors
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('whis_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface RegisterData {
  email: string;
  username: string;
  password: string;
}

export interface User {
  id: string;
  email: string;
  username: string;
  is_active: boolean;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
}

export const auth = {
  login: async (credentials: LoginCredentials): Promise<AuthResponse> => {
    try {
      console.log('Attempting login with:', credentials.username);
      
      const params = new URLSearchParams();
      params.append('grant_type', 'password');
      params.append('username', credentials.username);
      params.append('password', credentials.password);
      
      const response = await apiClient.post<AuthResponse>('/api/token', params, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
      });
      
      console.log('Login response:', response.data);
      return response.data;
    } catch (error: any) {
      console.error('Login error:', error.response?.data || error.message);
      throw error;
    }
  },
  register: async (data: RegisterData): Promise<User> => {
    const response = await apiClient.post<User>('/api/register', data);
    return response.data;
  },
  getCurrentUser: async (): Promise<User> => {
    const response = await apiClient.get<User>('/api/users/me');
    return response.data;
  },
};

export interface Item {
  id: string;
  name: string;
  category: string;
  location: string;
  brand?: string;
  model_number?: string;
  serial_number?: string;
  purchase_date?: string;
  purchase_price?: number;
  current_value?: number;
  warranty_expiration?: string;
  notes?: string;
  custom_fields?: Record<string, any>;
  created_at: string;
  updated_at: string;
  images: ItemImage[];
}

export interface ItemImage {
  id: string;
  filename: string;
  file_path: string;
  created_at: string;
}

export interface SearchFilters {
  query?: string;
  category?: string;
  location?: string;
  min_value?: number;
  max_value?: number;
  sort_by?: string;
  sort_desc?: boolean;
  page?: number;
  page_size?: number;
}

export interface ItemListResponse {
  items: Item[];
  total: number;
  page: number;
  page_size: number;
}

// Dev helper to generate dummy item data
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
    custom_fields: {}
  };
};

export const items = {
  list: async (filters: SearchFilters = {}): Promise<ItemListResponse> => {
    const response = await apiClient.get<ItemListResponse>('/api/items', { params: filters });
    return response.data;
  },
  get: async (id: string): Promise<Item> => {
    const response = await apiClient.get<Item>(`/api/items/${id}`);
    return response.data;
  },
  create: async (data: Partial<Item>, isDev: boolean = false): Promise<Item> => {
    let itemData = isDev ? generateDummyItem() : data;
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
  bulkDelete: async (itemIds: string[]): Promise<{ status: string; deleted_count: number }> => {
    const response = await apiClient.post<{ status: string; deleted_count: number }>(
      '/api/items/bulk-delete',
      { item_ids: itemIds }
    );
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
      if ((error as any)?.response?.status === 404) {
        return null;
      }
      throw error;
    }
  },
};

export const images = {
  upload: async (itemId: string, file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await apiClient.post(`/api/items/${itemId}/images`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },
  list: async (itemId: string) => {
    const response = await apiClient.get(`/api/items/${itemId}/images`);
    return response.data;
  },
  delete: async (imageId: string) => {
    await apiClient.delete(`/api/images/${imageId}`);
  },
};

export interface EbayCategoryResponse {
  categories: Array<{
    id: string;
    name: string;
    subcategories?: Array<{
      id: string;
      name: string;
    }>;
  }>;
  suggested_category?: {
    id: string;
    name: string;
  };
}

export interface EbayExportResponse {
  success: boolean;
  file_url?: string;
  message: string;
  errors?: string[];
  items_processed: number;
}

// eBay integration
export const ebay = {
  getCategories: async (itemId?: string): Promise<EbayCategoryResponse> => {
    const response = await apiClient.get<EbayCategoryResponse>('/api/ebay/categories', {
      params: itemId ? { item_id: itemId } : undefined
    });
    return response.data;
  },
  updateFields: async (itemId: string, fields: EbayFieldsData): Promise<EbayFieldsData> => {
    const response = await apiClient.post<EbayFieldsData>(`/api/ebay/items/${itemId}/ebay-fields`, fields);
    return response.data;
  },
  exportItems: async (itemIds: string[], defaultFields?: EbayFieldsData): Promise<EbayExportResponse> => {
    const response = await apiClient.post<EbayExportResponse>('/api/ebay/export', {
      item_ids: itemIds,
      default_fields: defaultFields
    });
    return response.data;
  },
};
