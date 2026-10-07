import { useQuery } from '@tanstack/react-query';
import { analytics } from '../api/client';
import { queryKeys } from '../api/queryKeys';
import type { ValueByCategory, ValueByLocation, WarrantyItem } from '../api/client';
import { ChartBarIcon, MapPinIcon, ClockIcon, CurrencyDollarIcon } from '@heroicons/react/24/outline';

export default function Reports() {
  const { data: categoryData } = useQuery({
    queryKey: queryKeys.analytics.valueByCategory(),
    queryFn: analytics.getValueByCategory,
  });

  const { data: locationData } = useQuery({
    queryKey: queryKeys.analytics.valueByLocation(),
    queryFn: analytics.getValueByLocation,
  });

  const { data: trendsData } = useQuery({
    queryKey: queryKeys.analytics.valueTrends(),
    queryFn: analytics.getValueTrends,
  });

  const { data: warrantyData } = useQuery({
    queryKey: queryKeys.analytics.warrantyStatus(),
    queryFn: analytics.getWarrantyStatus,
  });

  const { data: ageData } = useQuery({
    queryKey: queryKeys.analytics.ageAnalysis(),
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
          <h1 className="text-2xl font-semibold text-fg">Inventory Reports</h1>
          <p className="mt-2 text-sm text-muted">
            Detailed analytics and insights about your inventory items.
          </p>
        </div>
      </div>

      {/* Value Trends */}
      <div className="mt-8 bg-surface-raised shadow-sm ring-1 ring-overlay/5 sm:rounded-xl">
        <div className="px-4 py-6 sm:p-8">
          <h2 className="text-lg font-semibold text-fg mb-4">
            <CurrencyDollarIcon className="inline-block h-6 w-6 mr-2" />
            Value Trends
          </h2>
          {trendsData && (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <div className="bg-primary-subtle p-4 rounded-lg">
                <p className="text-sm text-subtle">Total Purchase Value</p>
                <p className="text-2xl font-semibold text-primary">
                  {formatCurrency(trendsData.total_purchase_value)}
                </p>
              </div>
              <div className="bg-primary-subtle p-4 rounded-lg">
                <p className="text-sm text-subtle">Current Total Value</p>
                <p className="text-2xl font-semibold text-primary">
                  {formatCurrency(trendsData.total_current_value)}
                </p>
              </div>
              <div className="bg-primary-subtle p-4 rounded-lg">
                <p className="text-sm text-subtle">Value Change</p>
                <p className={`text-2xl font-semibold ${trendsData.value_change >= 0 ? 'text-success' : 'text-danger'}`}>
                  {formatCurrency(trendsData.value_change)}
                </p>
              </div>
              <div className="bg-primary-subtle p-4 rounded-lg">
                <p className="text-sm text-subtle">Change Percentage</p>
                <p className={`text-2xl font-semibold ${trendsData.value_change_percentage >= 0 ? 'text-success' : 'text-danger'}`}>
                  {trendsData.value_change_percentage.toFixed(1)}%
                </p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Value by Category */}
      <div className="mt-8 bg-surface-raised shadow-sm ring-1 ring-overlay/5 sm:rounded-xl">
        <div className="px-4 py-6 sm:p-8">
          <h2 className="text-lg font-semibold text-fg mb-4">
            <ChartBarIcon className="inline-block h-6 w-6 mr-2" />
            Value by Category
          </h2>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-line-strong">
              <thead>
                <tr>
                  <th className="py-3.5 pl-4 pr-3 text-left text-sm font-semibold text-fg">Category</th>
                  <th className="px-3 py-3.5 text-right text-sm font-semibold text-fg">Items</th>
                  <th className="px-3 py-3.5 text-right text-sm font-semibold text-fg">Total Value</th>
                  <th className="px-3 py-3.5 text-right text-sm font-semibold text-fg">Average Value</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {categoryData?.map((category: ValueByCategory) => (
                  <tr key={category.category}>
                    <td className="whitespace-nowrap py-4 pl-4 pr-3 text-sm font-medium text-fg">
                      {category.category}
                    </td>
                    <td className="whitespace-nowrap px-3 py-4 text-right text-sm text-subtle">
                      {category.item_count}
                    </td>
                    <td className="whitespace-nowrap px-3 py-4 text-right text-sm text-subtle">
                      {formatCurrency(category.total_value)}
                    </td>
                    <td className="whitespace-nowrap px-3 py-4 text-right text-sm text-subtle">
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
      <div className="mt-8 bg-surface-raised shadow-sm ring-1 ring-overlay/5 sm:rounded-xl">
        <div className="px-4 py-6 sm:p-8">
          <h2 className="text-lg font-semibold text-fg mb-4">
            <MapPinIcon className="inline-block h-6 w-6 mr-2" />
            Value by Location
          </h2>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-line-strong">
              <thead>
                <tr>
                  <th className="py-3.5 pl-4 pr-3 text-left text-sm font-semibold text-fg">Location</th>
                  <th className="px-3 py-3.5 text-right text-sm font-semibold text-fg">Items</th>
                  <th className="px-3 py-3.5 text-right text-sm font-semibold text-fg">Total Value</th>
                  <th className="px-3 py-3.5 text-right text-sm font-semibold text-fg">Average Value</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {locationData?.map((location: ValueByLocation) => (
                  <tr key={location.location}>
                    <td className="whitespace-nowrap py-4 pl-4 pr-3 text-sm font-medium text-fg">
                      {location.location}
                    </td>
                    <td className="whitespace-nowrap px-3 py-4 text-right text-sm text-subtle">
                      {location.item_count}
                    </td>
                    <td className="whitespace-nowrap px-3 py-4 text-right text-sm text-subtle">
                      {formatCurrency(location.total_value)}
                    </td>
                    <td className="whitespace-nowrap px-3 py-4 text-right text-sm text-subtle">
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
      <div className="mt-8 bg-surface-raised shadow-sm ring-1 ring-overlay/5 sm:rounded-xl">
        <div className="px-4 py-6 sm:p-8">
          <h2 className="text-lg font-semibold text-fg mb-4">
            <ClockIcon className="inline-block h-6 w-6 mr-2" />
            Warranty Status
          </h2>
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            {/* Expiring Soon */}
            <div>
              <h3 className="text-sm font-medium text-warning mb-2">Expiring Soon</h3>
              <div className="bg-warning-subtle rounded-lg p-4">
                {warrantyData ? (
                  <>
                    {warrantyData.expiring_soon.length > 0 ? (
                      warrantyData.expiring_soon.map((item: WarrantyItem) => (
                        <div key={item.id} className="mb-2 last:mb-0">
                          <p className="text-sm font-medium text-fg">{item.name}</p>
                          <p className="text-xs text-subtle">Expires: {formatDate(item.expiration_date)}</p>
                        </div>
                      ))
                    ) : (
                      <p className="text-sm text-subtle">No warranties expiring soon</p>
                    )}
                  </>
                ) : (
                  <p className="text-sm text-subtle">Loading warranty information...</p>
                )}
              </div>
            </div>

            {/* Expired */}
            <div>
              <h3 className="text-sm font-medium text-danger mb-2">Expired</h3>
              <div className="bg-danger-subtle rounded-lg p-4">
                {warrantyData ? (
                  <>
                    {warrantyData.expired.length > 0 ? (
                      warrantyData.expired.map((item: WarrantyItem) => (
                        <div key={item.id} className="mb-2 last:mb-0">
                          <p className="text-sm font-medium text-fg">{item.name}</p>
                          <p className="text-xs text-subtle">Expired: {formatDate(item.expiration_date)}</p>
                        </div>
                      ))
                    ) : (
                      <p className="text-sm text-subtle">No expired warranties</p>
                    )}
                  </>
                ) : (
                  <p className="text-sm text-subtle">Loading warranty information...</p>
                )}
              </div>
            </div>

            {/* Active */}
            <div>
              <h3 className="text-sm font-medium text-success mb-2">Active</h3>
              <div className="bg-success-subtle rounded-lg p-4">
                {warrantyData ? (
                  <>
                    {warrantyData.active.length > 0 ? (
                      warrantyData.active.map((item: WarrantyItem) => (
                        <div key={item.id} className="mb-2 last:mb-0">
                          <p className="text-sm font-medium text-fg">{item.name}</p>
                          <p className="text-xs text-subtle">Valid until: {formatDate(item.expiration_date)}</p>
                        </div>
                      ))
                    ) : (
                      <p className="text-sm text-subtle">No active warranties</p>
                    )}
                  </>
                ) : (
                  <p className="text-sm text-subtle">Loading warranty information...</p>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Age Analysis */}
      <div className="mt-8 bg-surface-raised shadow-sm ring-1 ring-overlay/5 sm:rounded-xl">
        <div className="px-4 py-6 sm:p-8">
          <h2 className="text-lg font-semibold text-fg mb-4">Age Analysis</h2>
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-4">
            {ageData && Object.entries(ageData).map(([range, data]) => (
              <div key={range} className="bg-surface-muted rounded-lg p-4">
                <h3 className="text-sm font-medium text-fg mb-2">{range}</h3>
                <div className="space-y-2">
                  <p className="text-sm text-subtle">
                    Items: <span className="font-medium text-fg">{data.count}</span>
                  </p>
                  <p className="text-sm text-subtle">
                    Total Value: <span className="font-medium text-fg">{formatCurrency(data.total_value)}</span>
                  </p>
                  <p className="text-sm text-subtle">
                    Average Value:{' '}
                    <span className="font-medium text-fg">
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