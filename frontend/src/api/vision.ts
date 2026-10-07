/**
 * Vision auto-fill API client (v3.1).
 *
 * `POST /api/vision/identify` returns a discriminated union:
 * - `JobReference` when the ARQ worker is active → poll
 *   `GET /api/jobs/{id}` via useJobPoll.
 * - Full `VisionResult` when the sync fallback fires.
 *
 * Use `isJobReference` from `./jobs` to branch.
 */

import { apiClient } from './http';
import type { JobReference, VisionResult } from './types';

export type VisionIdentifyResponse = JobReference | VisionResult;

export interface VisionIdentifyOptions {
  images: File[];
  hints?: Record<string, unknown>;
}

export const vision = {
  identify: async (
    options: VisionIdentifyOptions,
  ): Promise<VisionIdentifyResponse> => {
    const formData = new FormData();
    for (const file of options.images) {
      formData.append('files', file);
    }
    if (options.hints) {
      formData.append('hints', JSON.stringify(options.hints));
    }
    const response = await apiClient.post<VisionIdentifyResponse>(
      '/api/vision/identify',
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } },
    );
    return response.data;
  },
};
