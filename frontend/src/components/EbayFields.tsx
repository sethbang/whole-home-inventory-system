import React from 'react';

export interface EbayFieldsData {
  category_id?: string;
  condition?: 'NEW' | 'LIKE_NEW' | 'VERY_GOOD' | 'GOOD' | 'ACCEPTABLE' | 'FOR_PARTS';
  listing_format?: 'FIXED_PRICE' | 'AUCTION';
  duration?: 'DAYS_3' | 'DAYS_5' | 'DAYS_7' | 'DAYS_10' | 'DAYS_30' | 'GTC';
  shipping_service?: 'USPS_FIRST_CLASS' | 'USPS_PRIORITY' | 'USPS_GROUND' | 'UPS_GROUND' | 'FEDEX_GROUND' | 'FREIGHT' | 'LOCAL_PICKUP';
  shipping_cost?: number;
  returns_accepted?: boolean;
  return_period?: 'DAYS_30' | 'DAYS_60' | 'NO_RETURNS';
  payment_methods?: Array<'PAYPAL' | 'CREDIT_CARD' | 'BANK_TRANSFER'>;
  starting_price?: number;
  reserve_price?: number;
  buy_it_now_price?: number;
  quantity?: number;
  domestic_shipping_only?: boolean;
  item_specifics?: Record<string, string>;
}

interface EbayFieldsProps {
  fields: EbayFieldsData;
  onChange: (fields: EbayFieldsData) => void;
  onCategoryLookup?: () => void;
}

const CONDITIONS = [
  { value: 'NEW', label: 'New' },
  { value: 'LIKE_NEW', label: 'Like New' },
  { value: 'VERY_GOOD', label: 'Very Good' },
  { value: 'GOOD', label: 'Good' },
  { value: 'ACCEPTABLE', label: 'Acceptable' },
  { value: 'FOR_PARTS', label: 'For Parts' },
];

const LISTING_FORMATS = [
  { value: 'FIXED_PRICE', label: 'Fixed Price' },
  { value: 'AUCTION', label: 'Auction' },
];

const DURATIONS = [
  { value: 'DAYS_3', label: '3 Days' },
  { value: 'DAYS_5', label: '5 Days' },
  { value: 'DAYS_7', label: '7 Days' },
  { value: 'DAYS_10', label: '10 Days' },
  { value: 'DAYS_30', label: '30 Days' },
  { value: 'GTC', label: 'Good Till Cancelled' },
];

const SHIPPING_SERVICES = [
  { value: 'USPS_FIRST_CLASS', label: 'USPS First Class' },
  { value: 'USPS_PRIORITY', label: 'USPS Priority' },
  { value: 'USPS_GROUND', label: 'USPS Ground' },
  { value: 'UPS_GROUND', label: 'UPS Ground' },
  { value: 'FEDEX_GROUND', label: 'FedEx Ground' },
  { value: 'FREIGHT', label: 'Freight' },
  { value: 'LOCAL_PICKUP', label: 'Local Pickup' },
];

const RETURN_PERIODS = [
  { value: 'DAYS_30', label: '30 Days' },
  { value: 'DAYS_60', label: '60 Days' },
  { value: 'NO_RETURNS', label: 'No Returns' },
];

const PAYMENT_METHODS = [
  { value: 'PAYPAL', label: 'PayPal' },
  { value: 'CREDIT_CARD', label: 'Credit Card' },
  { value: 'BANK_TRANSFER', label: 'Bank Transfer' },
];

