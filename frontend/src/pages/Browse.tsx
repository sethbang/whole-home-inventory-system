import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Disclosure } from '@headlessui/react';
import {
  ChevronDownIcon,
  ChevronUpIcon,
  Squares2X2Icon,
  Bars3Icon,
} from '@heroicons/react/24/outline';

import { items } from '../api/items';
import { queryKeys } from '../api/queryKeys';
import type {
  ItemListResponse,
  LocationCount,
  SearchFilters,
} from '../api/types';
import ItemCard from '../components/ItemCard';

type ViewMode = 'card' | 'list';

const PAGE_SIZE = 24;

const INITIAL_FILTERS: Required<
  Pick<SearchFilters, 'query' | 'category' | 'location' | 'sort_by' | 'sort_desc' | 'page' | 'page_size'>
> & { min_value: number | undefined; max_value: number | undefined } = {
  query: '',
  category: '',
  location: '',
  sort_by: '',
  sort_desc: false,
  page: 1,
  page_size: PAGE_SIZE,
  min_value: undefined,
  max_value: undefined,
};

function classNames(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(' ');
}

interface RoomsSidebarProps {
  counts: LocationCount[] | undefined;
  selected: string;
  onSelect: (location: string) => void;
}

function RoomsSidebar({ counts, selected, onSelect }: RoomsSidebarProps) {
  const total = counts?.reduce((sum, c) => sum + c.count, 0) ?? 0;
  return (
    <nav aria-label="Rooms" className="space-y-0.5">
      <button
        type="button"
        onClick={() => onSelect('')}
        className={classNames(
          'flex w-full items-center justify-between rounded-md px-3 py-2 text-sm',
          selected === ''
            ? 'bg-primary-subtle font-semibold text-primary-hover'
            : 'text-muted hover:bg-surface-muted',
        )}
      >
        <span>All</span>
        <span className="text-xs text-subtle">{total}</span>
      </button>
      {counts?.map((row) => (
        <button
          key={row.location}
          type="button"
          onClick={() => onSelect(row.location)}
          className={classNames(
            'flex w-full items-center justify-between rounded-md px-3 py-2 text-sm',
            selected === row.location
              ? 'bg-primary-subtle font-semibold text-primary-hover'
              : 'text-muted hover:bg-surface-muted',
          )}
        >
          <span className="truncate">{row.location}</span>
          <span className="ml-2 text-xs text-subtle">{row.count}</span>
        </button>
      ))}
      {counts && counts.length === 0 && (
        <p className="px-3 py-2 text-xs text-subtle">
          No rooms yet — add an item to get started.
        </p>
      )}
    </nav>
  );
}

function CardSkeletonGrid() {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {Array.from({ length: 8 }).map((_, i) => (
        <div
          key={i}
          className="overflow-hidden rounded-lg border border-line bg-surface-raised"
        >
          <div className="aspect-[4/3] w-full animate-pulse bg-surface-muted" />
          <div className="space-y-2 p-3">
            <div className="h-4 w-3/4 animate-pulse rounded bg-surface-muted" />
            <div className="h-3 w-1/2 animate-pulse rounded bg-surface-muted" />
          </div>
        </div>
      ))}
    </div>
  );
}

