/**
 * Item-value pricing API client (v3.1).
 *
 * All three endpoints return a discriminated union:
 * - `JobReference` when the worker enqueues a refresh.
 * - `PriceEstimateEnvelope` when the cache answered synchronously,
 *   when the sync fallback ran, or on force-refresh without the
 *   worker.
 *
 * Consumers check via the `isJobReference` type guard and pass the
 * job id into `useJobPoll`; when the poll resolves, the envelope
 * arrives under `data.result`.
 */

import { apiClient } from './http';
import type {
  JobReference,
  PriceEstimateEnvelope,
} from './types';

export type PricingResponse = JobReference | PriceEstimateEnvelope;

export interface EstimateRequest {
  item_id?: string;
  metadata?: Record<string, unknown>;
}

export const pricing = {
  estimate: async (body: EstimateRequest): Promise<PricingResponse> => {
    const response = await apiClient.post<PricingResponse>(
      '/api/pricing/estimate',
      body,
    );
    return response.data;
  },
  refresh: async (itemId: string): Promise<PricingResponse> => {
    const response = await apiClient.post<PricingResponse>(
      `/api/pricing/refresh/${itemId}`,
    );
    return response.data;
  },
  getCached: async (itemId: string): Promise<PricingResponse> => {
    const response = await apiClient.get<PricingResponse>(
      `/api/pricing/estimate/${itemId}`,
    );
    return response.data;
  },
};
