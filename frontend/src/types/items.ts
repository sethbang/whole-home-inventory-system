export interface ItemImage {
  id: string;
  filename: string;
  file_path: string;
  created_at: string;
  // v3.0: populated asynchronously by the thumbnail_generate ARQ task.
  // Null while the job is in flight; UI falls back to file_path.
  thumbnail_path?: string | null;
  thumbnail_generated_at?: string | null;
}

export interface Item {
  id: string;
  name: string;
  category: string;
  location: string;
  brand?: string;
  model_number?: string;
  serial_number?: string;
  barcode?: string;
  purchase_date?: string;
  purchase_price?: number;
  current_value?: number;
  warranty_expiration?: string;
  notes?: string;
  custom_fields?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  images: ItemImage[];
  // v2.2 pre-wire fields — always null today, populated by v3.1 pricing.
  estimated_value_low?: number | null;
  estimated_value_median?: number | null;
  estimated_value_high?: number | null;
  price_last_checked?: string | null;
  price_provider?: string | null;
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
