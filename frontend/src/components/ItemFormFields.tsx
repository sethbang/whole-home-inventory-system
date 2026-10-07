import type { ReactNode } from 'react';
import { Controller } from 'react-hook-form';
import type { Control, FieldErrors, UseFormRegister } from 'react-hook-form';

import CustomFields from './CustomFields';
import type {
  AddItemFormValues,
  AddItemSubmitValues,
} from '../pages/AddItem.schema';

// Both consuming pages declare their form as
// useForm<AddItemFormValues, unknown, AddItemSubmitValues>, so the
// register/control values they hand us carry all three type params.
// Mirror them here exactly so the props line up without a cast.
interface ItemFormFieldsProps {
  register: UseFormRegister<AddItemFormValues>;
  errors: FieldErrors<AddItemFormValues>;
  control: Control<AddItemFormValues, unknown, AddItemSubmitValues>;
  // When provided, the category/location fields render as <select>
  // dropdowns populated from these arrays (ItemDetail — editing an
  // existing item). When undefined, they render as free-text <input>s
  // (AddItem — the user may type a brand-new category/location).
  categories?: string[];
  locations?: string[];
  // Optional extra content rendered inside the Current Value grid cell,
  // directly after the field's error message. ItemDetail uses this slot
  // for its "Estimate value with AI" button + PriceEstimateCard so the
  // pricing UI keeps its exact original placement.
  currentValueExtra?: ReactNode;
}

