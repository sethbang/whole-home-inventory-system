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
    } catch (error: any) {
      if (error?.response?.data) {
        console.error('Export failed:', error.response.data);
        setImportError(`Export failed: ${error.response.data.detail || 'Please try again.'}`);
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
    <div className="bg-white shadow rounded-lg p-6">
      <h2 className="text-xl font-semibold mb-4">Data Migration Tools</h2>
      
      <div className="space-y-6">
        {/* Export Section */}
        <div>
          <h3 className="text-lg font-medium mb-2">Export Items</h3>
          <p className="text-gray-600 mb-3">Download your items in CSV or JSON format</p>
          <div className="flex space-x-4">
            <button
              onClick={() => handleExport('csv')}
              className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              Export as CSV
            </button>
            <button
              onClick={() => handleExport('json')}
              className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500"
            >
              Export as JSON
            </button>
          </div>
        </div>

        {/* Import Section */}
        <div>
          <h3 className="text-lg font-medium mb-2">Import Items</h3>
          <p className="text-gray-600 mb-3">Upload items from a CSV or JSON file</p>
          <div className="flex flex-col space-y-4">
            <input
              type="file"
              accept=".csv,.json"
              onChange={handleImport}
              className="block w-full text-sm text-gray-500
                file:mr-4 file:py-2 file:px-4
                file:rounded file:border-0
                file:text-sm file:font-semibold
                file:bg-blue-50 file:text-blue-700
                hover:file:bg-blue-100"
            />
            {importStatus && (
              <p className="text-green-600">{importStatus}</p>
            )}
            {importError && (
              <p className="text-red-600 whitespace-pre-line">{importError}</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default DataMigration;