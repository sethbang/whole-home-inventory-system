import { lazy, Suspense, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Controller, useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation, useQuery } from '@tanstack/react-query';
import { CameraIcon, QrCodeIcon } from '@heroicons/react/24/outline';

import CustomFields from '../components/CustomFields';
import { SectionErrorBoundary } from '../components/ErrorBoundary';
import PriceEstimateCard from '../components/PriceEstimateCard';
import VisionIdentifyButton from '../components/VisionIdentifyButton';
import VisionSuggestionPanel from '../components/VisionSuggestionPanel';
import { useDevMode } from '../contexts/useDevMode';
import { items, images } from '../api/client';
import { apiErrorMessage } from '../api/errors';
import { isJobReference, useJobPoll } from '../api/jobs';
import { pricing } from '../api/pricing';
import { queryKeys } from '../api/queryKeys';
import type {
  PriceEstimateEnvelope,
  VisionResult,
  VisionSuggestion,
} from '../api/types';
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
  const [visionResult, setVisionResult] = useState<VisionResult | null>(null);
  // Track which form fields were populated by vision so we can render
  // "AI" chips until the user edits them. The set is keyed by the
  // RHF field name (not the vision suggestion key) — same string on
  // both sides thanks to the 1:1 mapping in the accept handler.
  const [aiFields, setAiFields] = useState<Set<string>>(() => new Set());
  // Vision → pricing chain. After the user applies suggestions we
  // fire a metadata-based pricing lookup so the "current value"
  // input gets a suggested value too.
  const [priceEnvelope, setPriceEnvelope] =
    useState<PriceEstimateEnvelope | null>(null);
  const [priceJobId, setPriceJobId] = useState<string | null>(null);

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
    watch,
    formState: { errors, isSubmitting },
  } = useForm<AddItemFormValues, unknown, AddItemSubmitValues>({
    resolver: zodResolver(addItemSchema),
    defaultValues: addItemDefaults,
  });

  // Clear the "AI" chip on any field the user manually edits —
  // keeps the badge honest. ``watch(callback)`` fires once per
  // user-initiated change without re-rendering.
  useEffect(() => {
    const subscription = watch((_, { name, type }) => {
      if (type !== 'change' || !name) return;
      setAiFields((prev) => {
        if (!prev.has(name)) return prev;
        const next = new Set(prev);
        next.delete(name);
        return next;
      });
    });
    return () => subscription.unsubscribe();
  }, [watch]);

  const uploadImageMutation = useMutation({
    mutationFn: async ({ itemId, file }: { itemId: string; file: File }) =>
      images.upload(itemId, file),
  });

  // v3.1: pricing chain. Triggered from the vision "Apply selected"
  // handler with the just-applied metadata — no item yet, so we
  // send metadata (not item_id).
  const estimatePriceFromMetadata = useMutation({
    mutationFn: (metadata: Record<string, unknown>) =>
      pricing.estimate({ metadata }),
    onSuccess: (response) => {
      if (isJobReference(response)) {
        setPriceJobId(response.job_id);
        return;
      }
      setPriceEnvelope(response as PriceEstimateEnvelope);
    },
  });

  const priceJob = useJobPoll(priceJobId);
  useEffect(() => {
    if (!priceJobId || !priceJob.data) return;
    const { status, result } = priceJob.data;
    if (status === 'complete' && result) {
      setPriceJobId(null);
      setPriceEnvelope(result as unknown as PriceEstimateEnvelope);
    } else if (status === 'failed' || status === 'not_found') {
      setPriceJobId(null);
    }
  }, [priceJob.data, priceJobId]);

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
          <h2 className="text-2xl font-bold leading-7 text-fg sm:truncate sm:text-3xl sm:tracking-tight">
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
              className="ml-3 inline-flex items-center rounded-md bg-primary px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-primary-accent focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
            >
              Quick Add (Dev)
            </button>
          )}
        </div>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="mt-8 space-y-8" noValidate>
        {serverError && (
          <div role="alert" className="rounded-md bg-danger-subtle p-4">
            <div className="text-sm text-danger">{serverError}</div>
          </div>
        )}

        <div className="space-y-8 divide-y divide-line">
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
              <input
                id="category"
                type="text"
                aria-invalid={errors.category ? 'true' : 'false'}
                {...register('category')}
                className="mt-1 block w-full rounded-md border-line-strong shadow-sm focus:border-primary focus:ring-primary sm:text-sm"
                placeholder="Enter a category"
              />
              {errors.category && (
                <p className="mt-2 text-sm text-danger">{errors.category.message}</p>
              )}
            </div>

            <div className="sm:col-span-3">
              <label htmlFor="location" className="block text-sm font-medium text-muted">
                Location
              </label>
              <input
                id="location"
                type="text"
                aria-invalid={errors.location ? 'true' : 'false'}
                {...register('location')}
                className="mt-1 block w-full rounded-md border-line-strong shadow-sm focus:border-primary focus:ring-primary sm:text-sm"
                placeholder="Enter a location"
              />
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
                  Images
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
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={() => setShowScanner(true)}
                      className="inline-flex items-center px-3 py-2 border border-line-strong shadow-sm text-sm font-medium rounded-md text-muted bg-surface-raised hover:bg-surface-muted focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary"
                    >
                      <CameraIcon className="h-5 w-5 mr-2" />
                      Camera
                    </button>
                    <button
                      type="button"
                      onClick={() => setShowScanner(true)}
                      className="inline-flex items-center px-3 py-2 border border-line-strong shadow-sm text-sm font-medium rounded-md text-muted bg-surface-raised hover:bg-surface-muted focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary"
                    >
                      <QrCodeIcon className="h-5 w-5 mr-2" />
                      Scan Barcode
                    </button>
                    <SectionErrorBoundary label="vision identify">
                      <VisionIdentifyButton
                        onResult={setVisionResult}
                        maxFiles={4}
                      />
                    </SectionErrorBoundary>
                  </div>
                </div>
              </div>

              {visionResult && (
                <SectionErrorBoundary
                  label="vision suggestion panel"
                  resetKey={visionResult.queried_at}
                >
                  <div className="mt-4">
                    <VisionSuggestionPanel
                    suggestion={visionResult.suggestion}
                    provider={visionResult.provider}
                    model={visionResult.model}
                    onApply={(accepted: Partial<VisionSuggestion>) => {
                      // Map vision fields onto form fields. Only keys
                      // that line up exactly get applied; the rest
                      // (suggested_tags, item_specifics) land in
                      // custom_fields.user_defined in a later
                      // iteration.
                      const touched = new Set<string>(aiFields);
                      const apply = (formField: string, value: unknown) => {
                        if (value === null || value === undefined || value === '') return;
                        setValue(formField as keyof AddItemFormValues, value as never);
                        touched.add(formField);
                      };
                      apply('name', accepted.name);
                      apply('brand', accepted.brand);
                      apply('model_number', accepted.model_number);
                      apply('category', accepted.category);
                      apply('serial_number', accepted.serial_number);
                      apply('notes', accepted.description);
                      setAiFields(touched);
                      setVisionResult(null);
                      // Chain into pricing. If the accepted payload
                      // doesn't have enough identity (brand +
                      // model_number), skip — pricing needs them.
                      if (accepted.brand && accepted.model_number) {
                        estimatePriceFromMetadata.mutate({
                          brand: accepted.brand,
                          model_number: accepted.model_number,
                          name: accepted.name ?? undefined,
                          condition: accepted.condition ?? undefined,
                          year: accepted.year ?? undefined,
                        });
                      }
                    }}
                      onDismiss={() => setVisionResult(null)}
                    />
                  </div>
                </SectionErrorBoundary>
              )}

              {aiFields.size > 0 && (
                <div
                  className="mt-3 flex flex-wrap items-center gap-2 rounded-md bg-primary-subtle px-3 py-2 text-xs text-primary"
                  role="status"
                  aria-live="polite"
                >
                  <span className="font-semibold">AI filled:</span>
                  {Array.from(aiFields).map((field) => (
                    <span
                      key={field}
                      className="rounded bg-primary px-1.5 py-0.5 text-white"
                    >
                      {field}
                    </span>
                  ))}
                  <span className="text-[11px] text-primary">
                    (chips clear as you edit each field)
                  </span>
                </div>
              )}

              {(estimatePriceFromMetadata.isPending || priceJobId) && !priceEnvelope && (
                <p className="mt-3 text-xs text-muted">
                  Looking up resale value from vision metadata…
                </p>
              )}

              {priceEnvelope && (
                <div className="mt-4">
                  <PriceEstimateCard
                    envelope={priceEnvelope}
                    refreshing={
                      estimatePriceFromMetadata.isPending || priceJobId !== null
                    }
                    onApplyMedian={(median) => {
                      setValue('current_value', String(median.toFixed(2)));
                      setAiFields((prev) => {
                        const next = new Set(prev);
                        next.add('current_value');
                        return next;
                      });
                    }}
                  />
                </div>
              )}

              {scanningStatus && (
                <div className="mt-2 rounded-md bg-primary-subtle p-4">
                  <div className="text-sm text-primary">{scanningStatus}</div>
                </div>
              )}

              {showScanner && (
                <Suspense
                  fallback={
                    <div className="mt-2 text-sm text-subtle">
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
