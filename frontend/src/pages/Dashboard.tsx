import React from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { PlusIcon, TrashIcon } from '@heroicons/react/24/outline';
import { items, ebay, facebook } from '../api/client';
import { apiErrorMessage } from '../api/errors';
import { queryKeys } from '../api/queryKeys';
import type { Item, ItemListResponse } from '../api/client';
import DataMigration from '../components/DataMigration';
import ItemCard from '../components/ItemCard';
import ConfirmDialog from '../components/ConfirmDialog';
import DashboardFilterBar from '../components/DashboardFilterBar';
import {
  filterReducer,
  initialFilterState,
  toSearchFilters,
} from './Dashboard.filters';

export default function Dashboard() {
  const queryClient = useQueryClient();
  const [viewMode, setViewMode] = React.useState<'list' | 'grid'>('list');
  const [selectedItems, setSelectedItems] = React.useState<Set<string>>(
    new Set(),
  );
  const [showDeleteConfirm, setShowDeleteConfirm] = React.useState(false);
  const [showDeleteAllConfirm, setShowDeleteAllConfirm] = React.useState(false);
  const [deleteAllConfirmCount, setDeleteAllConfirmCount] = React.useState(0);
  const [filters, dispatch] = React.useReducer(
    filterReducer,
    initialFilterState,
  );
  const searchFilters = React.useMemo(
    () => toSearchFilters(filters),
    [filters],
  );

  const handleDeleteSelected = async () => {
    try {
      await items.bulkDelete(Array.from(selectedItems));
      setSelectedItems(new Set());
      setShowDeleteConfirm(false);
      queryClient.invalidateQueries({ queryKey: queryKeys.items.all });
    } catch (error) {
      console.error('Error deleting items:', error);
      alert('Failed to delete items. Please try again.');
    }
  };

  const handleDeleteAll = async () => {
    if (!data?.items) return;
    try {
      await items.bulkDelete(data.items.map((item) => item.id));
      setShowDeleteAllConfirm(false);
      setDeleteAllConfirmCount(0);
      queryClient.invalidateQueries({ queryKey: queryKeys.items.all });
    } catch (error) {
      console.error('Error deleting all items:', error);
      alert('Failed to delete all items. Please try again.');
    }
  };

  const toggleItemSelection = (itemId: string) => {
    const newSelected = new Set(selectedItems);
    if (newSelected.has(itemId)) {
      newSelected.delete(itemId);
    } else {
      newSelected.add(itemId);
    }
    setSelectedItems(newSelected);
  };

  const { data, isLoading } = useQuery<ItemListResponse>({
    queryKey: queryKeys.items.list(searchFilters),
    queryFn: () => items.list(searchFilters),
  });

  const { data: categories } = useQuery<string[]>({
    queryKey: queryKeys.items.categories(),
    queryFn: items.getCategories,
  });

  const { data: locations } = useQuery<string[]>({
    queryKey: queryKeys.items.locations(),
    queryFn: items.getLocations,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
      </div>
    );
  }

  const allSelected = Boolean(
    data?.items &&
      data.items.length > 0 &&
      data.items.length === selectedItems.size,
  );

  return (
    <div>
      <div className="sm:flex sm:items-center">
        <div className="sm:flex-auto">
          <h1 className="text-2xl font-semibold text-fg">Inventory Items</h1>
          <p className="mt-2 text-sm text-muted">
            A list of all your inventory items including their name, category,
            location, and value.
          </p>
        </div>
        <div className="mt-4 sm:ml-16 sm:mt-0 flex space-x-4">
          {selectedItems.size > 0 && (
            <>
              <button
                onClick={() => setShowDeleteConfirm(true)}
                className="inline-flex items-center rounded-md bg-danger px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-danger"
              >
                <TrashIcon className="h-5 w-5 mr-1" />
                Delete Selected ({selectedItems.size})
              </button>
              <button
                onClick={async () => {
                  try {
                    await ebay.exportItems({
                      item_ids: Array.from(selectedItems),
                    });
                  } catch (err) {
                    alert(apiErrorMessage(err, 'eBay export failed'));
                  }
                }}
                className="inline-flex items-center rounded-md border border-line-strong bg-surface-raised px-3 py-2 text-sm font-semibold text-muted shadow-sm hover:bg-surface-muted"
              >
                Export eBay CSV ({selectedItems.size})
              </button>
              <button
                onClick={async () => {
                  try {
                    await facebook.exportItems({
                      item_ids: Array.from(selectedItems),
                    });
                  } catch (err) {
                    alert(apiErrorMessage(err, 'Facebook export failed'));
                  }
                }}
                className="inline-flex items-center rounded-md border border-line-strong bg-surface-raised px-3 py-2 text-sm font-semibold text-muted shadow-sm hover:bg-surface-muted"
              >
                Export FB Catalog ({selectedItems.size})
              </button>
            </>
          )}
          <button
            onClick={() => {
              setShowDeleteAllConfirm(true);
              setDeleteAllConfirmCount(0);
            }}
            className="inline-flex items-center rounded-md bg-danger px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-danger"
          >
            <TrashIcon className="h-5 w-5 mr-1" />
            Delete All
          </button>
          <Link
            to="/items/new"
            className="block rounded-md bg-primary px-3 py-2 text-center text-sm font-semibold text-white shadow-sm hover:bg-primary focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
          >
            <PlusIcon className="inline-block h-5 w-5 mr-1" />
            Add Item
          </Link>
        </div>
        <div className="mt-4 sm:ml-4 sm:mt-0">
          <div className="flex rounded-md shadow-sm">
            <button
              type="button"
              aria-label="List view"
              aria-pressed={viewMode === 'list'}
              onClick={() => setViewMode('list')}
              className={`relative inline-flex items-center rounded-l-md px-3 py-2 text-sm font-semibold ${
                viewMode === 'list'
                  ? 'bg-primary text-white'
                  : 'bg-surface-raised text-fg ring-1 ring-inset ring-line hover:bg-surface-muted'
              }`}
            >
              List View
            </button>
            <button
              type="button"
              aria-label="Grid view"
              aria-pressed={viewMode === 'grid'}
              onClick={() => setViewMode('grid')}
              className={`relative -ml-px inline-flex items-center rounded-r-md px-3 py-2 text-sm font-semibold ${
                viewMode === 'grid'
                  ? 'bg-primary text-white'
                  : 'bg-surface-raised text-fg ring-1 ring-inset ring-line hover:bg-surface-muted'
              }`}
            >
              Grid View
            </button>
          </div>
        </div>
      </div>

      <DashboardFilterBar
        filters={filters}
        dispatch={dispatch}
        categories={categories}
        locations={locations}
      />

      {/* Data Migration Tools */}
      <div className="mt-8">
        <DataMigration />
      </div>

      {/* Items View */}
      {viewMode === 'list' ? (
        /* List View */
        <div className="mt-8 flow-root">
          <div className="-mx-4 -my-2 overflow-x-auto sm:-mx-6 lg:-mx-8">
            <div className="inline-block min-w-full py-2 align-middle sm:px-6 lg:px-8">
              <div className="overflow-hidden shadow ring-1 ring-overlay ring-opacity-5 sm:rounded-lg">
                <table className="min-w-full divide-y divide-line-strong">
                  <thead className="bg-surface-muted">
                    <tr>
                      <th scope="col" className="relative px-4 sm:px-6 py-3.5">
                        <input
                          type="checkbox"
                          aria-label="Select all items"
                          className="absolute left-4 top-1/2 -mt-2 h-4 w-4 rounded border-line-strong text-primary focus:ring-primary"
                          checked={allSelected}
                          onChange={(e) => {
                            if (e.target.checked && data?.items) {
                              setSelectedItems(
                                new Set(data.items.map((item) => item.id)),
                              );
                            } else {
                              setSelectedItems(new Set());
                            }
                          }}
                        />
                      </th>
                      <th
                        scope="col"
                        className="py-3.5 pl-4 pr-3 text-left text-sm font-semibold text-fg"
                      >
                        Name
                      </th>
                      <th
                        scope="col"
                        className="px-3 py-3.5 text-left text-sm font-semibold text-fg"
                      >
                        Category
                      </th>
                      <th
                        scope="col"
                        className="px-3 py-3.5 text-left text-sm font-semibold text-fg"
                      >
                        Location
                      </th>
                      <th
                        scope="col"
                        className="px-3 py-3.5 text-left text-sm font-semibold text-fg"
                      >
                        Value
                      </th>
                      <th
                        scope="col"
                        className="relative py-3.5 pl-3 pr-4 sm:pr-6"
                      >
                        <span className="sr-only">Actions</span>
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-line bg-surface-raised">
                    {data?.items.map((item: Item) => (
                      <tr key={item.id}>
                        <td className="relative whitespace-nowrap py-4 pl-4 pr-3 sm:pl-6">
                          <input
                            type="checkbox"
                            aria-label={`Select ${item.name}`}
                            className="absolute left-4 top-1/2 -mt-2 h-4 w-4 rounded border-line-strong text-primary focus:ring-primary"
                            checked={selectedItems.has(item.id)}
                            onChange={() => toggleItemSelection(item.id)}
                          />
                        </td>
                        <td className="whitespace-nowrap py-4 pl-4 pr-3 text-sm font-medium text-fg">
                          <Link
                            to={`/items/${item.id}`}
                            className="hover:text-primary"
                          >
                            {item.name}
                          </Link>
                        </td>
                        <td className="whitespace-nowrap px-3 py-4 text-sm text-subtle">
                          {item.category}
                        </td>
                        <td className="whitespace-nowrap px-3 py-4 text-sm text-subtle">
                          {item.location}
                        </td>
                        <td className="whitespace-nowrap px-3 py-4 text-sm text-subtle">
                          ${item.current_value?.toFixed(2) ?? '0.00'}
                        </td>
                        <td className="relative whitespace-nowrap py-4 pl-3 pr-4 text-right text-sm font-medium sm:pr-6">
                          <Link
                            to={`/items/${item.id}`}
                            className="text-primary hover:text-primary-hover"
                          >
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
            <div key={item.id} className="relative">
              <input
                type="checkbox"
                aria-label={`Select ${item.name}`}
                className="absolute left-3 top-3 z-10 h-4 w-4 rounded border-line-strong bg-surface-raised text-primary focus:ring-primary"
                checked={selectedItems.has(item.id)}
                onClick={(e) => e.stopPropagation()}
                onChange={() => toggleItemSelection(item.id)}
              />
              <ItemCard item={item} layout="card" />
            </div>
          ))}
        </div>
      )}

      {/* Pagination */}
      {data && data.total > filters.page_size && (
        <div className="mt-4 flex items-center justify-between">
          <div className="flex flex-1 justify-between sm:hidden">
            <button
              onClick={() =>
                dispatch({ type: 'SET_PAGE', value: filters.page - 1 })
              }
              disabled={filters.page === 1}
              className="relative inline-flex items-center rounded-md border border-line-strong bg-surface-raised px-4 py-2 text-sm font-medium text-muted hover:bg-surface-muted"
            >
              Previous
            </button>
            <button
              onClick={() =>
                dispatch({ type: 'SET_PAGE', value: filters.page + 1 })
              }
              disabled={filters.page * filters.page_size >= data.total}
              className="relative ml-3 inline-flex items-center rounded-md border border-line-strong bg-surface-raised px-4 py-2 text-sm font-medium text-muted hover:bg-surface-muted"
            >
              Next
            </button>
          </div>
          <div className="hidden sm:flex sm:flex-1 sm:items-center sm:justify-between">
            <div>
              <p className="text-sm text-muted">
                Showing{' '}
                <span className="font-medium">
                  {(filters.page - 1) * filters.page_size + 1}
                </span>{' '}
                to{' '}
                <span className="font-medium">
                  {Math.min(filters.page * filters.page_size, data.total)}
                </span>{' '}
                of <span className="font-medium">{data.total}</span> results
              </p>
            </div>
            <div>
              <nav
                className="isolate inline-flex -space-x-px rounded-md shadow-sm"
                aria-label="Pagination"
              >
                <button
                  onClick={() =>
                    dispatch({ type: 'SET_PAGE', value: filters.page - 1 })
                  }
                  disabled={filters.page === 1}
                  className="relative inline-flex items-center rounded-l-md px-2 py-2 text-subtle ring-1 ring-inset ring-line hover:bg-surface-muted focus:z-20 focus:outline-offset-0"
                >
                  <span className="sr-only">Previous</span>
                  Previous
                </button>
                <button
                  onClick={() =>
                    dispatch({ type: 'SET_PAGE', value: filters.page + 1 })
                  }
                  disabled={filters.page * filters.page_size >= data.total}
                  className="relative inline-flex items-center rounded-r-md px-2 py-2 text-subtle ring-1 ring-inset ring-line hover:bg-surface-muted focus:z-20 focus:outline-offset-0"
                >
                  <span className="sr-only">Next</span>
                  Next
                </button>
              </nav>
            </div>
          </div>
        </div>
      )}

      {/* Delete Selected Confirmation Dialog */}
      {showDeleteConfirm && (
        <ConfirmDialog
          title="Delete Selected Items"
          message={`Are you sure you want to delete ${selectedItems.size} selected items? This action cannot be undone.`}
          confirmLabel="Delete"
          onConfirm={handleDeleteSelected}
          onCancel={() => setShowDeleteConfirm(false)}
        />
      )}

      {/* Delete All Confirmation Dialog */}
      {showDeleteAllConfirm && (
        <ConfirmDialog
          title="Delete All Items"
          message={
            deleteAllConfirmCount === 0
              ? 'Are you sure you want to delete ALL items? This action cannot be undone.'
              : deleteAllConfirmCount === 1
                ? 'Please confirm again that you want to delete ALL items.'
                : 'Final confirmation: Delete ALL items permanently?'
          }
          confirmLabel={
            deleteAllConfirmCount < 2
              ? 'Confirm Delete All'
              : 'Delete All Permanently'
          }
          onConfirm={() => {
            if (deleteAllConfirmCount < 2) {
              setDeleteAllConfirmCount((prev) => prev + 1);
            } else {
              handleDeleteAll();
            }
          }}
          onCancel={() => {
            setShowDeleteAllConfirm(false);
            setDeleteAllConfirmCount(0);
          }}
        />
      )}
    </div>
  );
}
