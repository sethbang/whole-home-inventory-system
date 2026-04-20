export interface ValueByCategory {
  category: string;
  item_count: number;
  total_value: number;
}

export interface ValueByLocation {
  location: string;
  item_count: number;
  total_value: number;
}

export interface ValueTrends {
  total_purchase_value: number;
  total_current_value: number;
  value_change: number;
  value_change_percentage: number;
}

export interface WarrantyItem {
  id: string;
  name: string;
  expiration_date: string;
}

export interface WarrantyStatus {
  expiring_soon: WarrantyItem[];
  expired: WarrantyItem[];
  active: WarrantyItem[];
}

export interface AgeBucket {
  count: number;
  total_value: number;
  items: Array<{
    id: string;
    name: string;
    purchase_date: string;
    current_value: number;
  }>;
}

export type AgeAnalysis = Record<string, AgeBucket>;
