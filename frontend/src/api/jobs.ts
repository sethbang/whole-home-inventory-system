/**
 * Background job polling (v3.0).
 *
 * Pairs with `GET /api/jobs/{job_id}` on the backend. Service-layer
 * enqueuers return a `JobReference` (``{ kind: 'job', job_id }``) when
 * the ARQ worker is active, otherwise they return the full resource
 * inline — consumers branch on the discriminator.
 *
 * ``useJobPoll`` wraps ``useQuery`` with a 1s refetch interval that
 * stops once the job reaches a terminal state. Pages that enqueue
 * work hand the returned ``jobId`` into this hook and render based on
 * the latest status.
 */

import { useQuery } from '@tanstack/react-query';

import { queryKeys } from './queryKeys';
import { apiClient } from './http';

export type JobStatus =
  | 'queued'
  | 'running'
  | 'complete'
  | 'failed'
  | 'not_found';

export interface JobDetail {
  job_id: string;
  status: JobStatus;
  result?: Record<string, unknown> | null;
  error?: string | null;
  queued_at?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
}

export interface JobReference {
  kind: 'job';
  job_id: string;
}

const TERMINAL_STATES: ReadonlySet<JobStatus> = new Set([
  'complete',
  'failed',
  'not_found',
]);

export const jobs = {
  get: async (jobId: string): Promise<JobDetail> => {
    const response = await apiClient.get<JobDetail>(`/api/jobs/${jobId}`);
    return response.data;
  },
};

/**
 * React Query hook that polls ``/api/jobs/{jobId}`` until the job reaches
 * a terminal state. Pass ``null`` when there's no job in flight and the
 * hook stays disabled.
 */
export function useJobPoll(jobId: string | null, pollMs = 1000) {
  return useQuery<JobDetail>({
    queryKey: jobId ? queryKeys.jobs.detail(jobId) : ['jobs', 'detail', 'none'],
    queryFn: () => jobs.get(jobId as string),
    enabled: Boolean(jobId),
    refetchInterval: (query) => {
      const latest = query.state.data;
      if (!latest) return pollMs;
      return TERMINAL_STATES.has(latest.status) ? false : pollMs;
    },
    // Don't retry aggressively — a 404 or 503 should surface to the UI
    // immediately rather than spinning.
    retry: false,
  });
}

export function isJobReference(
  value: unknown,
): value is JobReference {
  return (
    typeof value === 'object' &&
    value !== null &&
    (value as { kind?: unknown }).kind === 'job' &&
    typeof (value as { job_id?: unknown }).job_id === 'string'
  );
}
