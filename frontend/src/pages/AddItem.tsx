import { lazy, Suspense, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Controller, useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation, useQuery } from '@tanstack/react-query';
import { CameraIcon, QrCodeIcon } from '@heroicons/react/24/outline';

import CustomFields from '../components/CustomFields';
import { useDevMode } from '../contexts/DevModeContext';
import { items, images } from '../api/client';
import { apiErrorMessage } from '../api/errors';
import { queryKeys } from '../api/queryKeys';
import {
  type AddItemFormValues,
  type AddItemSubmitValues,
  addItemDefaults,
  addItemSchema,
} from './AddItem.schema';

// Lazy-loaded: @zxing/* bundles are ~400 KB gzipped and only needed when
// the user opens the scanner.
const BarcodeScanner = lazy(() => import('../components/BarcodeScanner'));

export default function AddItem() {
  const navigate = useNavigate();
  const { isDevMode } = useDevMode();
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [serverError, setServerError] = useState<string | null>(null);
  const [showScanner, setShowScanner] = useState(false);
  const [scanningStatus, setScanningStatus] = useState<string | null>(null);

  // Warm the autocomplete caches on mount — loader also preloads them but
  // these hooks give React Query a live subscription.
  useQuery({
    queryKey: queryKeys.items.categories(),
    queryFn: items.getCategories,
  });
  useQuery({
    queryKey: queryKeys.items.locations(),
    queryFn: items.getLocations,
  });

  const {
    register,
    handleSubmit,
    setValue,
    control,
    formState: { errors, isSubmitting },
  } = useForm<AddItemFormValues, unknown, AddItemSubmitValues>({
    resolver: zodResolver(addItemSchema),
    defaultValues: addItemDefaults,
  });

  const uploadImageMutation = useMutation({
    mutationFn: async ({ itemId, file }: { itemId: string; file: File }) =>
      images.upload(itemId, file),
  });

  const createItemMutation = useMutation({
    mutationFn: async (params: {
      values: AddItemSubmitValues | Record<string, never>;
      isDev: boolean;
    }) => {
      const { values, isDev } = params;
      const item = await items.create(values, isDev);

      if (selectedFiles.length > 0) {
        try {
          await Promise.all(
            selectedFiles.map((file) =>
              uploadImageMutation.mutateAsync({ itemId: item.id, file }),
            ),
          );
        } catch {
          setServerError(
            'Item was created but some images failed to upload. You can add them later.',
          );
        }
      }
      return item;
    },
    onSuccess: (item) => {
      navigate(`/items/${item.id}`);
    },
    onError: (err) => {
      setServerError(apiErrorMessage(err, 'Failed to create item'));
    },
  });

  const onSubmit = (values: AddItemSubmitValues) => {
    setServerError(null);
    createItemMutation.mutate({ values, isDev: false });
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files) {
      setSelectedFiles(Array.from(event.target.files));
    }
  };

  return (
    <div>
      <div className="md:flex md:items-center md:justify-between">
        <div className="min-w-0 flex-1">
          <h2 className="text-2xl font-bold leading-7 text-gray-900 sm:truncate sm:text-3xl sm:tracking-tight">
            Add New Item
          </h2>
        </div>
        <div className="mt-4 flex md:ml-4 md:mt-0">
          {isDevMode && (
            <button
              type="button"
              onClick={() =>
                createItemMutation.mutate({ values: {}, isDev: true })
              }
              className="ml-3 inline-flex items-center rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600"
            >
              Quick Add (Dev)
            </button>
          )}
        </div>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="mt-8 space-y-8" noValidate>
        {serverError && (
          <div role="alert" className="rounded-md bg-red-50 p-4">
            <div className="text-sm text-red-700">{serverError}</div>
          </div>
        )}

        <div className="space-y-8 divide-y divide-gray-200">
          <div className="grid grid-cols-1 gap-y-6 sm:grid-cols-6 sm:gap-x-6">
            <div className="sm:col-span-4">
              <label htmlFor="name" className="block text-sm font-medium text-gray-700">
                Name
              </label>
              <input
                id="name"
                type="text"
                aria-invalid={errors.name ? 'true' : 'false'}
                {...register('name')}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
              />
              {errors.name && (
                <p className="mt-2 text-sm text-red-600">{errors.name.message}</p>
              )}
            </div>

            <div className="sm:col-span-3">
              <label htmlFor="category" className="block text-sm font-medium text-gray-700">
                Category
              </label>
              <input
                id="category"
                type="text"
                aria-invalid={errors.category ? 'true' : 'false'}
                {...register('category')}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
                placeholder="Enter a category"
              />
              {errors.category && (
                <p className="mt-2 text-sm text-red-600">{errors.category.message}</p>
              )}
            </div>

            <div className="sm:col-span-3">
              <label htmlFor="location" className="block text-sm font-medium text-gray-700">
                Location
              </label>
              <input
                id="location"
                type="text"
                aria-invalid={errors.location ? 'true' : 'false'}
                {...register('location')}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
                placeholder="Enter a location"
              />
              {errors.location && (
                <p className="mt-2 text-sm text-red-600">{errors.location.message}</p>
              )}
            </div>

            <div className="sm:col-span-3">
              <label htmlFor="brand" className="block text-sm font-medium text-gray-700">
                Brand
              </label>
              <input
                id="brand"
                type="text"
                {...register('brand')}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
              />
            </div>

            <div className="sm:col-span-3">
              <label htmlFor="model_number" className="block text-sm font-medium text-gray-700">
                Model Number
              </label>
              <input
                id="model_number"
                type="text"
                {...register('model_number')}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
              />
            </div>

            <div className="sm:col-span-3">
              <label htmlFor="serial_number" className="block text-sm font-medium text-gray-700">
                Serial Number
              </label>
              <input
                id="serial_number"
                type="text"
                {...register('serial_number')}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
              />
            </div>

            <div className="sm:col-span-3">
              <label htmlFor="barcode" className="block text-sm font-medium text-gray-700">
                Barcode
              </label>
              <input
                id="barcode"
                type="text"
                {...register('barcode')}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
              />
            </div>

            <div className="sm:col-span-3">
              <label htmlFor="purchase_date" className="block text-sm font-medium text-gray-700">
                Purchase Date
              </label>
              <input
                id="purchase_date"
                type="date"
                {...register('purchase_date')}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
              />
            </div>

            <div className="sm:col-span-3">
              <label htmlFor="purchase_price" className="block text-sm font-medium text-gray-700">
                Purchase Price
              </label>
              <div className="mt-1 relative rounded-md shadow-sm">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <span className="text-gray-500 sm:text-sm">$</span>
                </div>
                <input
                  id="purchase_price"
                  type="number"
                  step="0.01"
                  min="0"
                  {...register('purchase_price')}
                  className="mt-1 block w-full pl-7 rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
                />
              </div>
              {errors.purchase_price && (
                <p className="mt-2 text-sm text-red-600">
                  {errors.purchase_price.message}
                </p>
              )}
            </div>

            <div className="sm:col-span-3">
              <label htmlFor="current_value" className="block text-sm font-medium text-gray-700">
                Current Value
              </label>
              <div className="mt-1 relative rounded-md shadow-sm">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <span className="text-gray-500 sm:text-sm">$</span>
                </div>
                <input
                  id="current_value"
                  type="number"
                  step="0.01"
                  min="0"
                  {...register('current_value')}
                  className="mt-1 block w-full pl-7 rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
                />
              </div>
              {errors.current_value && (
                <p className="mt-2 text-sm text-red-600">
                  {errors.current_value.message}
                </p>
              )}
            </div>

            <div className="sm:col-span-3">
              <label htmlFor="warranty_expiration" className="block text-sm font-medium text-gray-700">
                Warranty Expiration
              </label>
              <input
                id="warranty_expiration"
                type="date"
                {...register('warranty_expiration')}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
              />
            </div>

            <div className="sm:col-span-6">
              <label htmlFor="notes" className="block text-sm font-medium text-gray-700">
                Notes
              </label>
              <textarea
                id="notes"
                rows={3}
                {...register('notes')}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
              />
            </div>

            <div className="sm:col-span-6">
              <label className="block text-sm font-medium text-gray-700 mb-4">
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

            <div className="sm:col-span-6">
              <div>
                <label htmlFor="images" className="block text-sm font-medium text-gray-700">
                  Images
                </label>
                <div className="mt-1 flex items-center gap-4">
                  <input
                    type="file"
                    id="images"
                    multiple
                    accept="image/*"
                    onChange={handleFileChange}
                    className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-primary-50 file:text-primary-700 hover:file:bg-primary-100"
                  />
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => setShowScanner(true)}
                      className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
                    >
                      <CameraIcon className="h-5 w-5 mr-2" />
                      Camera
                    </button>
                    <button
                      type="button"
                      onClick={() => setShowScanner(true)}
                      className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
                    >
                      <QrCodeIcon className="h-5 w-5 mr-2" />
                      Scan Barcode
                    </button>
                  </div>
                </div>
              </div>

              {scanningStatus && (
                <div className="mt-2 rounded-md bg-blue-50 p-4">
                  <div className="text-sm text-blue-700">{scanningStatus}</div>
                </div>
              )}

              {showScanner && (
                <Suspense
                  fallback={
                    <div className="mt-2 text-sm text-gray-500">
                      Loading scanner…
                    </div>
                  }
                >
                  <BarcodeScanner
                    onCapture={(file: File) => {
                      setSelectedFiles((prev) => [...prev, file]);
                      setShowScanner(false);
                    }}
                    onBarcodeScan={async (barcode: string) => {
                      setScanningStatus('Looking up barcode...');
                      try {
                        const item = await items.lookupBarcode(barcode);
                        if (item) {
                          setValue('name', item.name ?? '');
                          setValue('brand', item.brand ?? '');
                          setValue('model_number', item.model_number ?? '');
                          setValue('serial_number', item.serial_number ?? '');
                          setValue('barcode', barcode);
                          setScanningStatus('Item found! Form updated.');
                          setShowScanner(false);
                        } else {
                          setValue('barcode', barcode);
                          setScanningStatus(
                            'No item found for this barcode. Please fill in the details manually.',
                          );
                        }
                      } catch (err) {
                        setScanningStatus(
                          apiErrorMessage(
                            err,
                            'Error looking up barcode. Please try again.',
                          ),
                        );
                      }
                    }}
                    onClose={() => {
                      setShowScanner(false);
                      setScanningStatus(null);
                    }}
                  />
                </Suspense>
              )}
            </div>
          </div>
        </div>

        <div className="pt-5">
          <div className="flex justify-end">
            <button
              type="button"
              onClick={() => navigate('/')}
              className="rounded-md border border-gray-300 bg-white py-2 px-4 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="ml-3 inline-flex justify-center rounded-md border border-transparent bg-primary-600 py-2 px-4 text-sm font-medium text-white shadow-sm hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 disabled:opacity-60"
            >
              {isSubmitting ? 'Saving...' : 'Save'}
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}