export default function EbayFields({ fields, onChange, onCategoryLookup }: EbayFieldsProps) {
  const updateField = (field: keyof EbayFieldsData, value: any) => {
    onChange({ ...fields, [field]: value });
  };

  const isAuction = fields.listing_format === 'AUCTION';

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-y-6 sm:grid-cols-6 sm:gap-x-6">
        {/* Category */}
        <div className="sm:col-span-3">
          <label htmlFor="category_id" className="block text-sm font-medium text-gray-700">
            Category
          </label>
          <div className="mt-1 flex items-center gap-2">
            <input
              type="text"
              id="category_id"
              value={fields.category_id || ''}
              onChange={(e) => updateField('category_id', e.target.value)}
              className="block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
              placeholder="eBay Category ID"
            />
            {onCategoryLookup && (
              <button
                type="button"
                onClick={onCategoryLookup}
                className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
              >
                Look Up
              </button>
            )}
          </div>
        </div>

        {/* Listing Format */}
        <div className="sm:col-span-3">
          <label htmlFor="listing_format" className="block text-sm font-medium text-gray-700">
            Listing Format
          </label>
          <select
            id="listing_format"
            value={fields.listing_format || ''}
            onChange={(e) => updateField('listing_format', e.target.value)}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
          >
            <option value="">Select Format</option>
            {LISTING_FORMATS.map(({ value, label }) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </div>

        {/* Condition */}
        <div className="sm:col-span-3">
          <label htmlFor="condition" className="block text-sm font-medium text-gray-700">
            Condition
          </label>
          <select
            id="condition"
            value={fields.condition || ''}
            onChange={(e) => updateField('condition', e.target.value)}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
          >
            <option value="">Select Condition</option>
            {CONDITIONS.map(({ value, label }) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </div>

        {/* Duration */}
        <div className="sm:col-span-3">
          <label htmlFor="duration" className="block text-sm font-medium text-gray-700">
            Duration
          </label>
          <select
            id="duration"
            value={fields.duration || ''}
            onChange={(e) => updateField('duration', e.target.value)}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
          >
            <option value="">Select Duration</option>
            {DURATIONS.map(({ value, label }) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </div>

        {/* Quantity */}
        <div className="sm:col-span-3">
          <label htmlFor="quantity" className="block text-sm font-medium text-gray-700">
            Quantity
          </label>
          <input
            type="number"
            id="quantity"
            min="1"
            value={fields.quantity || '1'}
            onChange={(e) => updateField('quantity', parseInt(e.target.value))}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
          />
        </div>

        {/* Price Fields */}
        {isAuction ? (
          <>
            <div className="sm:col-span-3">
              <label htmlFor="starting_price" className="block text-sm font-medium text-gray-700">
                Starting Price
              </label>
              <div className="mt-1 relative rounded-md shadow-sm">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <span className="text-gray-500 sm:text-sm">$</span>
                </div>
                <input
                  type="number"
                  id="starting_price"
                  step="0.01"
                  min="0"
                  value={fields.starting_price || ''}
                  onChange={(e) => updateField('starting_price', parseFloat(e.target.value))}
                  className="mt-1 block w-full pl-7 rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
                />
              </div>
            </div>

            <div className="sm:col-span-3">
              <label htmlFor="reserve_price" className="block text-sm font-medium text-gray-700">
                Reserve Price
              </label>
              <div className="mt-1 relative rounded-md shadow-sm">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <span className="text-gray-500 sm:text-sm">$</span>
                </div>
                <input
                  type="number"
                  id="reserve_price"
                  step="0.01"
                  min="0"
                  value={fields.reserve_price || ''}
                  onChange={(e) => updateField('reserve_price', parseFloat(e.target.value))}
                  className="mt-1 block w-full pl-7 rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
                />
              </div>
            </div>
          </>
        ) : (
          <div className="sm:col-span-3">
            <label htmlFor="buy_it_now_price" className="block text-sm font-medium text-gray-700">
              Buy It Now Price
            </label>
            <div className="mt-1 relative rounded-md shadow-sm">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <span className="text-gray-500 sm:text-sm">$</span>
              </div>
              <input
                type="number"
                id="buy_it_now_price"
                step="0.01"
                min="0"
                value={fields.buy_it_now_price || ''}
                onChange={(e) => updateField('buy_it_now_price', parseFloat(e.target.value))}
                className="mt-1 block w-full pl-7 rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
              />
            </div>
          </div>
        )}

        {/* Shipping Service */}
        <div className="sm:col-span-3">
          <label htmlFor="shipping_service" className="block text-sm font-medium text-gray-700">
            Shipping Service
          </label>
          <select
            id="shipping_service"
            value={fields.shipping_service || ''}
            onChange={(e) => updateField('shipping_service', e.target.value)}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
          >
            <option value="">Select Shipping Service</option>
            {SHIPPING_SERVICES.map(({ value, label }) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </div>

        {/* Shipping Cost */}
        <div className="sm:col-span-3">
          <label htmlFor="shipping_cost" className="block text-sm font-medium text-gray-700">
            Shipping Cost
          </label>
          <div className="mt-1 relative rounded-md shadow-sm">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <span className="text-gray-500 sm:text-sm">$</span>
            </div>
            <input
              type="number"
              id="shipping_cost"
              step="0.01"
              min="0"
              value={fields.shipping_cost || ''}
              onChange={(e) => updateField('shipping_cost', parseFloat(e.target.value))}
              className="mt-1 block w-full pl-7 rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
            />
          </div>
        </div>

        {/* Returns */}
        <div className="sm:col-span-3">
          <div className="flex items-center">
            <input
              type="checkbox"
              id="returns_accepted"
              checked={fields.returns_accepted || false}
              onChange={(e) => updateField('returns_accepted', e.target.checked)}
              className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
            />
            <label htmlFor="returns_accepted" className="ml-2 block text-sm font-medium text-gray-700">
              Accept Returns
            </label>
          </div>
        </div>

        {fields.returns_accepted && (
          <div className="sm:col-span-3">
            <label htmlFor="return_period" className="block text-sm font-medium text-gray-700">
              Return Period
            </label>
            <select
              id="return_period"
              value={fields.return_period || ''}
              onChange={(e) => updateField('return_period', e.target.value)}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
            >
              <option value="">Select Return Period</option>
              {RETURN_PERIODS.map(({ value, label }) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </div>
        )}

        {/* Payment Methods */}
        <div className="sm:col-span-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Payment Methods
          </label>
          <div className="space-y-2">
            {PAYMENT_METHODS.map(({ value, label }) => (
              <div key={value} className="flex items-center">
                <input
                  type="checkbox"
                  id={`payment_${value}`}
                  checked={(fields.payment_methods || []).includes(value as any)}
                  onChange={(e) => {
                    const methods = fields.payment_methods || [];
                    if (e.target.checked) {
                      updateField('payment_methods', [...methods, value]);
                    } else {
                      updateField('payment_methods', methods.filter(m => m !== value));
                    }
                  }}
                  className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                />
                <label htmlFor={`payment_${value}`} className="ml-2 block text-sm text-gray-700">
                  {label}
                </label>
              </div>
            ))}
          </div>
        </div>

        {/* Domestic Shipping Only */}
        <div className="sm:col-span-6">
          <div className="flex items-center">
            <input
              type="checkbox"
              id="domestic_shipping_only"
              checked={fields.domestic_shipping_only || false}
              onChange={(e) => updateField('domestic_shipping_only', e.target.checked)}
              className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
            />
            <label htmlFor="domestic_shipping_only" className="ml-2 block text-sm font-medium text-gray-700">
              Domestic Shipping Only
            </label>
          </div>
        </div>
      </div>
    </div>
  );
}