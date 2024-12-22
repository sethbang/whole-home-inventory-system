import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { PlusIcon } from '@heroicons/react/24/outline';
import { items } from '../api/client';
import type { Item, ItemListResponse } from '../api/client';

export default function Dashboard() {
  const [viewMode, setViewMode] = React.useState<'list' | 'grid'>('list');
  const [searchFilters, setSearchFilters] = React.useState({
    query: '',
    category: '',
    location: '',
    min_value: undefined as number | undefined,
    max_value: undefined as number | undefined,
    sort_by: '',
    sort_desc: false,
    page: 1,
    page_size: 20,
  });

  const { data, isLoading } = useQuery<ItemListResponse>({
    queryKey: ['items', searchFilters],
    queryFn: () => items.list(searchFilters),
  });

  const { data: categories } = useQuery<string[]>({
    queryKey: ['categories'],
    queryFn: items.getCategories,
  });

  const { data: locations } = useQuery<string[]>({
    queryKey: ['locations'],
    queryFn: items.getLocations,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  return (
    <div>
      <div className="sm:flex sm:items-center">
        <div className="sm:flex-auto">
          <h1 className="text-2xl font-semibold text-gray-900">Inventory Items</h1>
          <p className="mt-2 text-sm text-gray-700">
            A list of all your inventory items including their name, category, location, and value.
          </p>
        </div>
        <div className="mt-4 sm:ml-16 sm:mt-0 sm:flex-none">
          <Link
            to="/items/new"
            className="block rounded-md bg-primary-600 px-3 py-2 text-center text-sm font-semibold text-white shadow-sm hover:bg-primary-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-600"
          >
            <PlusIcon className="inline-block h-5 w-5 mr-1" />
            Add Item
          </Link>
        </div>
        <div className="mt-4 sm:ml-4 sm:mt-0">
          <div className="flex rounded-md shadow-sm">
            <button
              type="button"
              onClick={() => setViewMode('list')}
              className={`relative inline-flex items-center rounded-l-md px-3 py-2 text-sm font-semibold ${
                viewMode === 'list'
                  ? 'bg-primary-600 text-white'
                  : 'bg-white text-gray-900 ring-1 ring-inset ring-gray-300 hover:bg-gray-50'
              }`}
            >
              List View
            </button>
            <button
              type="button"
              onClick={() => setViewMode('grid')}
              className={`relative -ml-px inline-flex items-center rounded-r-md px-3 py-2 text-sm font-semibold ${
                viewMode === 'grid'
                  ? 'bg-primary-600 text-white'
                  : 'bg-white text-gray-900 ring-1 ring-inset ring-gray-300 hover:bg-gray-50'
              }`}
            >
              Grid View
            </button>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="mt-8 bg-white shadow-sm ring-1 ring-gray-900/5 sm:rounded-xl md:col-span-2">
        <div className="px-4 py-6 sm:p-8">
          <div className="grid grid-cols-1 gap-x-6 gap-y-4 sm:grid-cols-6">
            <div className="sm:col-span-2">
              <label htmlFor="search" className="block text-sm font-medium leading-6 text-gray-900">
                Search
              </label>
              <input
                type="text"
                name="search"
                id="search"
                value={searchFilters.query}
                onChange={(e) => setSearchFilters((prev) => ({ ...prev, query: e.target.value }))}
                className="block w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-primary-600 sm:text-sm sm:leading-6"
                placeholder="Search items..."
              />
            </div>

            <div className="sm:col-span-2">
              <label htmlFor="category" className="block text-sm font-medium leading-6 text-gray-900">
                Category
              </label>
              <select
                id="category"
                name="category"
                value={searchFilters.category}
                onChange={(e) => setSearchFilters((prev) => ({ ...prev, category: e.target.value }))}
                className="block w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 focus:ring-2 focus:ring-inset focus:ring-primary-600 sm:text-sm sm:leading-6"
              >
                <option value="">All Categories</option>
                {categories?.map((category) => (
                  <option key={category} value={category}>
                    {category}
                  </option>
                ))}
              </select>
            </div>

            <div className="sm:col-span-2">
              <label htmlFor="location" className="block text-sm font-medium leading-6 text-gray-900">
                Location
              </label>
              <select
                id="location"
                name="location"
                value={searchFilters.location}
                onChange={(e) => setSearchFilters((prev) => ({ ...prev, location: e.target.value }))}
                className="block w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 focus:ring-2 focus:ring-inset focus:ring-primary-600 sm:text-sm sm:leading-6"
              >
                <option value="">All Locations</option>
                {locations?.map((location) => (
                  <option key={location} value={location}>
                    {location}
                  </option>
                ))}
              </select>
            </div>

            <div className="sm:col-span-2">
              <label htmlFor="min_value" className="block text-sm font-medium leading-6 text-gray-900">
                Min Value
              </label>
              <div className="mt-1 relative rounded-md shadow-sm">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <span className="text-gray-500 sm:text-sm">$</span>
                </div>
                <input
                  type="number"
                  id="min_value"
                  min="0"
                  step="0.01"
                  value={searchFilters.min_value || ''}
                  onChange={(e) => setSearchFilters((prev) => ({ ...prev, min_value: e.target.value ? Number(e.target.value) : undefined }))}
                  className="block w-full pl-7 rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-primary-600 sm:text-sm sm:leading-6"
                />
              </div>
            </div>

            <div className="sm:col-span-2">
              <label htmlFor="max_value" className="block text-sm font-medium leading-6 text-gray-900">
                Max Value
              </label>
              <div className="mt-1 relative rounded-md shadow-sm">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <span className="text-gray-500 sm:text-sm">$</span>
                </div>
                <input
                  type="number"
                  id="max_value"
                  min="0"
                  step="0.01"
                  value={searchFilters.max_value || ''}
                  onChange={(e) => setSearchFilters((prev) => ({ ...prev, max_value: e.target.value ? Number(e.target.value) : undefined }))}
                  className="block w-full pl-7 rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-primary-600 sm:text-sm sm:leading-6"
                />
              </div>
            </div>

            <div className="sm:col-span-2">
              <label htmlFor="sort_by" className="block text-sm font-medium leading-6 text-gray-900">
                Sort By
              </label>
              <select
                id="sort_by"
                value={searchFilters.sort_by}
                onChange={(e) => setSearchFilters((prev) => ({ ...prev, sort_by: e.target.value }))}
                className="block w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 focus:ring-2 focus:ring-inset focus:ring-primary-600 sm:text-sm sm:leading-6"
              >
                <option value="">None</option>
                <option value="name">Name</option>
                <option value="category">Category</option>
                <option value="location">Location</option>
                <option value="current_value">Value</option>
                <option value="created_at">Date Added</option>
              </select>
            </div>

            <div className="sm:col-span-2">
              <label htmlFor="sort_order" className="block text-sm font-medium leading-6 text-gray-900">
                Sort Order
              </label>
              <select
                id="sort_order"
                value={searchFilters.sort_desc ? 'desc' : 'asc'}
                onChange={(e) => setSearchFilters((prev) => ({ ...prev, sort_desc: e.target.value === 'desc' }))}
                className="block w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 focus:ring-2 focus:ring-inset focus:ring-primary-600 sm:text-sm sm:leading-6"
              >
                <option value="asc">Ascending</option>
                <option value="desc">Descending</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Items View */}
      {viewMode === 'list' ? (
        /* List View */
        <div className="mt-8 flow-root">
          <div className="-mx-4 -my-2 overflow-x-auto sm:-mx-6 lg:-mx-8">
            <div className="inline-block min-w-full py-2 align-middle sm:px-6 lg:px-8">
              <div className="overflow-hidden shadow ring-1 ring-black ring-opacity-5 sm:rounded-lg">
                <table className="min-w-full divide-y divide-gray-300">
                  <thead className="bg-gray-50">
                    <tr>
                      <th scope="col" className="py-3.5 pl-4 pr-3 text-left text-sm font-semibold text-gray-900 sm:pl-6">
                        Name
                      </th>
                      <th scope="col" className="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">
                        Category
                      </th>
                      <th scope="col" className="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">
                        Location
                      </th>
                      <th scope="col" className="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">
                        Value
                      </th>
                      <th scope="col" className="relative py-3.5 pl-3 pr-4 sm:pr-6">
                        <span className="sr-only">Actions</span>
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200 bg-white">
                    {data?.items.map((item: Item) => (
                      <tr key={item.id}>
                        <td className="whitespace-nowrap py-4 pl-4 pr-3 text-sm font-medium text-gray-900 sm:pl-6">
                          <Link to={`/items/${item.id}`} className="hover:text-primary-600">
                            {item.name}
                          </Link>
                        </td>
                        <td className="whitespace-nowrap px-3 py-4 text-sm text-gray-500">{item.category}</td>
                        <td className="whitespace-nowrap px-3 py-4 text-sm text-gray-500">{item.location}</td>
                        <td className="whitespace-nowrap px-3 py-4 text-sm text-gray-500">
                          ${item.current_value?.toFixed(2) ?? '0.00'}
                        </td>
                        <td className="relative whitespace-nowrap py-4 pl-3 pr-4 text-right text-sm font-medium sm:pr-6">
                          <Link to={`/items/${item.id}`} className="text-primary-600 hover:text-primary-900">
                            Edit
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      ) : (
        /* Grid View */
        <div className="mt-8 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {data?.items.map((item: Item) => (
            <div key={item.id} className="relative flex flex-col overflow-hidden rounded-lg border border-gray-200">
              {item.images && item.images[0] && (
                <div className="aspect-h-1 aspect-w-1 bg-gray-200">
                  <img
                    src={`http://localhost:8000/uploads/${item.images[0].filename}`}
                    alt=""
                    className="h-48 w-full object-cover"
                  />
                </div>
              )}
              <div className="flex flex-1 flex-col p-4">
                <h3 className="text-sm font-medium text-gray-900">
                  <Link to={`/items/${item.id}`} className="hover:text-primary-600">
                    {item.name}
                  </Link>
                </h3>
                <dl className="mt-2 flex flex-col">
                  <dt className="sr-only">Category</dt>
                  <dd className="text-sm text-gray-500">{item.category}</dd>
                  <dt className="sr-only">Location</dt>
                  <dd className="text-sm text-gray-500">{item.location}</dd>
                  <dt className="sr-only">Value</dt>
                  <dd className="mt-1 text-sm font-medium text-gray-900">
                    ${item.current_value?.toFixed(2) ?? '0.00'}
                  </dd>
                </dl>
                <div className="mt-4">
                  <Link
                    to={`/items/${item.id}`}
                    className="text-sm font-medium text-primary-600 hover:text-primary-500"
                  >
                    Edit
                  </Link>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Pagination */}
      {data && data.total > searchFilters.page_size && (
        <div className="mt-4 flex items-center justify-between">
          <div className="flex flex-1 justify-between sm:hidden">
            <button
              onClick={() => setSearchFilters((prev) => ({ ...prev, page: prev.page - 1 }))}
              disabled={searchFilters.page === 1}
              className="relative inline-flex items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Previous
            </button>
            <button
              onClick={() => setSearchFilters((prev) => ({ ...prev, page: prev.page + 1 }))}
              disabled={searchFilters.page * searchFilters.page_size >= data.total}
              className="relative ml-3 inline-flex items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Next
            </button>
          </div>
          <div className="hidden sm:flex sm:flex-1 sm:items-center sm:justify-between">
            <div>
              <p className="text-sm text-gray-700">
                Showing <span className="font-medium">{(searchFilters.page - 1) * searchFilters.page_size + 1}</span> to{' '}
                <span className="font-medium">
                  {Math.min(searchFilters.page * searchFilters.page_size, data.total)}
                </span>{' '}
                of <span className="font-medium">{data.total}</span> results
              </p>
            </div>
            <div>
              <nav className="isolate inline-flex -space-x-px rounded-md shadow-sm" aria-label="Pagination">
                <button
                  onClick={() => setSearchFilters((prev) => ({ ...prev, page: prev.page - 1 }))}
                  disabled={searchFilters.page === 1}
                  className="relative inline-flex items-center rounded-l-md px-2 py-2 text-gray-400 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 focus:z-20 focus:outline-offset-0"
                >
                  <span className="sr-only">Previous</span>
                  Previous
                </button>
                <button
                  onClick={() => setSearchFilters((prev) => ({ ...prev, page: prev.page + 1 }))}
                  disabled={searchFilters.page * searchFilters.page_size >= data.total}
                  className="relative inline-flex items-center rounded-r-md px-2 py-2 text-gray-400 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 focus:z-20 focus:outline-offset-0"
                >
                  <span className="sr-only">Next</span>
                  Next
                </button>
              </nav>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
