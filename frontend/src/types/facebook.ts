export type FbCondition = 'NEW' | 'USED_LIKE_NEW' | 'USED_GOOD' | 'USED_FAIR';

export type FbAvailability = 'in stock' | 'out of stock';

export interface FbFieldsData {
  price?: number;
  condition?: FbCondition;
  category?: string;
  availability?: FbAvailability;
  description_override?: string;
  item_specifics?: Record<string, string>;
}

export interface FbCategoriesResponse {
  categories: string[];
}

export interface FbCopyPasteBlock {
  title: string;
  description: string;
  price?: number;
  suggested_category?: string;
  tags: string[];
  block: string;
}

export interface FbCatalogExportRequest {
  item_ids: string[];
  default_fields?: FbFieldsData;
}
