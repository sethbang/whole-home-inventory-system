import type {
  AgeAnalysis,
  ValueByCategory,
  ValueByLocation,
  ValueTrends,
  WarrantyStatus,
} from './types';
import { apiClient } from './http';

export const analytics = {
  getValueByCategory: async (): Promise<ValueByCategory[]> => {
    const response = await apiClient.get<ValueByCategory[]>(
      '/api/analytics/value-by-category',
    );
    return response.data;
  },
  getValueByLocation: async (): Promise<ValueByLocation[]> => {
    const response = await apiClient.get<ValueByLocation[]>(
      '/api/analytics/value-by-location',
    );
    return response.data;
  },
  getValueTrends: async (): Promise<ValueTrends> => {
    const response = await apiClient.get<ValueTrends>(
      '/api/analytics/value-trends',
    );
    return response.data;
  },
  getWarrantyStatus: async (): Promise<WarrantyStatus> => {
    const response = await apiClient.get<WarrantyStatus>(
      '/api/analytics/warranty-status',
    );
    return response.data;
  },
  getAgeAnalysis: async (): Promise<AgeAnalysis> => {
    const response = await apiClient.get<AgeAnalysis>(
      '/api/analytics/age-analysis',
    );
    return response.data;
  },
};

export type {
  AgeAnalysis,
  ValueByCategory,
  ValueByLocation,
  ValueTrends,
  WarrantyStatus,
};
