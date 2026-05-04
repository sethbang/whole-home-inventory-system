/**
 * React Router v7 loaders for WHIS.
 *
 * Each loader warms the React Query cache via ``ensureQueryData`` so the
 * target page renders with data already available — eliminating the
 * loading flash that used to happen on every navigation. Components
 * continue to call ``useQuery`` as before; the cached result is returned
 * synchronously.
 *
 * Loaders never return data directly (we return ``null`` by convention).
 * The cache is the single source of truth — ``useLoaderData`` is
 * intentionally not used so we don't have two places to keep in sync.
 */

import type { LoaderFunctionArgs } from 'react-router-dom';

import { analytics } from '../api/analytics';
import { backups } from '../api/backups';
import { items } from '../api/items';
import { llmConfig } from '../api/llmConfig';
import { queryKeys } from '../api/queryKeys';
import type { SearchFilters } from '../api/types';
import { queryClient } from '../queryClient';

const DEFAULT_LIST_FILTERS: SearchFilters = {
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

async function prefetchCategoriesAndLocations(): Promise<void> {
  await Promise.all([
    queryClient.ensureQueryData({
      queryKey: queryKeys.items.categories(),
      queryFn: items.getCategories,
    }),
    queryClient.ensureQueryData({
      queryKey: queryKeys.items.locations(),
      queryFn: items.getLocations,
    }),
  ]);
}

export async function dashboardLoader(): Promise<null> {
  await Promise.all([
    queryClient.ensureQueryData({
      queryKey: queryKeys.items.list(DEFAULT_LIST_FILTERS),
      queryFn: () => items.list(DEFAULT_LIST_FILTERS),
    }),
    prefetchCategoriesAndLocations(),
  ]);
  return null;
}

export async function addItemLoader(): Promise<null> {
  await prefetchCategoriesAndLocations();
  return null;
}

export async function itemDetailLoader({
  params,
}: LoaderFunctionArgs): Promise<null> {
  const id = params.id;
  if (!id) {
    throw new Response('Item ID missing from URL', { status: 400 });
  }
  await Promise.all([
    queryClient.ensureQueryData({
      queryKey: queryKeys.items.detail(id),
      queryFn: () => items.get(id),
    }),
    prefetchCategoriesAndLocations(),
  ]);
  return null;
}

export async function reportsLoader(): Promise<null> {
  await Promise.all([
    queryClient.ensureQueryData({
      queryKey: queryKeys.analytics.valueByCategory(),
      queryFn: analytics.getValueByCategory,
    }),
    queryClient.ensureQueryData({
      queryKey: queryKeys.analytics.valueByLocation(),
      queryFn: analytics.getValueByLocation,
    }),
    queryClient.ensureQueryData({
      queryKey: queryKeys.analytics.valueTrends(),
      queryFn: analytics.getValueTrends,
    }),
    queryClient.ensureQueryData({
      queryKey: queryKeys.analytics.warrantyStatus(),
      queryFn: analytics.getWarrantyStatus,
    }),
    queryClient.ensureQueryData({
      queryKey: queryKeys.analytics.ageAnalysis(),
      queryFn: analytics.getAgeAnalysis,
    }),
  ]);
  return null;
}

export async function backupsLoader(): Promise<null> {
  await queryClient.ensureQueryData({
    queryKey: queryKeys.backups.list(),
    queryFn: async () => (await backups.list()).backups,
  });
  return null;
}

export async function settingsLoader(): Promise<null> {
  // Don't await — a non-admin will be redirected by AdminLayout before
  // the page renders, and we don't want to surface their 403 as a
  // loader error. Catch is a safety net.
  queryClient
    .ensureQueryData({
      queryKey: queryKeys.llmConfig.detail(),
      queryFn: llmConfig.get,
    })
    .catch(() => {
      // Settings page handles its own loading state if the prefetch
      // fails (e.g. the user isn't actually admin server-side).
    });
  return null;
}
