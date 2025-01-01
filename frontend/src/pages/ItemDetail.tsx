import React, { useState } from 'react';
import CustomFields from '../components/CustomFields';
import CameraCapture from '../components/CameraCapture';
import ImageGallery from '../components/ImageGallery';
import EbayFields, { EbayFieldsData } from '../components/EbayFields';
import { CameraIcon } from '@heroicons/react/24/outline';
import { useNavigate, useParams } from 'react-router-dom';
import { useFormik } from 'formik';
import * as Yup from 'yup';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { items, images, ebay } from '../api/client';
import type { Item, EbayCategoryResponse } from '../api/client';
import { format } from 'date-fns';

const validationSchema = Yup.object({
  name: Yup.string().required('Name is required'),
  category: Yup.string().required('Category is required'),
  location: Yup.string().required('Location is required'),
  brand: Yup.string(),
  model_number: Yup.string(),
  serial_number: Yup.string(),
  purchase_date: Yup.date().nullable(),
  purchase_price: Yup.number().nullable().min(0, 'Price must be positive'),
  current_value: Yup.number().nullable().min(0, 'Value must be positive'),
  warranty_expiration: Yup.date().nullable(),
  notes: Yup.string(),
  custom_fields: Yup.object(),
});

export default function ItemDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [showCamera, setShowCamera] = useState(false);

  const { data: item, isLoading } = useQuery({
    queryKey: ['items', id],
    queryFn: () => items.get(id!),
  });

  const { data: categories = [] } = useQuery({
    queryKey: ['categories'],
    queryFn: items.getCategories,
  });

  const { data: locations = [] } = useQuery({
    queryKey: ['locations'],
    queryFn: items.getLocations,
  });

  const updateItemMutation = useMutation({
    mutationFn: async (values: Partial<Item>) => {
      return await items.update(id!, values);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['items', id] });
      navigate('/');
    },
    onError: (error: any) => {
      setError(error.response?.data?.detail || 'Failed to update item');
    },
  });

  const uploadImageMutation = useMutation({
    mutationFn: async (file: File) => {
      return await images.upload(id!, file);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['items', id] });
      setSelectedFiles([]);
    },
    onError: (error: any) => {
      setError(error.response?.data?.detail || 'Failed to upload image');
    },
  });

  const deleteImageMutation = useMutation({
    mutationFn: (imageId: string) => images.delete(imageId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['items', id] });
    },
    onError: (error: any) => {
      setError(error.response?.data?.detail || 'Failed to delete image');
    },
  });

  const deleteItemMutation = useMutation({
    mutationFn: () => items.delete(id!),
    onSuccess: () => {
      navigate('/');
    },
    onError: (error: any) => {
      setError(error.response?.data?.detail || 'Failed to delete item');
    },
  });

  const updateEbayFieldsMutation = useMutation({
    mutationFn: async (fields: EbayFieldsData) => {
      return await ebay.updateFields(id!, fields);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['items', id] });
    },
    onError: (error: any) => {
      setError(error.response?.data?.detail || 'Failed to update eBay fields');
    },
  });

  const lookupEbayCategoryMutation = useMutation({
    mutationFn: async () => {
      return await ebay.getCategories(id);
    },
    onSuccess: (data: EbayCategoryResponse) => {
      if (data.suggested_category) {
        const ebayFields = formik.values.custom_fields?.ebay || {};
        formik.setFieldValue('custom_fields', {
          ...formik.values.custom_fields,
          ebay: {
            ...ebayFields,
            category_id: data.suggested_category.id,
          },
        });
      }
    },
    onError: (error: any) => {
      setError(error.response?.data?.detail || 'Failed to lookup eBay category');
    },
  });

  const formik = useFormik({
    initialValues: {
      name: item?.name || '',
      category: item?.category || '',
      location: item?.location || '',
      brand: item?.brand || '',
      model_number: item?.model_number || '',
      serial_number: item?.serial_number || '',
      purchase_date: item?.purchase_date ? format(new Date(item.purchase_date), 'yyyy-MM-dd') : '',
      purchase_price: item?.purchase_price?.toString() || '',
      current_value: item?.current_value?.toString() || '',
      warranty_expiration: item?.warranty_expiration ? format(new Date(item.warranty_expiration), 'yyyy-MM-dd') : '',
      notes: item?.notes || '',
      custom_fields: item?.custom_fields || {},
    },
    validationSchema,
    enableReinitialize: true,
    onSubmit: async (values) => {
      const itemData: Partial<Item> = {
        ...values,
        purchase_price: values.purchase_price ? parseFloat(values.purchase_price) : undefined,
        current_value: values.current_value ? parseFloat(values.current_value) : undefined,
        purchase_date: values.purchase_date ? new Date(values.purchase_date).toISOString() : undefined,
        warranty_expiration: values.warranty_expiration ? new Date(values.warranty_expiration).toISOString() : undefined,
      };
      updateItemMutation.mutate(itemData);
    },
  });

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files) {
      Array.from(event.target.files).forEach(file => {
        uploadImageMutation.mutate(file);
      });
      // Clear the input
      event.target.value = '';
    }
  };

  const handleDeleteImage = async (imageId: string) => {
    if (window.confirm('Are you sure you want to delete this image?')) {
      deleteImageMutation.mutate(imageId);
    }
  };

  const handleDeleteItem = async () => {
    if (window.confirm('Are you sure you want to delete this item? This action cannot be undone.')) {
      deleteItemMutation.mutate();
    }
  };

  const handleEbayFieldsChange = (fields: EbayFieldsData) => {
    formik.setFieldValue('custom_fields', {
      ...formik.values.custom_fields,
      ebay: fields,
    });
    updateEbayFieldsMutation.mutate(fields);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  return (
    <div>
      <div className="md:flex md:items-center md:justify-between">
        <div className="min-w-0 flex-1">
          <h2 className="text-2xl font-bold leading-7 text-gray-900 sm:truncate sm:text-3xl sm:tracking-tight">
            Edit Item: {item?.name}
          </h2>
        </div>
        <div className="mt-4 flex md:ml-4 md:mt-0">
          <button
            type="button"
            onClick={handleDeleteItem}
            className="ml-3 inline-flex items-center rounded-md bg-red-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-red-700"
          >
            Delete Item
          </button>
        </div>
      </div>

      <form onSubmit={formik.handleSubmit} className="mt-8 space-y-8">
        {error && (
          <div className="rounded-md bg-red-50 p-4">
            <div className="text-sm text-red-700">{error}</div>
          </div>
        )}

        <div className="space-y-8 divide-y divide-gray-200">
          {/* Current Images */}
          {item?.images && item.images.length > 0 && (
            <div className="pt-8">
              <h3 className="text-lg font-medium leading-6 text-gray-900">Current Images</h3>
              <div className="mt-4">
                <ImageGallery
                  images={item.images}
                  onDelete={handleDeleteImage}
                />
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 gap-y-6 sm:grid-cols-6 sm:gap-x-6">
            <div className="sm:col-span-4">
              <label htmlFor="name" className="block text-sm font-medium text-gray-700">
                Name
              </label>
              <input
                type="text"
                id="name"
                {...formik.getFieldProps('name')}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
              />
              {formik.touched.name && formik.errors.name && (
                <p className="mt-2 text-sm text-red-600">{formik.errors.name}</p>
              )}
            </div>

            <div className="sm:col-span-3">
              <label htmlFor="category" className="block text-sm font-medium text-gray-700">
                Category
              </label>
              <select
                id="category"
                {...formik.getFieldProps('category')}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
              >
                <option value="">Select a category</option>
                {categories.map((category: string) => (
                  <option key={category} value={category}>
                    {category}
                  </option>
                ))}
              </select>
              {formik.touched.category && formik.errors.category && (
                <p className="mt-2 text-sm text-red-600">{formik.errors.category}</p>
              )}
            </div>

            <div className="sm:col-span-3">
              <label htmlFor="location" className="block text-sm font-medium text-gray-700">
                Location
              </label>
              <select
                id="location"
                {...formik.getFieldProps('location')}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
              >
                <option value="">Select a location</option>
                {locations.map((location: string) => (
                  <option key={location} value={location}>
                    {location}
                  </option>
                ))}
              </select>
              {formik.touched.location && formik.errors.location && (
                <p className="mt-2 text-sm text-red-600">{formik.errors.location}</p>
              )}
            </div>

            <div className="sm:col-span-3">
              <label htmlFor="brand" className="block text-sm font-medium text-gray-700">
                Brand
              </label>
              <input
                type="text"
                id="brand"
                {...formik.getFieldProps('brand')}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
              />
            </div>

            <div className="sm:col-span-3">
              <label htmlFor="model_number" className="block text-sm font-medium text-gray-700">
                Model Number
              </label>
              <input
                type="text"
                id="model_number"
                {...formik.getFieldProps('model_number')}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
              />
            </div>

            <div className="sm:col-span-3">
              <label htmlFor="serial_number" className="block text-sm font-medium text-gray-700">
                Serial Number
              </label>
              <input
                type="text"
                id="serial_number"
                {...formik.getFieldProps('serial_number')}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
              />
            </div>

            <div className="sm:col-span-3">
              <label htmlFor="purchase_date" className="block text-sm font-medium text-gray-700">
                Purchase Date
              </label>
              <input
                type="date"
                id="purchase_date"
                {...formik.getFieldProps('purchase_date')}
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
                  type="number"
                  id="purchase_price"
                  step="0.01"
                  min="0"
                  {...formik.getFieldProps('purchase_price')}
                  className="mt-1 block w-full pl-7 rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
                />
              </div>
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
                  type="number"
                  id="current_value"
                  step="0.01"
                  min="0"
                  {...formik.getFieldProps('current_value')}
                  className="mt-1 block w-full pl-7 rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
                />
              </div>
            </div>

            <div className="sm:col-span-3">
              <label htmlFor="warranty_expiration" className="block text-sm font-medium text-gray-700">
                Warranty Expiration
              </label>
              <input
                type="date"
                id="warranty_expiration"
                {...formik.getFieldProps('warranty_expiration')}
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
                {...formik.getFieldProps('notes')}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
              />
            </div>

            <div className="sm:col-span-6">
              <label className="block text-sm font-medium text-gray-700 mb-4">
                Custom Fields
              </label>
              <CustomFields
                fields={formik.values.custom_fields}
                onChange={(fields) => formik.setFieldValue('custom_fields', fields)}
              />
            </div>

            <div className="sm:col-span-6">
              <div>
                <label htmlFor="images" className="block text-sm font-medium text-gray-700">
                  Add Images
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
                  <button
                    type="button"
                    onClick={() => setShowCamera(true)}
                    className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 sm:hidden"
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

            {/* eBay Fields */}
            <div className="sm:col-span-6 pt-8">
              <h3 className="text-lg font-medium leading-6 text-gray-900 mb-4">eBay Listing Details</h3>
              <EbayFields
                fields={formik.values.custom_fields?.ebay || {}}
                onChange={handleEbayFieldsChange}
                onCategoryLookup={() => lookupEbayCategoryMutation.mutate()}
              />
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
              disabled={formik.isSubmitting}
              className="ml-3 inline-flex justify-center rounded-md border border-transparent bg-primary-600 py-2 px-4 text-sm font-medium text-white shadow-sm hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
            >
              {formik.isSubmitting ? 'Saving...' : 'Save'}
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}
