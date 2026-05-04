/**
 * LLM operator-config client (v3.2).
 *
 * Talks to the admin-only ``/api/llm-config*`` surface. Every method
 * here assumes the caller has an admin session — non-admins get 403
 * from the backend; the page-level guard in App.tsx redirects them
 * before any of these functions run.
 */

import { apiClient } from './http';
import type {
  LLMConfigRead,
  LLMConfigUpdate,
  LLMModelListResponse,
  LLMTestResponse,
  LLMVisionTestResponse,
} from './types';

export const llmConfig = {
  get: async (): Promise<LLMConfigRead> => {
    const response = await apiClient.get<LLMConfigRead>('/api/llm-config');
    return response.data;
  },

  update: async (payload: LLMConfigUpdate): Promise<LLMConfigRead> => {
    const response = await apiClient.put<LLMConfigRead>(
      '/api/llm-config',
      payload,
    );
    return response.data;
  },

  listModels: async (): Promise<LLMModelListResponse> => {
    const response = await apiClient.get<LLMModelListResponse>(
      '/api/llm-config/models',
    );
    return response.data;
  },

  testQuick: async (
    payload?: LLMConfigUpdate | null,
  ): Promise<LLMTestResponse> => {
    const response = await apiClient.post<LLMTestResponse>(
      '/api/llm-config/test',
      payload ?? null,
    );
    return response.data;
  },

  testVision: async (
    payload?: LLMConfigUpdate | null,
  ): Promise<LLMVisionTestResponse> => {
    const response = await apiClient.post<LLMVisionTestResponse>(
      '/api/llm-config/test-vision',
      payload ?? null,
    );
    return response.data;
  },
};
