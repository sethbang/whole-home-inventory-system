/**
 * Router configuration.
 *
 * Every page is lazy-loaded via ``lazy: () => import(...)`` so the main
 * bundle stays lean. Routes declare a ``loader`` that prefetches the
 * page's React Query data so the component renders with cached data
 * available immediately. Every route has a ``RouteErrorBoundary`` as its
 * ``errorElement`` so a thrown loader or render error stays localized
 * instead of blanking the app.
 */

import { createBrowserRouter } from 'react-router-dom';

import { RouteErrorBoundary } from '../components/ErrorBoundary';
import {
  addItemLoader,
  backupsLoader,
  browseLoader,
  dashboardLoader,
  itemDetailLoader,
  reportsLoader,
  settingsLoader,
} from './loaders';
import { AdminLayout, ProtectedLayout, RootLayout } from './layouts';

export const router = createBrowserRouter([
  {
    element: <RootLayout />,
    errorElement: <RouteErrorBoundary />,
    children: [
      {
        path: '/login',
        lazy: async () => {
          const mod = await import('../pages/Login');
          return { Component: mod.default };
        },
        errorElement: <RouteErrorBoundary />,
      },
      {
        path: '/register',
        lazy: async () => {
          const mod = await import('../pages/Register');
          return { Component: mod.default };
        },
        errorElement: <RouteErrorBoundary />,
      },
      {
        element: <ProtectedLayout />,
        errorElement: <RouteErrorBoundary />,
        children: [
          {
            index: true,
            loader: dashboardLoader,
            lazy: async () => {
              const mod = await import('../pages/Dashboard');
              return { Component: mod.default };
            },
          },
          {
            path: 'browse',
            loader: browseLoader,
            lazy: async () => {
              const mod = await import('../pages/Browse');
              return { Component: mod.default };
            },
          },
          {
            path: 'items/new',
            loader: addItemLoader,
            lazy: async () => {
              const mod = await import('../pages/AddItem');
              return { Component: mod.default };
            },
          },
          {
            path: 'items/:id',
            loader: itemDetailLoader,
            lazy: async () => {
              const mod = await import('../pages/ItemDetail');
              return { Component: mod.default };
            },
          },
          {
            path: 'reports',
            loader: reportsLoader,
            lazy: async () => {
              const mod = await import('../pages/Reports');
              return { Component: mod.default };
            },
          },
          {
            path: 'backups',
            loader: backupsLoader,
            lazy: async () => {
              const mod = await import('../pages/Backups');
              return { Component: mod.default };
            },
          },
          {
            element: <AdminLayout />,
            errorElement: <RouteErrorBoundary />,
            children: [
              {
                path: 'settings',
                loader: settingsLoader,
                lazy: async () => {
                  const mod = await import('../pages/Settings');
                  return { Component: mod.default };
                },
              },
            ],
          },
        ],
      },
    ],
  },
]);
