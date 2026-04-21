import { useMemo, useState } from 'react';
import { format } from 'date-fns';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

import { backups } from '../api/backups';
import { apiErrorMessage } from '../api/errors';
import { queryKeys } from '../api/queryKeys';
import type { Backup, RestoreResult } from '../types/backups';

// ---------------------------------------------------------------------------
// Restore dialog — two-phase, matches the v2.1 server contract.
// ---------------------------------------------------------------------------

interface RestoreDialogProps {
  backupId: string;
  preview: RestoreResult;
  onClose: () => void;
  onCommitted: (result: RestoreResult) => void;
}

function makeConfirmSchema(expectedCount: number) {
  return z.object({
    confirm: z
      .string()
      .transform((v) => parseInt(v, 10))
      .refine(
        (n) => !Number.isNaN(n) && n === expectedCount,
        { message: `Type ${expectedCount} to confirm.` },
      ),
  });
}

function RestoreDialog({
  backupId,
  preview,
  onClose,
  onCommitted,
}: RestoreDialogProps) {
  const [serverError, setServerError] = useState<string | null>(null);
  const expected = preview.current_item_count ?? 0;

  const confirmSchema = useMemo(() => makeConfirmSchema(expected), [expected]);
  type ConfirmValues = z.infer<typeof confirmSchema>;

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<{ confirm: string }, unknown, ConfirmValues>({
    resolver: zodResolver(confirmSchema),
    defaultValues: { confirm: '' },
  });

  const commit = useMutation({
    mutationFn: (values: ConfirmValues) =>
      backups.commitRestore(backupId, values.confirm),
    onSuccess: (result) => onCommitted(result),
    onError: (err) => setServerError(apiErrorMessage(err, 'Restore failed')),
  });

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="restore-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
    >
      <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
        <h2 id="restore-title" className="text-lg font-semibold text-gray-900">
          Restore backup?
        </h2>
        <p className="mt-2 text-sm text-gray-700">
          This will <strong>delete {expected} existing item(s)</strong> and
          replace them with{' '}
          <strong>{preview.backup_item_count ?? 0} item(s)</strong> (plus{' '}
          {preview.backup_image_count ?? 0} image(s)) from the archive. This
          cannot be undone.
        </p>
        <p className="mt-3 text-sm text-gray-700">
          Type <strong>{expected}</strong> below to confirm.
        </p>

        <form
          className="mt-4 space-y-3"
          onSubmit={handleSubmit((values) => {
            setServerError(null);
            commit.mutate(values);
          })}
          noValidate
        >
          {serverError && (
            <div role="alert" className="rounded-md bg-red-50 p-3 text-sm text-red-700">
              {serverError}
            </div>
          )}

          <input
            type="number"
            aria-label="Confirm item count"
            aria-invalid={errors.confirm ? 'true' : 'false'}
            {...register('confirm')}
            className="block w-full rounded-md border-gray-300 shadow-sm focus:border-primary focus:ring-primary sm:text-sm"
          />
          {errors.confirm && (
            <p className="text-sm text-red-600">{errors.confirm.message}</p>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="rounded-md border border-transparent bg-red-600 px-3 py-1.5 text-sm font-medium text-white shadow-sm hover:bg-red-700 disabled:opacity-60"
            >
              {isSubmitting ? 'Restoring…' : 'Restore'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Backups page
// ---------------------------------------------------------------------------

export default function Backups() {
  const queryClient = useQueryClient();
  const [serverError, setServerError] = useState<string | null>(null);
  const [pending, setPending] = useState<{
    backupId: string;
    preview: RestoreResult;
  } | null>(null);

  const { data: backupList = [], isLoading } = useQuery({
    queryKey: queryKeys.backups.list(),
    queryFn: async () => (await backups.list()).backups,
  });

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: queryKeys.backups.list() });

  const createBackup = useMutation({
    mutationFn: () => backups.create(),
    onSuccess: () => invalidate(),
    onError: (err) => setServerError(apiErrorMessage(err, 'Failed to create backup')),
  });

  const uploadBackup = useMutation({
    mutationFn: (file: File) => backups.upload(file),
    onSuccess: () => invalidate(),
    onError: (err) => setServerError(apiErrorMessage(err, 'Failed to upload backup')),
  });

  const deleteBackup = useMutation({
    mutationFn: (backupId: string) => backups.delete(backupId),
    onSuccess: () => invalidate(),
    onError: (err) => setServerError(apiErrorMessage(err, 'Failed to delete backup')),
  });

  const previewRestore = useMutation({
    mutationFn: (backupId: string) => backups.previewRestore(backupId),
    onSuccess: (preview, backupId) => setPending({ backupId, preview }),
    onError: (err) => setServerError(apiErrorMessage(err, 'Failed to preview restore')),
  });

  const handleRestoreCommitted = (result: RestoreResult) => {
    setPending(null);
    // Inventory just changed — invalidate everything item-adjacent.
    queryClient.invalidateQueries({ queryKey: queryKeys.items.all });
    queryClient.invalidateQueries({ queryKey: queryKeys.analytics.all });
    setServerError(null);
    alert(
      `Restore completed successfully!\nItems restored: ${result.items_restored}\nImages restored: ${result.images_restored}`,
    );
  };

  const formatSize = (bytes: number): string => {
    const units = ['B', 'KB', 'MB', 'GB'];
    let size = bytes;
    let unitIndex = 0;
    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024;
      unitIndex++;
    }
    return `${size.toFixed(1)} ${units[unitIndex]}`;
  };

  if (isLoading && backupList.length === 0) {
    return (
      <div className="p-6">
        <div className="flex items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
        </div>
      </div>
    );
  }

  const busy =
    createBackup.isPending ||
    uploadBackup.isPending ||
    deleteBackup.isPending ||
    previewRestore.isPending;

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Backups</h1>
        <div className="flex gap-4">
          <label className="bg-green-500 hover:bg-green-600 text-white px-4 py-2 rounded cursor-pointer disabled:opacity-50">
            <input
              type="file"
              accept=".zip"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (!file) return;
                setServerError(null);
                uploadBackup.mutate(file);
                e.target.value = '';
              }}
              disabled={busy}
            />
            Upload Backup
          </label>
          <button
            onClick={() => {
              setServerError(null);
              createBackup.mutate();
            }}
            disabled={busy}
            className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded disabled:opacity-50"
          >
            Create New Backup
          </button>
        </div>
      </div>

      {serverError && (
        <div
          role="alert"
          className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4"
        >
          {serverError}
        </div>
      )}

      <div className="bg-white rounded-lg shadow overflow-x-auto">
        <table className="min-w-[800px] w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Created At
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Size
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Items
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {backupList.map((backup: Backup) => (
              <tr key={backup.id}>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {format(new Date(backup.created_at), 'PPp')}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {formatSize(backup.size_bytes)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {backup.item_count} items, {backup.image_count} images
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span
                    className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full
                      ${backup.status === 'completed' ? 'bg-green-100 text-green-800' : ''}
                      ${backup.status === 'failed' ? 'bg-red-100 text-red-800' : ''}
                      ${backup.status === 'in_progress' ? 'bg-yellow-100 text-yellow-800' : ''}`}
                  >
                    {backup.status}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium space-x-2">
                  {backup.status === 'completed' && (
                    <>
                      <button
                        onClick={() => {
                          setServerError(null);
                          previewRestore.mutate(backup.id);
                        }}
                        disabled={busy}
                        className="text-indigo-600 hover:text-indigo-900 disabled:opacity-50"
                      >
                        {previewRestore.isPending &&
                        previewRestore.variables === backup.id
                          ? 'Loading…'
                          : 'Restore'}
                      </button>
                      <button
                        onClick={() => backups.download(backup.id)}
                        className="text-blue-600 hover:text-blue-900"
                      >
                        Download
                      </button>
                      <button
                        onClick={() => {
                          if (
                            window.confirm(
                              'Are you sure you want to delete this backup?',
                            )
                          ) {
                            deleteBackup.mutate(backup.id);
                          }
                        }}
                        className="text-red-600 hover:text-red-900"
                      >
                        Delete
                      </button>
                    </>
                  )}
                  {backup.status === 'failed' && (
                    <span className="text-red-600" title={backup.error_message}>
                      Failed: {backup.error_message}
                    </span>
                  )}
                  {backup.status === 'in_progress' && (
                    <span className="text-yellow-600">Processing...</span>
                  )}
                </td>
              </tr>
            ))}
            {backupList.length === 0 && (
              <tr>
                <td colSpan={5} className="px-6 py-4 text-center text-gray-500">
                  No backups found. Create your first backup to protect your data.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {pending && (
        <RestoreDialog
          backupId={pending.backupId}
          preview={pending.preview}
          onClose={() => setPending(null)}
          onCommitted={handleRestoreCommitted}
        />
      )}
    </div>
  );
}
