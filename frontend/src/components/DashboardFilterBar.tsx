/**
 * Dashboard filter bar — search / category / location / value range /
 * sort controls. Purely presentational: it receives the current
 * ``FilterState`` and dispatches ``FilterAction``s back up.
 *
 * Extracted from Dashboard.tsx so the page component stays focused on
 * data fetching + layout.
 */

import type { Dispatch } from 'react';
import type { FilterAction, FilterState } from '../pages/Dashboard.filters';

export interface DashboardFilterBarProps {
  filters: FilterState;
  dispatch: Dispatch<FilterAction>;
  categories: string[] | undefined;
  locations: string[] | undefined;
}

const fieldClass =
  'block w-full rounded-md border-0 py-1.5 text-fg shadow-sm ring-1 ring-inset ring-line placeholder:text-subtle focus:ring-2 focus:ring-inset focus:ring-primary sm:text-sm sm:leading-6';
const labelClass = 'block text-sm font-medium leading-6 text-fg';

export default function DashboardFilterBar({
  filters,
  dispatch,
  categories,
  locations,
}: DashboardFilterBarProps) {
  return (
    <div className="mt-8 bg-surface-raised shadow-sm ring-1 ring-overlay/5 sm:rounded-xl md:col-span-2">
      <div className="px-4 py-6 sm:p-8">
        <div className="grid grid-cols-1 gap-x-6 gap-y-4 sm:grid-cols-6">
          <div className="sm:col-span-2">
            <label htmlFor="search" className={labelClass}>
              Search
            </label>
            <input
              type="text"
              name="search"
              id="search"
              value={filters.query}
              onChange={(e) =>
                dispatch({ type: 'SET_QUERY', value: e.target.value })
              }
              className={fieldClass}
              placeholder="Search items..."
            />
          </div>

          <div className="sm:col-span-2">
            <label htmlFor="category" className={labelClass}>
              Category
            </label>
            <select
              id="category"
              name="category"
              value={filters.category}
              onChange={(e) =>
                dispatch({ type: 'SET_CATEGORY', value: e.target.value })
              }
              className={fieldClass}
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
            <label htmlFor="location" className={labelClass}>
              Location
            </label>
            <select
              id="location"
              name="location"
              value={filters.location}
              onChange={(e) =>
                dispatch({ type: 'SET_LOCATION', value: e.target.value })
              }
              className={fieldClass}
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
            <label htmlFor="min_value" className={labelClass}>
              Min Value
            </label>
            <div className="mt-1 relative rounded-md shadow-sm">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <span className="text-subtle sm:text-sm">$</span>
              </div>
              <input
                type="number"
                id="min_value"
                min="0"
                step="0.01"
                value={filters.min_value ?? ''}
                onChange={(e) =>
                  dispatch({
                    type: 'SET_MIN_VALUE',
                    value: e.target.value ? Number(e.target.value) : undefined,
                  })
                }
                className={`${fieldClass} pl-7`}
              />
            </div>
          </div>

          <div className="sm:col-span-2">
            <label htmlFor="max_value" className={labelClass}>
              Max Value
            </label>
            <div className="mt-1 relative rounded-md shadow-sm">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <span className="text-subtle sm:text-sm">$</span>
              </div>
              <input
                type="number"
                id="max_value"
                min="0"
                step="0.01"
                value={filters.max_value ?? ''}
                onChange={(e) =>
                  dispatch({
                    type: 'SET_MAX_VALUE',
                    value: e.target.value ? Number(e.target.value) : undefined,
                  })
                }
                className={`${fieldClass} pl-7`}
              />
            </div>
          </div>

          <div className="sm:col-span-2">
            <label htmlFor="sort_by" className={labelClass}>
              Sort By
            </label>
            <select
              id="sort_by"
              value={filters.sort_by}
              onChange={(e) =>
                dispatch({ type: 'SET_SORT_BY', value: e.target.value })
              }
              className={fieldClass}
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
            <label htmlFor="sort_order" className={labelClass}>
              Sort Order
            </label>
            <select
              id="sort_order"
              value={filters.sort_desc ? 'desc' : 'asc'}
              onChange={(e) =>
                dispatch({
                  type: 'SET_SORT_DESC',
                  value: e.target.value === 'desc',
                })
              }
              className={fieldClass}
            >
              <option value="asc">Ascending</option>
              <option value="desc">Descending</option>
            </select>
          </div>
        </div>
      </div>
    </div>
  );
}
