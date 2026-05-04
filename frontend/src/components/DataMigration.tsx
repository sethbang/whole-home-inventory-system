import React, { useState } from 'react';
import { apiClient } from '../api/client';

interface ImportResult {
  success: boolean;
  message: string;
  items_imported: number;
  errors?: string[];
}

const DataMigration: React.FC = () => {
  const [importStatus, setImportStatus] = useState<string>('');
  const [importError, setImportError] = useState<string>('');

  const handleExport = async (format: 'csv' | 'json') => {
    try {
      const response = await apiClient.get<Blob>('/api/items/export/data', {
        params: { format },
        responseType: 'blob',
        headers: {
          'Accept': format === 'csv' ? 'text/csv' : 'application/json'
        }
      });
      
      // Create blob link to download
      const url = window.URL.createObjectURL(response.data);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `items_export.${format}`);
      
      // Start download
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      if (err.response?.data) {
        console.error('Export failed:', err.response.data);
        setImportError(`Export failed: ${err.response.data.detail || 'Please try again.'}`);
      } else {
        console.error('Export failed:', error);
        setImportError('Export failed. Please try again.');
      }
    }
  };

  const handleImport = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Check file extension
    const fileExt = file.name.split('.').pop()?.toLowerCase();
    if (fileExt !== 'csv' && fileExt !== 'json') {
      setImportError('Please upload a CSV or JSON file');
      return;
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
      setImportStatus('Importing...');
      setImportError('');

      const response = await apiClient.post<ImportResult>('/api/items/import', formData, {
        headers: {
          'Accept': 'application/json'
        }
      });
      
      if (response.data.success) {
        setImportStatus(`Successfully imported ${response.data.items_imported} items`);
        if (response.data.errors && response.data.errors.length > 0) {
          setImportError(`Some items had errors:\n${response.data.errors.join('\n')}`);
        }
      } else {
        setImportError('Import failed. Please try again.');
      }
    } catch (error) {
      console.error('Import failed:', error);
      setImportError('Import failed. Please try again.');
    }
  };

  return (
    <div className="bg-surface-raised shadow rounded-lg p-6">
      <h2 className="text-xl font-semibold mb-4">Data Migration Tools</h2>
      
      <div className="space-y-6">
        {/* Export Section */}
        <div>
          <h3 className="text-lg font-medium mb-2">Export Items</h3>
          <p className="text-muted mb-3">Download your items in CSV or JSON format</p>
          <div className="flex space-x-4">
            <button
              onClick={() => handleExport('csv')}
              className="bg-primary text-white px-4 py-2 rounded hover:bg-primary-hover focus:outline-none focus:ring-2 focus:ring-primary"
            >
              Export as CSV
            </button>
            <button
              onClick={() => handleExport('json')}
              className="bg-success text-white px-4 py-2 rounded hover:bg-success/85 focus:outline-none focus:ring-2 focus:ring-success"
            >
              Export as JSON
            </button>
          </div>
        </div>

        {/* Import Section */}
        <div>
          <h3 className="text-lg font-medium mb-2">Import Items</h3>
          <p className="text-muted mb-3">Upload items from a CSV or JSON file</p>
          <div className="flex flex-col space-y-4">
            <input
              type="file"
              accept=".csv,.json"
              onChange={handleImport}
              className="block w-full text-sm text-subtle
                file:mr-4 file:py-2 file:px-4
                file:rounded file:border-0
                file:text-sm file:font-semibold
                file:bg-primary-subtle file:text-primary
                hover:file:bg-primary-subtle"
            />
            {importStatus && (
              <p className="text-success">{importStatus}</p>
            )}
            {importError && (
              <p className="text-danger whitespace-pre-line">{importError}</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default DataMigration;