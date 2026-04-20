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
