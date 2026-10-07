import { queryKeys } from '../queryKeys';

describe('queryKeys factory', () => {
  describe('items', () => {
    it('all is the shared prefix', () => {
      expect(queryKeys.items.all).toEqual(['items']);
    });

    it('lists is prefixed by all', () => {
      expect(queryKeys.items.lists()).toEqual(['items', 'list']);
    });

    it('list includes filters so different filters cache separately', () => {
      const filtersA = { query: 'drill', page: 1 };
      const filtersB = { query: 'hammer', page: 1 };
      expect(queryKeys.items.list(filtersA)).not.toEqual(
        queryKeys.items.list(filtersB),
      );
      expect(queryKeys.items.list(filtersA)).toEqual([
        'items',
        'list',
        filtersA,
      ]);
    });

    it('detail is distinct from lists under items.all', () => {
      expect(queryKeys.items.detail('abc')).toEqual(['items', 'detail', 'abc']);
    });

    it('categories and locations are stable sibling keys', () => {
      expect(queryKeys.items.categories()).toEqual(['items', 'categories']);
      expect(queryKeys.items.locations()).toEqual(['items', 'locations']);
    });
  });

  describe('analytics', () => {
    it('every analytics subkey is prefixed by analytics.all', () => {
      const subKeys = [
        queryKeys.analytics.valueByCategory(),
        queryKeys.analytics.valueByLocation(),
        queryKeys.analytics.valueTrends(),
        queryKeys.analytics.warrantyStatus(),
        queryKeys.analytics.ageAnalysis(),
      ];
      for (const key of subKeys) {
        expect(key[0]).toBe('analytics');
      }
    });

    it('subkeys are unique', () => {
      const raw = [
        queryKeys.analytics.valueByCategory(),
        queryKeys.analytics.valueByLocation(),
        queryKeys.analytics.valueTrends(),
        queryKeys.analytics.warrantyStatus(),
        queryKeys.analytics.ageAnalysis(),
      ].map((k) => k.join('/'));
      expect(new Set(raw).size).toBe(raw.length);
    });
  });

  describe('ebay', () => {
    it('categories key varies with itemId', () => {
      expect(queryKeys.ebay.categories()).toEqual(['ebay', 'categories']);
      expect(queryKeys.ebay.categories('abc')).toEqual([
        'ebay',
        'categories',
        'abc',
      ]);
    });
  });

  describe('invalidation semantics', () => {
    it('items.all is a prefix of every items.* subkey', () => {
      // React Query invalidates by prefix; this matters for cache invalidation.
      const subkeys = [
        queryKeys.items.lists(),
        queryKeys.items.detail('id-1'),
        queryKeys.items.categories(),
        queryKeys.items.locations(),
        queryKeys.items.barcode('BAR-1'),
      ];
      for (const key of subkeys) {
        expect(key.slice(0, queryKeys.items.all.length)).toEqual(
          queryKeys.items.all,
        );
      }
    });
  });
});
