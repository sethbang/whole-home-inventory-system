import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { analytics } from '../api/client';
import type { ValueByCategory, ValueByLocation, WarrantyItem } from '../api/client';
import { ChartBarIcon, MapPinIcon, ClockIcon, CurrencyDollarIcon } from '@heroicons/react/24/outline';

export default function Reports() {
  const { data: categoryData } = useQuery({
    queryKey: ['analytics', 'value-by-category'],
    queryFn: analytics.getValueByCategory,
  });

  const { data: locationData } = useQuery({
    queryKey: ['analytics', 'value-by-location'],
    queryFn: analytics.getValueByLocation,
  });

  const { data: trendsData } = useQuery({
    queryKey: ['analytics', 'value-trends'],
    queryFn: analytics.getValueTrends,
  });

  const { data: warrantyData } = useQuery({
    queryKey: ['analytics', 'warranty-status'],
    queryFn: analytics.getWarrantyStatus,
  });

  const { data: ageData } = useQuery({
    queryKey: ['analytics', 'age-analysis'],
    queryFn: analytics.getAgeAnalysis,
  });

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(value);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString();
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="sm:flex sm:items-center">
        <div className="sm:flex-auto">
          <h1 className="text-2xl font-semibold text-gray-900">Inventory Reports</h1>
          <p className="mt-2 text-sm text-gray-700">
            Detailed analytics and insights about your inventory items.
          </p>
        </div>
      </div>

      {/* Value Trends */}
      <div className="mt-8 bg-white shadow-sm ring-1 ring-gray-900/5 sm:rounded-xl">
        <div className="px-4 py-6 sm:p-8">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            <CurrencyDollarIcon className="inline-block h-6 w-6 mr-2" />
            Value Trends
          </h2>
          {trendsData && (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <div className="bg-primary-50 p-4 rounded-lg">
                <p className="text-sm text-gray-500">Total Purchase Value</p>
                <p className="text-2xl font-semibold text-primary-600">
                  {formatCurrency(trendsData.total_purchase_value)}
                </p>
              </div>
              <div className="bg-primary-50 p-4 rounded-lg">
                <p className="text-sm text-gray-500">Current Total Value</p>
                <p className="text-2xl font-semibold text-primary-600">
                  {formatCurrency(trendsData.total_current_value)}
                </p>
              </div>
              <div className="bg-primary-50 p-4 rounded-lg">
                <p className="text-sm text-gray-500">Value Change</p>
                <p className={`text-2xl font-semibold ${trendsData.value_change >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {formatCurrency(trendsData.value_change)}
                </p>
              </div>
              <div className="bg-primary-50 p-4 rounded-lg">
                <p className="text-sm text-gray-500">Change Percentage</p>
                <p className={`text-2xl font-semibold ${trendsData.value_change_percentage >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {trendsData.value_change_percentage.toFixed(1)}%
                </p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Value by Category */}
      <div className="mt-8 bg-white shadow-sm ring-1 ring-gray-900/5 sm:rounded-xl">
        <div className="px-4 py-6 sm:p-8">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            <ChartBarIcon className="inline-block h-6 w-6 mr-2" />
            Value by Category
          </h2>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-300">
              <thead>
                <tr>
                  <th className="py-3.5 pl-4 pr-3 text-left text-sm font-semibold text-gray-900">Category</th>
                  <th className="px-3 py-3.5 text-right text-sm font-semibold text-gray-900">Items</th>
                  <th className="px-3 py-3.5 text-right text-sm font-semibold text-gray-900">Total Value</th>
                  <th className="px-3 py-3.5 text-right text-sm font-semibold text-gray-900">Average Value</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {categoryData?.map((category: ValueByCategory) => (
                  <tr key={category.category}>
                    <td className="whitespace-nowrap py-4 pl-4 pr-3 text-sm font-medium text-gray-900">
                      {category.category}
                    </td>
                    <td className="whitespace-nowrap px-3 py-4 text-right text-sm text-gray-500">
                      {category.item_count}
                    </td>
                    <td className="whitespace-nowrap px-3 py-4 text-right text-sm text-gray-500">
                      {formatCurrency(category.total_value)}
                    </td>
                    <td className="whitespace-nowrap px-3 py-4 text-right text-sm text-gray-500">
                      {formatCurrency(category.total_value / category.item_count)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Value by Location */}
      <div className="mt-8 bg-white shadow-sm ring-1 ring-gray-900/5 sm:rounded-xl">
        <div className="px-4 py-6 sm:p-8">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            <MapPinIcon className="inline-block h-6 w-6 mr-2" />
            Value by Location
          </h2>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-300">
              <thead>
                <tr>
                  <th className="py-3.5 pl-4 pr-3 text-left text-sm font-semibold text-gray-900">Location</th>
                  <th className="px-3 py-3.5 text-right text-sm font-semibold text-gray-900">Items</th>
                  <th className="px-3 py-3.5 text-right text-sm font-semibold text-gray-900">Total Value</th>
                  <th className="px-3 py-3.5 text-right text-sm font-semibold text-gray-900">Average Value</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {locationData?.map((location: ValueByLocation) => (
                  <tr key={location.location}>
                    <td className="whitespace-nowrap py-4 pl-4 pr-3 text-sm font-medium text-gray-900">
                      {location.location}
                    </td>
                    <td className="whitespace-nowrap px-3 py-4 text-right text-sm text-gray-500">
                      {location.item_count}
                    </td>
                    <td className="whitespace-nowrap px-3 py-4 text-right text-sm text-gray-500">
                      {formatCurrency(location.total_value)}
                    </td>
                    <td className="whitespace-nowrap px-3 py-4 text-right text-sm text-gray-500">
                      {formatCurrency(location.total_value / location.item_count)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Warranty Status */}
      <div className="mt-8 bg-white shadow-sm ring-1 ring-gray-900/5 sm:rounded-xl">
        <div className="px-4 py-6 sm:p-8">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            <ClockIcon className="inline-block h-6 w-6 mr-2" />
            Warranty Status
          </h2>
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            {/* Expiring Soon */}
            <div>
              <h3 className="text-sm font-medium text-yellow-600 mb-2">Expiring Soon</h3>
              <div className="bg-yellow-50 rounded-lg p-4">
                {warrantyData?.expiring_soon.map((item: WarrantyItem) => (
                  <div key={item.id} className="mb-2 last:mb-0">
                    <p className="text-sm font-medium text-gray-900">{item.name}</p>
                    <p className="text-xs text-gray-500">Expires: {formatDate(item.expiration_date)}</p>
                  </div>
                ))}
                {warrantyData?.expiring_soon.length === 0 && (
                  <p className="text-sm text-gray-500">No warranties expiring soon</p>
                )}
              </div>
            </div>

            {/* Expired */}
            <div>
              <h3 className="text-sm font-medium text-red-600 mb-2">Expired</h3>
              <div className="bg-red-50 rounded-lg p-4">
                {warrantyData?.expired.map((item: WarrantyItem) => (
                  <div key={item.id} className="mb-2 last:mb-0">
                    <p className="text-sm font-medium text-gray-900">{item.name}</p>
                    <p className="text-xs text-gray-500">Expired: {formatDate(item.expiration_date)}</p>
                  </div>
                ))}
                {warrantyData?.expired.length === 0 && (
                  <p className="text-sm text-gray-500">No expired warranties</p>
                )}
              </div>
            </div>

            {/* Active */}
            <div>
              <h3 className="text-sm font-medium text-green-600 mb-2">Active</h3>
              <div className="bg-green-50 rounded-lg p-4">
                {warrantyData?.active.map((item: WarrantyItem) => (
                  <div key={item.id} className="mb-2 last:mb-0">
                    <p className="text-sm font-medium text-gray-900">{item.name}</p>
                    <p className="text-xs text-gray-500">Valid until: {formatDate(item.expiration_date)}</p>
                  </div>
                ))}
                {warrantyData?.active.length === 0 && (
                  <p className="text-sm text-gray-500">No active warranties</p>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Age Analysis */}
      <div className="mt-8 bg-white shadow-sm ring-1 ring-gray-900/5 sm:rounded-xl">
        <div className="px-4 py-6 sm:p-8">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Age Analysis</h2>
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-4">
            {ageData && Object.entries(ageData).map(([range, data]) => (
              <div key={range} className="bg-gray-50 rounded-lg p-4">
                <h3 className="text-sm font-medium text-gray-900 mb-2">{range}</h3>
                <div className="space-y-2">
                  <p className="text-sm text-gray-500">
                    Items: <span className="font-medium text-gray-900">{data.count}</span>
                  </p>
                  <p className="text-sm text-gray-500">
                    Total Value: <span className="font-medium text-gray-900">{formatCurrency(data.total_value)}</span>
                  </p>
                  <p className="text-sm text-gray-500">
                    Average Value:{' '}
                    <span className="font-medium text-gray-900">
                      {formatCurrency(data.total_value / data.count)}
                    </span>
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}