export default function ItemFormFields({
  register,
  errors,
  control,
  categories,
  locations,
  currentValueExtra,
}: ItemFormFieldsProps) {
  return (
    <>
      <div className="sm:col-span-4">
        <label htmlFor="name" className="block text-sm font-medium text-muted">
          Name
        </label>
        <input
          id="name"
          type="text"
          aria-invalid={errors.name ? 'true' : 'false'}
          {...register('name')}
          className="mt-1 block w-full rounded-md border-line-strong shadow-sm focus:border-primary focus:ring-primary sm:text-sm"
        />
        {errors.name && (
          <p className="mt-2 text-sm text-danger">{errors.name.message}</p>
        )}
      </div>

      <div className="sm:col-span-3">
        <label htmlFor="category" className="block text-sm font-medium text-muted">
          Category
        </label>
        {categories ? (
          <select
            id="category"
            aria-invalid={errors.category ? 'true' : 'false'}
            {...register('category')}
            className="mt-1 block w-full rounded-md border-line-strong shadow-sm focus:border-primary focus:ring-primary sm:text-sm"
          >
            <option value="">Select a category</option>
            {categories.map((category: string) => (
              <option key={category} value={category}>
                {category}
              </option>
            ))}
          </select>
        ) : (
          <input
            id="category"
            type="text"
            aria-invalid={errors.category ? 'true' : 'false'}
            {...register('category')}
            className="mt-1 block w-full rounded-md border-line-strong shadow-sm focus:border-primary focus:ring-primary sm:text-sm"
            placeholder="Enter a category"
          />
        )}
        {errors.category && (
          <p className="mt-2 text-sm text-danger">{errors.category.message}</p>
        )}
      </div>

      <div className="sm:col-span-3">
        <label htmlFor="location" className="block text-sm font-medium text-muted">
          Location
        </label>
        {locations ? (
          <select
            id="location"
            aria-invalid={errors.location ? 'true' : 'false'}
            {...register('location')}
            className="mt-1 block w-full rounded-md border-line-strong shadow-sm focus:border-primary focus:ring-primary sm:text-sm"
          >
            <option value="">Select a location</option>
            {locations.map((location: string) => (
              <option key={location} value={location}>
                {location}
              </option>
            ))}
          </select>
        ) : (
          <input
            id="location"
            type="text"
            aria-invalid={errors.location ? 'true' : 'false'}
            {...register('location')}
            className="mt-1 block w-full rounded-md border-line-strong shadow-sm focus:border-primary focus:ring-primary sm:text-sm"
            placeholder="Enter a location"
          />
        )}
        {errors.location && (
          <p className="mt-2 text-sm text-danger">{errors.location.message}</p>
        )}
      </div>

      <div className="sm:col-span-3">
        <label htmlFor="brand" className="block text-sm font-medium text-muted">
          Brand
        </label>
        <input
          id="brand"
          type="text"
          {...register('brand')}
          className="mt-1 block w-full rounded-md border-line-strong shadow-sm focus:border-primary focus:ring-primary sm:text-sm"
        />
      </div>

      <div className="sm:col-span-3">
        <label htmlFor="model_number" className="block text-sm font-medium text-muted">
          Model Number
        </label>
        <input
          id="model_number"
          type="text"
          {...register('model_number')}
          className="mt-1 block w-full rounded-md border-line-strong shadow-sm focus:border-primary focus:ring-primary sm:text-sm"
        />
      </div>

      <div className="sm:col-span-3">
        <label htmlFor="serial_number" className="block text-sm font-medium text-muted">
          Serial Number
        </label>
        <input
          id="serial_number"
          type="text"
          {...register('serial_number')}
          className="mt-1 block w-full rounded-md border-line-strong shadow-sm focus:border-primary focus:ring-primary sm:text-sm"
        />
      </div>

      <div className="sm:col-span-3">
        <label htmlFor="barcode" className="block text-sm font-medium text-muted">
          Barcode
        </label>
        <input
          id="barcode"
          type="text"
          {...register('barcode')}
          className="mt-1 block w-full rounded-md border-line-strong shadow-sm focus:border-primary focus:ring-primary sm:text-sm"
        />
      </div>

      <div className="sm:col-span-3">
        <label htmlFor="purchase_date" className="block text-sm font-medium text-muted">
          Purchase Date
        </label>
        <input
          id="purchase_date"
          type="date"
          {...register('purchase_date')}
          className="mt-1 block w-full rounded-md border-line-strong shadow-sm focus:border-primary focus:ring-primary sm:text-sm"
        />
      </div>

      <div className="sm:col-span-3">
        <label htmlFor="purchase_price" className="block text-sm font-medium text-muted">
          Purchase Price
        </label>
        <div className="mt-1 relative rounded-md shadow-sm">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <span className="text-subtle sm:text-sm">$</span>
          </div>
          <input
            id="purchase_price"
            type="number"
            step="0.01"
            min="0"
            {...register('purchase_price')}
            className="mt-1 block w-full pl-7 rounded-md border-line-strong shadow-sm focus:border-primary focus:ring-primary sm:text-sm"
          />
        </div>
        {errors.purchase_price && (
          <p className="mt-2 text-sm text-danger">
            {errors.purchase_price.message}
          </p>
        )}
      </div>

      <div className="sm:col-span-3">
        <label htmlFor="current_value" className="block text-sm font-medium text-muted">
          Current Value
        </label>
        <div className="mt-1 relative rounded-md shadow-sm">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <span className="text-subtle sm:text-sm">$</span>
          </div>
          <input
            id="current_value"
            type="number"
            step="0.01"
            min="0"
            {...register('current_value')}
            className="mt-1 block w-full pl-7 rounded-md border-line-strong shadow-sm focus:border-primary focus:ring-primary sm:text-sm"
          />
        </div>
        {errors.current_value && (
          <p className="mt-2 text-sm text-danger">
            {errors.current_value.message}
          </p>
        )}
        {currentValueExtra}
      </div>

      <div className="sm:col-span-3">
        <label htmlFor="warranty_expiration" className="block text-sm font-medium text-muted">
          Warranty Expiration
        </label>
        <input
          id="warranty_expiration"
          type="date"
          {...register('warranty_expiration')}
          className="mt-1 block w-full rounded-md border-line-strong shadow-sm focus:border-primary focus:ring-primary sm:text-sm"
        />
      </div>

      <div className="sm:col-span-6">
        <label htmlFor="notes" className="block text-sm font-medium text-muted">
          Notes
        </label>
        <textarea
          id="notes"
          rows={3}
          {...register('notes')}
          className="mt-1 block w-full rounded-md border-line-strong shadow-sm focus:border-primary focus:ring-primary sm:text-sm"
        />
      </div>

      <div className="sm:col-span-6">
        <label className="block text-sm font-medium text-muted mb-4">
          Custom Fields
        </label>
        <Controller
          control={control}
          name="custom_fields"
          render={({ field }) => (
            <CustomFields
              fields={field.value}
              onChange={(fields) => field.onChange(fields)}
            />
          )}
        />
      </div>
    </>
  );
}
