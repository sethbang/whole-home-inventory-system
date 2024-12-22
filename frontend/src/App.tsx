import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { AuthProvider, RequireAuth } from './contexts/AuthContext';
import { DevModeProvider } from './contexts/DevModeContext';
import Layout from './components/Layout';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import AddItem from './pages/AddItem';
import ItemDetail from './pages/ItemDetail';
import Reports from './pages/Reports';
import Backups from './pages/Backups';

// Initialize React Query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <DevModeProvider>
          <AuthProvider>
            <Routes>
              {/* Public routes */}
              <Route path="/login" element={<Login />} />
              <Route path="/register" element={<Register />} />

              {/* Protected routes */}
              <Route
                path="/"
                element={
                  <RequireAuth>
                    <Layout>
                      <Dashboard />
                    </Layout>
                  </RequireAuth>
                }
              />
              <Route
                path="/items/new"
                element={
                  <RequireAuth>
                    <Layout>
                      <AddItem />
                    </Layout>
                  </RequireAuth>
                }
              />
              <Route
                path="/items/:id"
                element={
                  <RequireAuth>
                    <Layout>
                      <ItemDetail />
                    </Layout>
                  </RequireAuth>
                }
              />
              <Route
                path="/reports"
                element={
                  <RequireAuth>
                    <Layout>
                      <Reports />
                    </Layout>
                  </RequireAuth>
                }
              />
              <Route
                path="/backups"
                element={
                  <RequireAuth>
                    <Layout>
                      <Backups />
                    </Layout>
                  </RequireAuth>
                }
              />
            </Routes>
          </AuthProvider>
        </DevModeProvider>
      </Router>
      <ReactQueryDevtools />
    </QueryClientProvider>
  );
}

export default App;
