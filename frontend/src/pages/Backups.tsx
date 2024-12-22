import React, { useEffect, useState } from 'react';
import { backups, Backup } from '../api/client';
import { format } from 'date-fns';

const Backups: React.FC = () => {
  const [backupList, setBackupList] = useState<Backup[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [restoring, setRestoring] = useState(false);
  const [selectedBackup, setSelectedBackup] = useState<string | null>(null);

  const loadBackups = async () => {
    try {
      setLoading(true);
      const response = await backups.list();
      setBackupList(response.backups);
      setError(null);
    } catch (err) {
      setError('Failed to load backups');
      console.error('Error loading backups:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadBackups();
  }, []);

  const handleCreateBackup = async () => {
    try {
      setLoading(true);
      await backups.create();
      await loadBackups();
    } catch (err) {
      setError('Failed to create backup');
      console.error('Error creating backup:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleRestore = async (backupId: string) => {
    if (!window.confirm('Are you sure you want to restore from this backup? This will replace all current data.')) {
      return;
    }

    try {
      setRestoring(true);
      setSelectedBackup(backupId);
      const result = await backups.restore(backupId);
      if (result.success) {
        alert(`Restore completed successfully!\nItems restored: ${result.items_restored}\nImages restored: ${result.images_restored}`);
      } else {
        throw new Error(result.message);
      }
    } catch (err) {
      setError('Failed to restore backup');
      console.error('Error restoring backup:', err);
    } finally {
      setRestoring(false);
      setSelectedBackup(null);
    }
  };

  const handleDelete = async (backupId: string) => {
    if (!window.confirm('Are you sure you want to delete this backup?')) {
      return;
    }

    try {
      await backups.delete(backupId);
      await loadBackups();
    } catch (err) {
      setError('Failed to delete backup');
      console.error('Error deleting backup:', err);
    }
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

  if (loading && !backupList.length) {
    return (
      <div className="p-6">
        <div className="flex items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Backups</h1>
        <button
          onClick={handleCreateBackup}
          disabled={loading}
          className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded disabled:opacity-50"
        >
          Create New Backup
        </button>
      </div>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
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
            {backupList.map((backup) => (
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
                        onClick={() => handleRestore(backup.id)}
                        disabled={restoring}
                        className="text-indigo-600 hover:text-indigo-900 disabled:opacity-50"
                      >
                        {restoring && selectedBackup === backup.id ? 'Restoring...' : 'Restore'}
                      </button>
                      <button
                        onClick={() => backups.download(backup.id)}
                        className="text-blue-600 hover:text-blue-900"
                      >
                        Download
                      </button>
                      <button
                        onClick={() => handleDelete(backup.id)}
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
    </div>
  );
};

export default Backups;