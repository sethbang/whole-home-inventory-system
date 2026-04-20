/**
 * Layout-route elements for WHIS.
 *
 * React Router v7's data-router pattern composes layouts via nested route
 * elements that render ``<Outlet />``. The app's provider chain
 * (DevModeProvider -> AuthProvider) lives in the root layout so
 * ``useNavigate`` works inside the AuthProvider (it needs to be *inside* a
 * RouterProvider). The protected layout wraps RequireAuth + Layout so
 * every authenticated page gets the chrome with no per-route boilerplate.
 */

import { Outlet } from 'react-router-dom';

import Layout from '../components/Layout';
import { AuthProvider, RequireAuth } from '../contexts/AuthContext';
import { DevModeProvider } from '../contexts/DevModeContext';

export function RootLayout() {
  return (
    <DevModeProvider>
      <AuthProvider>
        <Outlet />
      </AuthProvider>
    </DevModeProvider>
  );
}

export function ProtectedLayout() {
  return (
    <RequireAuth>
      <Layout>
        <Outlet />
      </Layout>
    </RequireAuth>
  );
}
