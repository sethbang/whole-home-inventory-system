/**
 * Loader tests.
 *
 * Loaders are fire-and-forget: they prefetch into the React Query cache
 * and return null. The tests assert that each loader populates its
 * expected cache keys so ``useQuery`` in the matching page reads from
 * the cache synchronously on first render.
 */

import { LoaderFunctionArgs } from 'react-router-dom';

import { queryKeys } from '../../api/queryKeys';
import { queryClient } from '../../queryClient';
import {
  addItemLoader,
  backupsLoader,
  dashboardLoader,
  itemDetailLoader,
  reportsLoader,
} from '../loaders';

// Mock every api module that the loaders touch. The ``../http`` mock
// isn't necessary because we replace the helper objects wholesale.
jest.mock('../../api/items', () => ({
  items: {
    list: jest.fn().mockResolvedValue({
      items: [{ id: '1', name: 'X' }],
      total: 1,
      page: 1,
      page_size: 20,
    }),
    get: jest.fn().mockResolvedValue({ id: '1', name: 'Drill' }),
    getCategories: jest.fn().mockResolvedValue(['Tools']),
    getLocations: jest.fn().mockResolvedValue(['Garage']),
  },
}));
jest.mock('../../api/analytics', () => ({
  analytics: {
    getValueByCategory: jest.fn().mockResolvedValue([]),
    getValueByLocation: jest.fn().mockResolvedValue([]),
    getValueTrends: jest.fn().mockResolvedValue({
      total_purchase_value: 0,
      total_current_value: 0,
      value_change: 0,
      value_change_percentage: 0,
    }),
    getWarrantyStatus: jest.fn().mockResolvedValue({
      expiring_soon: [],
      expired: [],
      active: [],
    }),
    getAgeAnalysis: jest.fn().mockResolvedValue({}),
  },
}));
jest.mock('../../api/backups', () => ({
  backups: {
    list: jest.fn().mockResolvedValue({ backups: [] }),
  },
}));

beforeEach(() => {
  queryClient.clear();
});

describe('dashboardLoader', () => {
  it('prefetches the default items list plus categories and locations', async () => {
    await dashboardLoader();
    expect(
      queryClient.getQueryData(queryKeys.items.categories()),
    ).toEqual(['Tools']);
    expect(
      queryClient.getQueryData(queryKeys.items.locations()),
    ).toEqual(['Garage']);
    // A list query is present (exact key shape uses the filter object).
    const cached = queryClient.getQueriesData({
      queryKey: queryKeys.items.lists(),
    });
    expect(cached.length).toBeGreaterThan(0);
  });
});

describe('addItemLoader', () => {
  it('prefetches categories and locations', async () => {
    await addItemLoader();
    expect(
      queryClient.getQueryData(queryKeys.items.categories()),
    ).toEqual(['Tools']);
    expect(
      queryClient.getQueryData(queryKeys.items.locations()),
    ).toEqual(['Garage']);
  });
});

describe('itemDetailLoader', () => {
  it('prefetches the item detail by id', async () => {
    await itemDetailLoader({
      params: { id: 'abc' },
    } as unknown as LoaderFunctionArgs);

    expect(queryClient.getQueryData(queryKeys.items.detail('abc'))).toEqual({
      id: '1',
      name: 'Drill',
    });
  });

  it('throws when id is missing', async () => {
    await expect(
      itemDetailLoader({
        params: {},
      } as unknown as LoaderFunctionArgs),
    ).rejects.toBeTruthy();
  });
});

describe('reportsLoader', () => {
  it('prefetches all five analytics subscriptions', async () => {
    await reportsLoader();
    expect(
      queryClient.getQueryData(queryKeys.analytics.valueByCategory()),
    ).toBeDefined();
    expect(
      queryClient.getQueryData(queryKeys.analytics.valueByLocation()),
    ).toBeDefined();
    expect(
      queryClient.getQueryData(queryKeys.analytics.valueTrends()),
    ).toBeDefined();
    expect(
      queryClient.getQueryData(queryKeys.analytics.warrantyStatus()),
    ).toBeDefined();
    expect(
      queryClient.getQueryData(queryKeys.analytics.ageAnalysis()),
    ).toBeDefined();
  });
});

describe('backupsLoader', () => {
  it('prefetches the backups list', async () => {
    await backupsLoader();
    expect(queryClient.getQueryData(queryKeys.backups.list())).toEqual([]);
  });
});