export default function Browse() {
  const [filters, setFilters] = React.useState(INITIAL_FILTERS);
  const [viewMode, setViewMode] = React.useState<ViewMode>('card');
  const [showMoreFilters, setShowMoreFilters] = React.useState(false);
  const [searchInput, setSearchInput] = React.useState('');

  // Debounce the search input so we're not firing a request on every
  // keystroke. 250ms is enough to feel responsive but coalesces a typed
  // word into a single request on common typing speeds.
  React.useEffect(() => {
    const handle = window.setTimeout(() => {
      setFilters((prev) =>
        prev.query === searchInput
          ? prev
          : { ...prev, query: searchInput, page: 1 },
      );
    }, 250);
    return () => window.clearTimeout(handle);
  }, [searchInput]);

  const { data, isLoading } = useQuery<ItemListResponse>({
    queryKey: queryKeys.items.list(filters),
    queryFn: () => items.list(filters),
  });

  const { data: locationCounts } = useQuery<LocationCount[]>({
    queryKey: queryKeys.items.locationCounts(),
    queryFn: items.getLocationCounts,
  });

  const { data: categories } = useQuery<string[]>({
    queryKey: queryKeys.items.categories(),
    queryFn: items.getCategories,
  });

  const handleSelectRoom = (location: string) => {
    setFilters((prev) => ({ ...prev, location, page: 1 }));
  };

  const clearAllFilters = () => {
    setSearchInput('');
    setFilters(INITIAL_FILTERS);
  };

  const hasActiveFilters =
    filters.query !== '' ||
    filters.category !== '' ||
    filters.location !== '' ||
    filters.min_value !== undefined ||
    filters.max_value !== undefined;

  const totalPages = data ? Math.max(1, Math.ceil(data.total / filters.page_size)) : 1;

  return (
    <div className="md:flex md:gap-6">
      {/* Mobile rooms accordion */}
      <div className="md:hidden">
        <Disclosure>
          {({ open }) => (
            <div className="rounded-md border border-line bg-surface-raised">
              <Disclosure.Button className="flex w-full items-center justify-between px-3 py-2 text-sm font-medium text-fg">
                <span>
                  Rooms
                  {filters.location && (
                    <span className="ml-2 text-xs text-primary-hover">
                      · {filters.location}
                    </span>
                  )}
                </span>
                {open ? (
                  <ChevronUpIcon className="h-5 w-5 text-subtle" />
                ) : (
                  <ChevronDownIcon className="h-5 w-5 text-subtle" />
                )}
              </Disclosure.Button>
              <Disclosure.Panel className="border-t border-line p-2">
                <RoomsSidebar
                  counts={locationCounts}
                  selected={filters.location}
                  onSelect={handleSelectRoom}
                />
              </Disclosure.Panel>
            </div>
          )}
        </Disclosure>
      </div>

      {/* Desktop rooms sidebar */}
      <aside className="hidden md:block md:w-56 md:flex-shrink-0">
        <div className="sticky top-6">
          <h2 className="mb-2 px-3 text-xs font-semibold uppercase tracking-wide text-subtle">
            Rooms
          </h2>
          <RoomsSidebar
            counts={locationCounts}
            selected={filters.location}
            onSelect={handleSelectRoom}
          />
        </div>
      </aside>

      {/* Main panel */}
      <div className="mt-4 min-w-0 flex-1 md:mt-0">
        <div className="mb-4 flex items-center justify-between gap-2">
          <div>
            <h1 className="text-2xl font-semibold text-fg">Browse</h1>
            <p className="mt-0.5 text-sm text-muted">
              {filters.location
                ? `Items in ${filters.location}`
                : 'All your items'}
              {data && ` · ${data.total} total`}
            </p>
          </div>
        </div>

        {/* Toolbar */}
        <div className="flex flex-wrap items-center gap-2 rounded-md border border-line bg-surface-raised p-2">
          <input
            type="search"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Search items..."
            className="block min-w-0 flex-1 rounded-md border-0 py-1.5 text-sm text-fg ring-1 ring-inset ring-line focus:ring-2 focus:ring-inset focus:ring-primary"
            aria-label="Search items"
          />

          <div className="flex rounded-md shadow-sm" role="group" aria-label="View mode">
            <button
              type="button"
              onClick={() => setViewMode('card')}
              aria-pressed={viewMode === 'card'}
              aria-label="Card view"
              className={classNames(
                'inline-flex items-center rounded-l-md px-2.5 py-1.5 text-sm',
                viewMode === 'card'
                  ? 'bg-primary text-white'
                  : 'bg-surface-raised text-muted ring-1 ring-inset ring-line hover:bg-surface-muted',
              )}
            >
              <Squares2X2Icon className="h-4 w-4" />
            </button>
            <button
              type="button"
              onClick={() => setViewMode('list')}
              aria-pressed={viewMode === 'list'}
              aria-label="List view"
              className={classNames(
                '-ml-px inline-flex items-center rounded-r-md px-2.5 py-1.5 text-sm',
                viewMode === 'list'
                  ? 'bg-primary text-white'
                  : 'bg-surface-raised text-muted ring-1 ring-inset ring-line hover:bg-surface-muted',
              )}
            >
              <Bars3Icon className="h-4 w-4" />
            </button>
          </div>

          <select
            aria-label="Sort"
            value={
              filters.sort_by === ''
                ? ''
                : `${filters.sort_by}:${filters.sort_desc ? 'desc' : 'asc'}`
            }
            onChange={(e) => {
              const v = e.target.value;
              if (v === '') {
                setFilters((prev) => ({
                  ...prev,
                  sort_by: '',
                  sort_desc: false,
                  page: 1,
                }));
                return;
              }
              const [sort_by, dir] = v.split(':');
              setFilters((prev) => ({
                ...prev,
                sort_by,
                sort_desc: dir === 'desc',
                page: 1,
              }));
            }}
            className="rounded-md border-0 py-1.5 pl-2 pr-8 text-sm text-fg ring-1 ring-inset ring-line focus:ring-2 focus:ring-inset focus:ring-primary"
          >
            <option value="">Sort: Default</option>
            <option value="name:asc">Name (A→Z)</option>
            <option value="name:desc">Name (Z→A)</option>
            <option value="current_value:desc">Value (high→low)</option>
            <option value="current_value:asc">Value (low→high)</option>
            <option value="created_at:desc">Newest first</option>
            <option value="created_at:asc">Oldest first</option>
          </select>

          <button
            type="button"
            onClick={() => setShowMoreFilters((v) => !v)}
            aria-expanded={showMoreFilters}
            className="inline-flex items-center gap-1 rounded-md bg-surface-raised px-2.5 py-1.5 text-sm text-muted ring-1 ring-inset ring-line hover:bg-surface-muted"
          >
            More filters
            {showMoreFilters ? (
              <ChevronUpIcon className="h-4 w-4" />
            ) : (
              <ChevronDownIcon className="h-4 w-4" />
            )}
          </button>

          {hasActiveFilters && (
            <button
              type="button"
              onClick={clearAllFilters}
              className="text-sm text-primary-hover hover:underline"
            >
              Clear filters
            </button>
          )}
        </div>

        {showMoreFilters && (
          <div className="mt-2 grid grid-cols-1 gap-3 rounded-md border border-line bg-surface-raised p-3 sm:grid-cols-3">
            <div>
              <label
                htmlFor="browse-category"
                className="block text-xs font-medium text-muted"
              >
                Category
              </label>
              <select
                id="browse-category"
                value={filters.category}
                onChange={(e) =>
                  setFilters((prev) => ({
                    ...prev,
                    category: e.target.value,
                    page: 1,
                  }))
                }
                className="mt-1 block w-full rounded-md border-0 py-1.5 text-sm text-fg ring-1 ring-inset ring-line focus:ring-2 focus:ring-inset focus:ring-primary"
              >
                <option value="">All categories</option>
                {categories?.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label
                htmlFor="browse-min-value"
                className="block text-xs font-medium text-muted"
              >
                Min value
              </label>
              <input
                id="browse-min-value"
                type="number"
                min={0}
                step="0.01"
                value={filters.min_value ?? ''}
                onChange={(e) =>
                  setFilters((prev) => ({
                    ...prev,
                    min_value: e.target.value === '' ? undefined : Number(e.target.value),
                    page: 1,
                  }))
                }
                className="mt-1 block w-full rounded-md border-0 py-1.5 text-sm text-fg ring-1 ring-inset ring-line focus:ring-2 focus:ring-inset focus:ring-primary"
              />
            </div>
            <div>
              <label
                htmlFor="browse-max-value"
                className="block text-xs font-medium text-muted"
              >
                Max value
              </label>
              <input
                id="browse-max-value"
                type="number"
                min={0}
                step="0.01"
                value={filters.max_value ?? ''}
                onChange={(e) =>
                  setFilters((prev) => ({
                    ...prev,
                    max_value: e.target.value === '' ? undefined : Number(e.target.value),
                    page: 1,
                  }))
                }
                className="mt-1 block w-full rounded-md border-0 py-1.5 text-sm text-fg ring-1 ring-inset ring-line focus:ring-2 focus:ring-inset focus:ring-primary"
              />
            </div>
          </div>
        )}

        {/* Results */}
        <div className="mt-4">
          {isLoading ? (
            <CardSkeletonGrid />
          ) : data && data.items.length === 0 ? (
            <div className="rounded-md border border-dashed border-line-strong bg-surface-raised p-8 text-center">
              <p className="text-sm text-muted">No items match these filters.</p>
              {hasActiveFilters && (
                <button
                  type="button"
                  onClick={clearAllFilters}
                  className="mt-2 text-sm font-medium text-primary-hover hover:underline"
                >
                  Clear filters
                </button>
              )}
            </div>
          ) : viewMode === 'card' ? (
            <div
              data-testid="browse-card-grid"
              className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
            >
              {data?.items.map((item) => (
                <ItemCard key={item.id} item={item} layout="card" />
              ))}
            </div>
          ) : (
            <div data-testid="browse-list" className="space-y-2">
              {data?.items.map((item) => (
                <ItemCard key={item.id} item={item} layout="row" />
              ))}
            </div>
          )}
        </div>

        {/* Pagination */}
        {data && data.total > filters.page_size && (
          <div className="mt-6 flex items-center justify-between">
            <p className="text-sm text-muted">
              Showing{' '}
              <span className="font-medium">
                {(filters.page - 1) * filters.page_size + 1}
              </span>
              –
              <span className="font-medium">
                {Math.min(filters.page * filters.page_size, data.total)}
              </span>{' '}
              of <span className="font-medium">{data.total}</span>
            </p>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() =>
                  setFilters((prev) => ({ ...prev, page: Math.max(1, prev.page - 1) }))
                }
                disabled={filters.page === 1}
                className="inline-flex items-center rounded-md bg-surface-raised px-3 py-1.5 text-sm text-muted ring-1 ring-inset ring-line hover:bg-surface-muted disabled:opacity-50"
              >
                Previous
              </button>
              <span className="inline-flex items-center text-sm text-muted">
                Page {filters.page} / {totalPages}
              </span>
              <button
                type="button"
                onClick={() =>
                  setFilters((prev) => ({ ...prev, page: prev.page + 1 }))
                }
                disabled={filters.page * filters.page_size >= data.total}
                className="inline-flex items-center rounded-md bg-surface-raised px-3 py-1.5 text-sm text-muted ring-1 ring-inset ring-line hover:bg-surface-muted disabled:opacity-50"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
