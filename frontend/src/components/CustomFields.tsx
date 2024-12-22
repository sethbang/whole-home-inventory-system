import React from 'react';
import { PlusIcon, XMarkIcon } from '@heroicons/react/24/outline';

type FieldType = 'string' | 'number' | 'boolean';

interface CustomField {
  key: string;
  type: FieldType;
  value: string | number | boolean;
}

interface CustomFieldsProps {
  fields: Record<string, any>;
  onChange: (fields: Record<string, any>) => void;
}

export default function CustomFields({ fields, onChange }: CustomFieldsProps) {
  const [newFieldKey, setNewFieldKey] = React.useState('');
  const [newFieldType, setNewFieldType] = React.useState<FieldType>('string');

  const customFields = React.useMemo(() => {
    return Object.entries(fields).map(([key, value]) => ({
      key,
      type: typeof value as FieldType,
      value,
    }));
  }, [fields]);

  const handleAddField = () => {
    if (!newFieldKey.trim()) return;

    const defaultValues: Record<FieldType, any> = {
      string: '',
      number: 0,
      boolean: false,
    };

    onChange({
      ...fields,
      [newFieldKey]: defaultValues[newFieldType],
    });

    setNewFieldKey('');
    setNewFieldType('string');
  };

  const handleRemoveField = (key: string) => {
    const newFields = { ...fields };
    delete newFields[key];
    onChange(newFields);
  };

  const handleFieldChange = (field: CustomField, value: string | number | boolean) => {
    onChange({
      ...fields,
      [field.key]: value,
    });
  };

  const renderFieldInput = (field: CustomField) => {
    switch (field.type) {
      case 'boolean':
        return (
          <input
            type="checkbox"
            checked={field.value as boolean}
            onChange={(e) => handleFieldChange(field, e.target.checked)}
            className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-600"
          />
        );
      case 'number':
        return (
          <input
            type="number"
            value={field.value as number}
            onChange={(e) => handleFieldChange(field, parseFloat(e.target.value) || 0)}
            className="block w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-primary-600 sm:text-sm sm:leading-6"
          />
        );
      default:
        return (
          <input
            type="text"
            value={field.value as string}
            onChange={(e) => handleFieldChange(field, e.target.value)}
            className="block w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-primary-600 sm:text-sm sm:leading-6"
          />
        );
    }
  };

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-x-6 gap-y-4 sm:grid-cols-8">
        <div className="sm:col-span-3">
          <input
            type="text"
            placeholder="Field name"
            value={newFieldKey}
            onChange={(e) => setNewFieldKey(e.target.value)}
            className="block w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-primary-600 sm:text-sm sm:leading-6"
          />
        </div>
        <div className="sm:col-span-3">
          <select
            value={newFieldType}
            onChange={(e) => setNewFieldType(e.target.value as FieldType)}
            className="block w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 focus:ring-2 focus:ring-inset focus:ring-primary-600 sm:text-sm sm:leading-6"
          >
            <option value="string">Text</option>
            <option value="number">Number</option>
            <option value="boolean">Yes/No</option>
          </select>
        </div>
        <div className="sm:col-span-2">
          <button
            type="button"
            onClick={handleAddField}
            disabled={!newFieldKey.trim()}
            className="inline-flex items-center rounded-md bg-primary-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-primary-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-600 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <PlusIcon className="h-4 w-4 mr-1" />
            Add Field
          </button>
        </div>
      </div>

      {customFields.length > 0 && (
        <div className="mt-4 space-y-4">
          {customFields.map((field) => (
            <div key={field.key} className="grid grid-cols-1 gap-x-6 gap-y-2 sm:grid-cols-8 items-center">
              <div className="sm:col-span-3">
                <label className="block text-sm font-medium text-gray-700">{field.key}</label>
              </div>
              <div className="sm:col-span-4">{renderFieldInput(field)}</div>
              <div className="sm:col-span-1">
                <button
                  type="button"
                  onClick={() => handleRemoveField(field.key)}
                  className="inline-flex items-center rounded-md text-gray-400 hover:text-gray-500"
                >
                  <XMarkIcon className="h-5 w-5" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
