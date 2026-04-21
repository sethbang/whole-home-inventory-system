/**
 * Controlled component for editing the Facebook Marketplace fields that
 * live under ``item.custom_fields.facebook``. Mirrors the EbayFields
 * component's pattern so both integrations feel consistent in the
 * ItemDetail tabbed panel (task #36).
 */

import type { ChangeEvent } from 'react';

import type { FbCondition, FbFieldsData } from '../types/facebook';

interface FacebookFieldsProps {
  fields: FbFieldsData;
  categories: string[];
  onChange: (fields: FbFieldsData) => void;
}

const CONDITIONS: Array<{ value: FbCondition; label: string }> = [
  { value: 'NEW', label: 'New' },
  { value: 'USED_LIKE_NEW', label: 'Used — Like New' },
  { value: 'USED_GOOD', label: 'Used — Good' },
  { value: 'USED_FAIR', label: 'Used — Fair' },
];

export default function FacebookFields({
  fields,
  categories,
  onChange,
}: FacebookFieldsProps) {
  const handle =
    <K extends keyof FbFieldsData>(key: K) =>
    (event: ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
      const raw = event.target.value;
      const value =
        key === 'price'
          ? raw === ''
            ? undefined
            : Number(raw)
          : raw === ''
            ? undefined
            : raw;
      onChange({ ...fields, [key]: value });
    };

  const handleAvailability = (event: ChangeEvent<HTMLInputElement>) => {
    onChange({
      ...fields,
      availability: event.target.checked ? 'in stock' : 'out of stock',
    });
  };

  return (
    <div className="grid grid-cols-1 gap-y-6 sm:grid-cols-6 sm:gap-x-6">
      <div className="sm:col-span-3">
        <label
          htmlFor="fb-price"
          className="block text-sm font-medium text-gray-700"
        >
          Listing Price (USD)
        </label>
        <div className="mt-1 relative rounded-md shadow-sm">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <span className="text-gray-500 sm:text-sm">$</span>
          </div>
          <input
            id="fb-price"
            type="number"
            step="0.01"
            min="0"
            value={fields.price ?? ''}
            onChange={handle('price')}
            className="mt-1 block w-full pl-7 rounded-md border-gray-300 shadow-sm focus:border-primary focus:ring-primary sm:text-sm"
          />
        </div>
      </div>

      <div className="sm:col-span-3">
        <label
          htmlFor="fb-condition"
          className="block text-sm font-medium text-gray-700"
        >
          Condition
        </label>
        <select
          id="fb-condition"
          value={fields.condition ?? ''}
          onChange={handle('condition')}
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary focus:ring-primary sm:text-sm"
        >
          <option value="">Select condition</option>
          {CONDITIONS.map((c) => (
            <option key={c.value} value={c.value}>
              {c.label}
            </option>
          ))}
        </select>
      </div>

      <div className="sm:col-span-3">
        <label
          htmlFor="fb-category"
          className="block text-sm font-medium text-gray-700"
        >
          Facebook Category
        </label>
        <select
          id="fb-category"
          value={fields.category ?? ''}
          onChange={handle('category')}
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary focus:ring-primary sm:text-sm"
        >
          <option value="">Auto-suggest from item category</option>
          {categories.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
      </div>

      <div className="sm:col-span-3 flex items-end">
        <label className="inline-flex items-center">
          <input
            type="checkbox"
            checked={(fields.availability ?? 'in stock') === 'in stock'}
            onChange={handleAvailability}
            className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
          />
          <span className="ml-2 text-sm text-gray-700">Available (in stock)</span>
        </label>
      </div>

      <div className="sm:col-span-6">
        <label
          htmlFor="fb-description"
          className="block text-sm font-medium text-gray-700"
        >
          Description Override
        </label>
        <textarea
          id="fb-description"
          rows={3}
          value={fields.description_override ?? ''}
          onChange={handle('description_override')}
          placeholder="Leave blank to use the item's notes + brand/model."
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary focus:ring-primary sm:text-sm"
        />
      </div>
    </div>
  );
}
