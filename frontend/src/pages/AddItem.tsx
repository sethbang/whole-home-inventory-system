import React, { useState } from 'react';
import CustomFields from '../components/CustomFields';
import CameraCapture from '../components/CameraCapture';
import { CameraIcon } from '@heroicons/react/24/outline';
import { useNavigate } from 'react-router-dom';
import { useFormik } from 'formik';
import * as Yup from 'yup';
import { useMutation, useQuery } from '@tanstack/react-query';
import { items, images } from '../api/client';

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

export default function AddItem() {
  const navigate = useNavigate();
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [showCamera, setShowCamera] = useState(false);

  // Fetch categories and locations for autocomplete (to be implemented)
  useQuery({
    queryKey: ['categories'],
    queryFn: items.getCategories,
  });

  useQuery({
    queryKey: ['locations'],
    queryFn: items.getLocations,
  });

  interface FormValues {
    name: string;
    category: string;
    location: string;
    brand: string;
    model_number: string;
    serial_number: string;
    purchase_date: string;
    purchase_price: string;
    current_value: string;
    warranty_expiration: string;
    notes: string;
    custom_fields: Record<string, unknown>;
  }

  const createItemMutation = useMutation({
    mutationFn: async (params: { values: FormValues } & { isDev?: boolean }) => {
      const { values, isDev } = params;
      const item = await items.create(
        isDev ? {} : {
          ...values,
          purchase_price: values.purchase_price ? parseFloat(values.purchase_price) : undefined,
          current_value: values.current_value ? parseFloat(values.current_value) : undefined,
          purchase_date: values.purchase_date || undefined,
          warranty_expiration: values.warranty_expiration || undefined,
        },
        isDev
      );
      if (selectedFiles.length > 0) {
        await Promise.all(selectedFiles.map((file) => images.upload(item.id, file)));
      }
      return item;
    },
    onSuccess: () => {
      navigate('/');
    },
    onError: (error: any) => {
      setError(error.response?.data?.detail || 'Failed to create item');
    },
  });

  const formik = useFormik({
    initialValues: {
      name: '',
      category: '',
      location: '',
      brand: '',
      model_number: '',
      serial_number: '',
      purchase_date: '',
      purchase_price: '',
      current_value: '',
      warranty_expiration: '',
      notes: '',
      custom_fields: {},
    },
    validationSchema,
    onSubmit: async (values: FormValues) => {
      createItemMutation.mutate({ values, isDev: false });
    },
  });

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
          <button
            type="button"
            onClick={() => {
              createItemMutation.mutate({ 
                values: {} as FormValues,
                isDev: true 
              });
            }}
            className="ml-3 inline-flex items-center rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600"
          >
            Quick Add (Dev)
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
              <input
                type="text"
                id="category"
                {...formik.getFieldProps('category')}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
                placeholder="Enter a category"
              />
              {formik.touched.category && formik.errors.category && (
                <p className="mt-2 text-sm text-red-600">{formik.errors.category}</p>
              )}
            </div>

            <div className="sm:col-span-3">
              <label htmlFor="location" className="block text-sm font-medium text-gray-700">
                Location
              </label>
              <input
                type="text"
                id="location"
                {...formik.getFieldProps('location')}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
                placeholder="Enter a location"
              />
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
                    setSelectedFiles((prev) => [...prev, file]);
                  }}
                  onClose={() => setShowCamera(false)}
                />
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
