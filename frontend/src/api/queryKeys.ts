/**
 * Centralized React Query cache key factory.
 *
 * Query keys used to be inline string tuples scattered across pages
 * (``['items']``, ``['items', id]``, ``['analytics', 'value-trends']``).
 * Duplicating them by hand is how cache-invalidation bugs ship — miss
 * a key and stale data survives a mutation.
 *
 * The factory exposes a hierarchical shape so ``invalidateQueries`` can
 * hit the right granularity. Example:
 *
 *   queryKeys.items.all              -> ['items']
 *   queryKeys.items.lists()          -> ['items', 'list']
 *   queryKeys.items.list({q:'drill'})-> ['items', 'list', { q: 'drill' }]
 *   queryKeys.items.detail(id)       -> ['items', 'detail', id]
 *
 * ``invalidateQueries({ queryKey: queryKeys.items.all })`` invalidates
 * everything under ``items`` (prefix match). Target a single detail with
 * ``queryKeys.items.detail(id)`` and the lists stay warm.
 *
 * Pattern adapted from tkdodo's "Effective React Query Keys".
 */

import type { SearchFilters } from '../types/items';

export const queryKeys = {
  items: {
    all: ['items'] as const,
    lists: () => [...queryKeys.items.all, 'list'] as const,
    list: (filters: SearchFilters) =>
      [...queryKeys.items.lists(), filters] as const,
    details: () => [...queryKeys.items.all, 'detail'] as const,
    detail: (id: string) => [...queryKeys.items.details(), id] as const,
    categories: () => [...queryKeys.items.all, 'categories'] as const,
    locations: () => [...queryKeys.items.all, 'locations'] as const,
    barcode: (barcode: string) =>
      [...queryKeys.items.all, 'barcode', barcode] as const,
  },
  images: {
    all: ['images'] as const,
    byItem: (itemId: string) =>
      [...queryKeys.images.all, 'byItem', itemId] as const,
  },
  backups: {
    all: ['backups'] as const,
    list: () => [...queryKeys.backups.all, 'list'] as const,
  },
  analytics: {
    all: ['analytics'] as const,
    valueByCategory: () =>
      [...queryKeys.analytics.all, 'value-by-category'] as const,
    valueByLocation: () =>
      [...queryKeys.analytics.all, 'value-by-location'] as const,
    valueTrends: () => [...queryKeys.analytics.all, 'value-trends'] as const,
    warrantyStatus: () =>
      [...queryKeys.analytics.all, 'warranty-status'] as const,
    ageAnalysis: () => [...queryKeys.analytics.all, 'age-analysis'] as const,
  },
  ebay: {
    all: ['ebay'] as const,
    categories: (itemId?: string) =>
      itemId
        ? ([...queryKeys.ebay.all, 'categories', itemId] as const)
        : ([...queryKeys.ebay.all, 'categories'] as const),
  },
  facebook: {
    // v2.3 landing. Keys defined up front so the frontend can register
    // invalidations against them as soon as the FB endpoints ship.
    all: ['facebook'] as const,
    categories: () => [...queryKeys.facebook.all, 'categories'] as const,
  },
} as const;
