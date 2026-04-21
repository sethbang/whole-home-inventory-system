/**
 * Shared axios instance + interceptors.
 *
 * Separated from the per-resource modules so those modules can import the
 * instance without creating a circular dependency through ``client.ts``
 * (which is now a barrel re-export for backward compat).
 */

import axios, { AxiosError } from 'axios';

import { logger } from '../lib/logger';
import { ApiError } from './errors';

// Dev uses Vite's proxy; prod runs against the same origin as the static
// assets (nginx / caddy), so a blank baseURL works for both.
const API_URL = '';

// v2.4: restored to `import.meta.env.DEV` now that Vitest is the test
// runner. The v2.3 NODE_ENV workaround existed only for ts-jest's
// CommonJS compilation.
const isDev = import.meta.env.DEV;

export const apiClient = axios.create({
  baseURL: API_URL,
  withCredentials: true,
  ...(isDev && {
    httpsAgent: {
      rejectUnauthorized: false,
    },
  }),
});

// Attach the stored JWT on every outbound request, if any.
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('whis_token');
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

/**
 * Normalize every axios failure into an ApiError before rejecting.
 * Also handles 401s by clearing the stored token and redirecting to /login.
 */
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('whis_token');
      // Keep redirect scoped to browser context — guard against jsdom / node.
      if (typeof window !== 'undefined') {
        window.location.href = '/login';
      }
    }

    const status = error.response?.status ?? 0;
    const data = error.response?.data as
      | { detail?: string; errors?: Record<string, string[]> }
      | undefined;
    const detail =
      (typeof data?.detail === 'string' && data.detail) ||
      error.message ||
      'Network error';
    const apiError = new ApiError(status, detail, data?.errors);

    logger.debug('apiClient error', { status, detail });
    return Promise.reject(apiError);
  },
);
