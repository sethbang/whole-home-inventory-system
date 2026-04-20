import type { Backup, BackupList, RestoreResult } from '../types/backups';
import { apiClient } from './http';

export const backups = {
  list: async (): Promise<BackupList> => {
    const response = await apiClient.get<BackupList>('/api/backups');
    return response.data;
  },
  create: async (): Promise<Backup> => {
    const response = await apiClient.post<Backup>('/api/backups');
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
   */
  commitRestore: async (
    backupId: string,
    confirmItemCount: number,
  ): Promise<RestoreResult> => {
    const response = await apiClient.post<RestoreResult>(
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
  download: (backupId: string): void => {
    // Trigger a browser download via a new tab; Content-Disposition header
    // lives on the server.
    window.open(`/api/backups/${backupId}/download`, '_blank');
  },
  /**
   * @deprecated v2.1 changed restore to a two-phase contract
   * (``previewRestore`` + ``commitRestore``). This alias forwards to
   * ``previewRestore`` so Backups.tsx keeps compiling until the v2.3
   * UI rewrite wires the two-phase flow. Do not use in new code.
   */
  restore: async (backupId: string): Promise<RestoreResult> => {
    return backups.previewRestore(backupId);
  },
};

export type { Backup, BackupList, RestoreResult };
