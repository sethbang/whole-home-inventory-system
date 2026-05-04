import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Controller, useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Tab } from '@headlessui/react';
import { format } from 'date-fns';
import { CameraIcon } from '@heroicons/react/24/outline';

import CustomFields from '../components/CustomFields';
import CameraCapture from '../components/CameraCapture';
import ImageGallery from '../components/ImageGallery';
import EbayFields, { EbayFieldsData } from '../components/EbayFields';
import FacebookFields from '../components/FacebookFields';
import FacebookCopyPasteDialog from '../components/FacebookCopyPasteDialog';
import PriceEstimateCard from '../components/PriceEstimateCard';
import { items, images, ebay, facebook } from '../api/client';
import { apiErrorMessage } from '../api/errors';
import { isJobReference, useJobPoll } from '../api/jobs';
import { pricing } from '../api/pricing';
import { queryKeys } from '../api/queryKeys';
import type { EbayCategoryResponse } from '../api/client';
import type { FbFieldsData, PriceEstimateEnvelope } from '../api/types';
import {
  type AddItemFormValues,
  type AddItemSubmitValues,
  addItemDefaults,
  addItemSchema,
} from './AddItem.schema';

export default function ItemDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [serverError, setServerError] = useState<string | null>(null);
  const [showCamera, setShowCamera] = useState(false);
  const [priceEnvelope, setPriceEnvelope] =
    useState<PriceEstimateEnvelope | null>(null);
  const [priceJobId, setPriceJobId] = useState<string | null>(null);

  const { data: item, isLoading } = useQuery({
    queryKey: queryKeys.items.detail(id!),
    queryFn: () => items.get(id!),
    enabled: !!id,
  });

  const { data: categories = [] } = useQuery({
    queryKey: queryKeys.items.categories(),
    queryFn: items.getCategories,
  });

  const { data: locations = [] } = useQuery({
    queryKey: queryKeys.items.locations(),
    queryFn: items.getLocations,
  });

  const { data: fbCategoriesData } = useQuery({
    queryKey: queryKeys.facebook.categories(),
    queryFn: facebook.getCategories,
  });
  const fbCategories = fbCategoriesData?.categories ?? [];

  const [showFbDialog, setShowFbDialog] = useState(false);

  // v3.1: pricing estimate + refresh. estimate() respects the cache;
  // refresh() forces a fresh provider round-trip.
  const estimatePrice = useMutation({
    mutationFn: () => pricing.estimate({ item_id: id }),
    onSuccess: (response) => {
      setServerError(null);
      if (isJobReference(response)) {
        setPriceJobId(response.job_id);
      } else {
        setPriceEnvelope(response as PriceEstimateEnvelope);
      }
    },
    onError: (err) => setServerError(apiErrorMessage(err, 'Pricing lookup failed')),
  });

  const refreshPrice = useMutation({
    mutationFn: () => pricing.refresh(id!),
    onSuccess: (response) => {
      setServerError(null);
      if (isJobReference(response)) {
        setPriceJobId(response.job_id);
      } else {
        setPriceEnvelope(response as PriceEstimateEnvelope);
      }
    },
    onError: (err) =>
      setServerError(apiErrorMessage(err, 'Pricing refresh failed')),
  });

  const priceJob = useJobPoll(priceJobId);
  useEffect(() => {
    if (!priceJobId || !priceJob.data) return;
    const { status, result, error } = priceJob.data;
    if (status === 'complete' && result) {
      setPriceJobId(null);
      setPriceEnvelope(result as unknown as PriceEstimateEnvelope);
      // Item pricing columns changed server-side — invalidate the item
      // query so the parent re-fetches and re-renders.
      queryClient.invalidateQueries({ queryKey: queryKeys.items.detail(id!) });
    } else if (status === 'failed' || status === 'not_found') {
      setPriceJobId(null);
      setServerError(error ?? 'Pricing job failed');
    }
  }, [priceJob.data, priceJobId, id, queryClient]);

  const pricingBusy =
    estimatePrice.isPending || refreshPrice.isPending || priceJobId !== null;

  const {
    register,
    handleSubmit,
    control,
    reset,
    watch,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<AddItemFormValues, unknown, AddItemSubmitValues>({
    resolver: zodResolver(addItemSchema),
    defaultValues: addItemDefaults,
  });

  // Populate the form once the item loads. ``reset`` with ``keepDirty: false``
  // so subsequent manual edits aren't flagged until the user changes them.
  useEffect(() => {
    if (!item) return;
    reset({
      name: item.name ?? '',
      category: item.category ?? '',
      location: item.location ?? '',
      brand: item.brand ?? '',
      model_number: item.model_number ?? '',
      serial_number: item.serial_number ?? '',
      barcode: item.barcode ?? '',
      purchase_date: item.purchase_date
        ? format(new Date(item.purchase_date), 'yyyy-MM-dd')
        : '',
      purchase_price: item.purchase_price?.toString() ?? '',
      current_value: item.current_value?.toString() ?? '',
      warranty_expiration: item.warranty_expiration
        ? format(new Date(item.warranty_expiration), 'yyyy-MM-dd')
        : '',
      notes: item.notes ?? '',
      custom_fields: (item.custom_fields ?? {}) as Record<string, unknown>,
    });
  }, [item, reset]);

  const updateItemMutation = useMutation({
    mutationFn: async (values: AddItemSubmitValues) => items.update(id!, values),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.items.detail(id!) });
      navigate('/');
    },
    onError: (err) => {
      setServerError(apiErrorMessage(err, 'Failed to update item'));
    },
  });

  const uploadImageMutation = useMutation({
    mutationFn: async (file: File) => images.upload(id!, file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.items.detail(id!) });
    },
    onError: (err) => {
      setServerError(apiErrorMessage(err, 'Failed to upload image'));
    },
  });

  const deleteImageMutation = useMutation({
    mutationFn: (imageId: string) => images.delete(imageId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.items.detail(id!) });
    },
    onError: (err) => {
      setServerError(apiErrorMessage(err, 'Failed to delete image'));
    },
  });

  const deleteItemMutation = useMutation({
    mutationFn: () => items.delete(id!),
    onSuccess: () => navigate('/'),
    onError: (err) => {
      setServerError(apiErrorMessage(err, 'Failed to delete item'));
    },
  });

  const updateEbayFieldsMutation = useMutation({
    mutationFn: async (fields: EbayFieldsData) => ebay.updateFields(id!, fields),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.items.detail(id!) });
    },
    onError: (err) => {
      setServerError(apiErrorMessage(err, 'Failed to update eBay fields'));
    },
  });

  const updateFbFieldsMutation = useMutation({
    mutationFn: async (fields: FbFieldsData) => facebook.updateFields(id!, fields),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.items.detail(id!) });
    },
    onError: (err) => {
      setServerError(apiErrorMessage(err, 'Failed to update Facebook fields'));
    },
  });

  const lookupEbayCategoryMutation = useMutation({
    mutationFn: async () => ebay.getCategories(id),
    onSuccess: (data: EbayCategoryResponse) => {
      if (data.suggested_category) {
        const current = (watch('custom_fields') ?? {}) as Record<string, unknown>;
        const ebayFields = (current.ebay ?? {}) as Record<string, unknown>;
        setValue('custom_fields', {
          ...current,
          ebay: { ...ebayFields, category_id: data.suggested_category.id },
        });
      }
    },
    onError: (err) => {
      setServerError(apiErrorMessage(err, 'Failed to lookup eBay category'));
    },
  });

  const onSubmit = (values: AddItemSubmitValues) => {
    setServerError(null);
    updateItemMutation.mutate(values);
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files) {
      Array.from(event.target.files).forEach((file) => {
        uploadImageMutation.mutate(file);
      });
      event.target.value = '';
    }
  };

  const handleDeleteImage = async (imageId: string) => {
    if (window.confirm('Are you sure you want to delete this image?')) {
      deleteImageMutation.mutate(imageId);
    }
  };

  const handleDeleteItem = async () => {
    if (
      window.confirm(
        'Are you sure you want to delete this item? This action cannot be undone.',
      )
    ) {
      deleteItemMutation.mutate();
    }
  };

  const handleEbayFieldsChange = (fields: EbayFieldsData) => {
    const current = (watch('custom_fields') ?? {}) as Record<string, unknown>;
    setValue('custom_fields', { ...current, ebay: fields });
    updateEbayFieldsMutation.mutate(fields);
  };

  const handleFbFieldsChange = (fields: FbFieldsData) => {
    const current = (watch('custom_fields') ?? {}) as Record<string, unknown>;
    setValue('custom_fields', { ...current, facebook: fields });
    updateFbFieldsMutation.mutate(fields);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
      </div>
    );
  }

  const customFieldsValue = watch('custom_fields') ?? {};
  const ebayFieldsValue = (customFieldsValue as Record<string, unknown>)
    .ebay as EbayFieldsData | undefined;
  const fbFieldsValue = (customFieldsValue as Record<string, unknown>)
    .facebook as FbFieldsData | undefined;

  return (
    <div>
      <div className="md:flex md:items-center md:justify-between">
        <div className="min-w-0 flex-1">
          <h2 className="text-2xl font-bold leading-7 text-fg sm:truncate sm:text-3xl sm:tracking-tight">
            Edit Item: {item?.name}
          </h2>
        </div>
        <div className="mt-4 flex md:ml-4 md:mt-0">
          <button
            type="button"
            onClick={handleDeleteItem}
            className="ml-3 inline-flex items-center rounded-md bg-danger px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-danger"
          >
            Delete Item
          </button>
        </div>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="mt-8 space-y-8" noValidate>
        {serverError && (
          <div role="alert" className="rounded-md bg-danger-subtle p-4">
            <div className="text-sm text-danger">{serverError}</div>
          </div>
        )}

        <div className="space-y-8 divide-y divide-line">
          {item?.images && item.images.length > 0 && (
            <div className="pt-8">
              <h3 className="text-lg font-medium leading-6 text-fg">
                Current Images
              </h3>
              <div className="mt-4">
                <ImageGallery images={item.images} onDelete={handleDeleteImage} />
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 gap-y-6 sm:grid-cols-6 sm:gap-x-6">
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
              {errors.category && (
                <p className="mt-2 text-sm text-danger">{errors.category.message}</p>
              )}
            </div>

            <div className="sm:col-span-3">
              <label htmlFor="location" className="block text-sm font-medium text-muted">
                Location
              </label>
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
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  onClick={() => estimatePrice.mutate()}
                  disabled={pricingBusy}
                  className="inline-flex items-center gap-2 rounded-md border border-primary bg-primary-subtle px-3 py-1 text-xs font-medium text-primary hover:bg-primary-subtle-hover disabled:opacity-60"
                >
                  {pricingBusy ? 'Checking…' : 'Estimate value with AI'}
                </button>
              </div>
              {priceEnvelope && (
                <div className="mt-3">
                  <PriceEstimateCard
                    envelope={priceEnvelope}
                    refreshing={refreshPrice.isPending || priceJobId !== null}
                    onRefresh={() => refreshPrice.mutate()}
                    onApplyMedian={(median) => {
                      setValue('current_value', String(median.toFixed(2)));
                    }}
                  />
                </div>
              )}
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

            <div className="sm:col-span-6">
              <div>
                <label htmlFor="images" className="block text-sm font-medium text-muted">
                  Add Images
                </label>
                <div className="mt-1 flex items-center gap-4">
                  <input
                    type="file"
                    id="images"
                    multiple
                    accept="image/*"
                    onChange={handleFileChange}
                    className="block w-full text-sm text-subtle file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-primary-subtle file:text-primary-hover hover:file:bg-primary-subtle-hover"
                  />
                  <button
                    type="button"
                    onClick={() => setShowCamera(true)}
                    className="inline-flex items-center px-3 py-2 border border-line-strong shadow-sm text-sm font-medium rounded-md text-muted bg-surface-raised hover:bg-surface-muted focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary sm:hidden"
                  >
                    <CameraIcon className="h-5 w-5" />
                  </button>
                </div>
              </div>

              {showCamera && (
                <CameraCapture
                  onCapture={(file) => {
                    uploadImageMutation.mutate(file);
                    setShowCamera(false);
                  }}
                  onClose={() => setShowCamera(false)}
                />
              )}
            </div>

            <div className="sm:col-span-6 pt-8">
              <h3 className="text-lg font-medium leading-6 text-fg mb-4">
                Marketplace Integrations
              </h3>
              <Tab.Group>
                <Tab.List className="flex gap-2 border-b border-line">
                  {['eBay', 'Facebook Marketplace'].map((label) => (
                    <Tab
                      key={label}
                      className={({ selected }) =>
                        `px-4 py-2 text-sm font-medium border-b-2 focus:outline-none ${
                          selected
                            ? 'border-primary text-primary-hover'
                            : 'border-transparent text-subtle hover:text-muted'
                        }`
                      }
                    >
                      {label}
                    </Tab>
                  ))}
                </Tab.List>
                <Tab.Panels className="mt-6">
                  <Tab.Panel>
                    <EbayFields
                      fields={ebayFieldsValue ?? {}}
                      onChange={handleEbayFieldsChange}
                      onCategoryLookup={() => lookupEbayCategoryMutation.mutate()}
                    />
                  </Tab.Panel>
                  <Tab.Panel>
                    <FacebookFields
                      fields={fbFieldsValue ?? {}}
                      categories={fbCategories}
                      onChange={handleFbFieldsChange}
                    />
                    <div className="mt-4 flex justify-end">
                      <button
                        type="button"
                        onClick={() => setShowFbDialog(true)}
                        className="rounded-md border border-transparent bg-primary px-3 py-1.5 text-sm font-medium text-white shadow-sm hover:bg-primary-hover"
                      >
                        Generate copy-paste block
                      </button>
                    </div>
                  </Tab.Panel>
                </Tab.Panels>
              </Tab.Group>
            </div>
          </div>
        </div>

        {showFbDialog && id && (
          <FacebookCopyPasteDialog
            itemId={id}
            onClose={() => setShowFbDialog(false)}
          />
        )}

        <div className="pt-5">
          <div className="flex justify-end">
            <button
              type="button"
              onClick={() => navigate('/')}
              className="rounded-md border border-line-strong bg-surface-raised py-2 px-4 text-sm font-medium text-muted shadow-sm hover:bg-surface-muted focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="ml-3 inline-flex justify-center rounded-md border border-transparent bg-primary py-2 px-4 text-sm font-medium text-white shadow-sm hover:bg-primary-hover focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 disabled:opacity-60"
            >
              {isSubmitting ? 'Saving...' : 'Save'}
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}
