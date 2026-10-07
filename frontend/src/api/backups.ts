import type { Backup, BackupList, RestoreResult } from './types';
import { apiClient } from './http';
import { downloadGet } from './download';
import type { JobReference } from './jobs';

/**
 * v3.0: create/commit responses are discriminated unions. When the ARQ
 * worker is active the backend returns a JobReference and the UI polls
 * via useJobPoll; otherwise it returns the completed resource inline.
 */
export type BackupCreateResponse = JobReference | Backup;
export type RestoreCommitResponse = JobReference | RestoreResult;

export const backups = {
  list: async (): Promise<BackupList> => {
    const response = await apiClient.get<BackupList>('/api/backups');
    return response.data;
  },
  create: async (): Promise<BackupCreateResponse> => {
    const response = await apiClient.post<BackupCreateResponse>('/api/backups');
    return response.data;
  },
  /**
   * Non-destructive preview. Always safe — returns the counts that a commit
   * would change but touches no data. Required first step of the v2.1
   * two-phase restore contract.
   */
  previewRestore: async (backupId: string): Promise<RestoreResult> => {
    const response = await apiClient.post<RestoreResult>(
      `/api/backups/${backupId}/restore`,
      undefined,
      { params: { dry_run: true } },
    );
    return response.data;
  },
  /**
   * Destructive commit. ``confirmItemCount`` must match the server-side
   * item count (which the preview returned). A mismatch is rejected with
   * 409 rather than proceeding — guards against stale-UI races.
   *
   * Response is a discriminated union: on deployments with the worker
   * profile active the server returns a JobReference and the caller
   * should poll. Otherwise it returns the completed RestoreResult
   * inline (sync fallback).
   */
  commitRestore: async (
    backupId: string,
    confirmItemCount: number,
  ): Promise<RestoreCommitResponse> => {
    const response = await apiClient.post<RestoreCommitResponse>(
      `/api/backups/${backupId}/restore`,
      { confirm_item_count: confirmItemCount },
      { params: { dry_run: false } },
    );
    return response.data;
  },
  upload: async (file: File): Promise<Backup> => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await apiClient.post<Backup>(
      '/api/backups/upload',
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } },
    );
    return response.data;
  },
  delete: async (backupId: string): Promise<void> => {
    await apiClient.delete(`/api/backups/${backupId}`);
  },
  download: (backupId: string, fallback = 'backup.zip'): Promise<void> =>
    // Auth is JWT-in-Authorization-header, so a plain `window.open` request
    // wouldn't carry credentials and the server would 401. Fetch the blob
    // through the authenticated axios client instead, then synthesize a
    // download via a hidden anchor.
    downloadGet(`/api/backups/${backupId}/download`, { fallback }),
};

export type { Backup, BackupList, RestoreResult };
