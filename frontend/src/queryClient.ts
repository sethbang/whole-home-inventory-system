/**
 * App-wide React Query client singleton.
 *
 * Needs to live outside the React tree so route loaders (which run before
 * any component mounts) can call ``queryClient.ensureQueryData(...)`` to
 * prefetch a page's data. The ``<QueryClientProvider>`` in App.tsx uses
 * this same instance so ``useQuery`` in components reads from the already-
 * populated cache.
 */

import { QueryClient } from '@tanstack/react-query';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});
