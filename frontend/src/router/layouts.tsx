/**
 * Layout-route elements for WHIS.
 *
 * React Router v7's data-router pattern composes layouts via nested route
 * elements that render ``<Outlet />``. The app's provider chain
 * (ThemeProvider -> DevModeProvider -> AuthProvider) lives in the root
 * layout so ``useNavigate`` works inside the AuthProvider (it needs to be
 * *inside* a RouterProvider). ThemeProvider is outermost so Login /
 * Register inherit the active day/night theme even before AuthProvider
 * resolves a session. The protected layout wraps RequireAuth + Layout so
 * every authenticated page gets the chrome with no per-route boilerplate.
 */

import { Navigate, Outlet } from 'react-router-dom';

import Layout from '../components/Layout';
import { AuthProvider, RequireAuth } from '../contexts/AuthContext';
import { DevModeProvider } from '../contexts/DevModeContext';
import { ThemeProvider } from '../contexts/ThemeContext';
import { useAuth } from '../contexts/useAuth';

export function RootLayout() {
  return (
    <ThemeProvider>
      <DevModeProvider>
        <AuthProvider>
          <Outlet />
        </AuthProvider>
      </DevModeProvider>
    </ThemeProvider>
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

/**
 * Admin-only nested layout. Renders the protected chrome only when the
 * current user is admin; otherwise redirects home. The auth context
 * already enforces "must be authenticated"; this adds the admin gate.
 */
export function AdminLayout() {
  const { user, isLoading } = useAuth();
  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary" />
      </div>
    );
  }
  if (!user || !user.is_admin) {
    return <Navigate to="/" replace />;
  }
  return <Outlet />;
}
