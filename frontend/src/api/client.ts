import axios from 'axios';

const API_URL = 'http://localhost:8000/api';

export const apiClient = axios.create({
  baseURL: API_URL,
  withCredentials: true,
});

// Development flag to bypass authentication (must match AuthContext)
const BYPASS_AUTH = true;

// Add auth token to requests if available and not in bypass mode
apiClient.interceptors.request.use((config) => {
  if (!BYPASS_AUTH) {
    const token = localStorage.getItem('whis_token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

// Handle auth errors when not in bypass mode
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (!BYPASS_AUTH && error.response?.status === 401) {
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
      
      const response = await apiClient.post<AuthResponse>('/token', params, {
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
    const response = await apiClient.post<User>('/register', data);
    return response.data;
  },
  getCurrentUser: async (): Promise<User> => {
    const response = await apiClient.get<User>('/users/me');
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
    const response = await apiClient.get<ItemListResponse>('/items', { params: filters });
    return response.data;
  },
  get: async (id: string): Promise<Item> => {
    const response = await apiClient.get<Item>(`/items/${id}`);
    return response.data;
  },
  create: async (data: Partial<Item>, isDev: boolean = false): Promise<Item> => {
    let itemData = isDev ? generateDummyItem() : data;
    const response = await apiClient.post<Item>('/items', itemData);
    return response.data;
  },
  update: async (id: string, data: Partial<Item>): Promise<Item> => {
    const response = await apiClient.put<Item>(`/items/${id}`, data);
    return response.data;
  },
  delete: async (id: string): Promise<void> => {
    await apiClient.delete(`/items/${id}`);
  },
  getCategories: async (): Promise<string[]> => {
    const response = await apiClient.get<string[]>('/categories');
    return response.data;
  },
  getLocations: async (): Promise<string[]> => {
    const response = await apiClient.get<string[]>('/locations');
    return response.data;
  },
};

export const images = {
  upload: async (itemId: string, file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await apiClient.post(`/items/${itemId}/images`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },
  list: async (itemId: string) => {
    const response = await apiClient.get(`/items/${itemId}/images`);
    return response.data;
  },
  delete: async (imageId: string) => {
    await apiClient.delete(`/images/${imageId}`);
  },
};
