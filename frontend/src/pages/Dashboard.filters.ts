/**
 * Dashboard filter/search/sort/pagination state.
 *
 * Previously the Dashboard tracked these eight-odd values in a single
 * ``useState`` object updated with ad-hoc spread callbacks. Consolidating
 * into a typed reducer makes the state transitions explicit (and unit
 * testable in isolation) and guarantees the pagination-reset invariant:
 * any filter change resets ``page`` back to 1 so the user is never left
 * stranded on a now-empty page.
 *
 * The state shape mirrors the backend ``SearchFilter`` Pydantic model and
 * is consumed directly as the React Query key + the ``items.list`` query
 * params — see ``Dashboard.tsx``.
 */

import type { SearchFilters } from '../api/types';

/** Filter state. Shape-compatible with ``SearchFilters`` (all keys present). */
export interface FilterState {
  query: string;
  category: string;
  location: string;
  min_value: number | undefined;
  max_value: number | undefined;
  sort_by: string;
  sort_desc: boolean;
  page: number;
  page_size: number;
}

export const initialFilterState: FilterState = {
  query: '',
  category: '',
  location: '',
  min_value: undefined,
  max_value: undefined,
  sort_by: '',
  sort_desc: false,
  page: 1,
  page_size: 20,
};

/** Discriminated-union of every supported filter transition. */
export type FilterAction =
  | { type: 'SET_QUERY'; value: string }
  | { type: 'SET_CATEGORY'; value: string }
  | { type: 'SET_LOCATION'; value: string }
  | { type: 'SET_MIN_VALUE'; value: number | undefined }
  | { type: 'SET_MAX_VALUE'; value: number | undefined }
  | { type: 'SET_SORT_BY'; value: string }
  | { type: 'SET_SORT_DESC'; value: boolean }
  | { type: 'SET_SORT'; sort_by: string; sort_desc: boolean }
  | { type: 'SET_PAGE'; value: number }
  | { type: 'RESET' };

/**
 * Pure reducer. Every action other than ``SET_PAGE`` and ``RESET``
 * changes the result set, so each of those resets ``page`` to 1.
 */
export function filterReducer(
  state: FilterState,
  action: FilterAction,
): FilterState {
  switch (action.type) {
    case 'SET_QUERY':
      return { ...state, query: action.value, page: 1 };
    case 'SET_CATEGORY':
      return { ...state, category: action.value, page: 1 };
    case 'SET_LOCATION':
      return { ...state, location: action.value, page: 1 };
    case 'SET_MIN_VALUE':
      return { ...state, min_value: action.value, page: 1 };
    case 'SET_MAX_VALUE':
      return { ...state, max_value: action.value, page: 1 };
    case 'SET_SORT_BY':
      return { ...state, sort_by: action.value, page: 1 };
    case 'SET_SORT_DESC':
      return { ...state, sort_desc: action.value, page: 1 };
    case 'SET_SORT':
      return {
        ...state,
        sort_by: action.sort_by,
        sort_desc: action.sort_desc,
        page: 1,
      };
    case 'SET_PAGE':
      return { ...state, page: action.value };
    case 'RESET':
      return { ...initialFilterState };
    default:
      return state;
  }
}

/**
 * Narrows ``FilterState`` to the ``SearchFilters`` shape used as the
 * React Query key + ``items.list`` params. They are structurally the
 * same today; this keeps the call sites honest if either drifts.
 */
export function toSearchFilters(state: FilterState): SearchFilters {
  return {
    query: state.query,
    category: state.category,
    location: state.location,
    min_value: state.min_value,
    max_value: state.max_value,
    sort_by: state.sort_by,
    sort_desc: state.sort_desc,
    page: state.page,
    page_size: state.page_size,
  };
}
