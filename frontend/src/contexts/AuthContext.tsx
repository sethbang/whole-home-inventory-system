import React, { createContext, useContext, useEffect, useState } from 'react';
import { User, auth } from '../api/client';
import { useNavigate } from 'react-router-dom';
import { useDevMode } from './DevModeContext';

// Default admin user for development
const DEV_USER: User = {
  id: 'a7a41c99-5555-4191-9b62-5e39b347b515',
  email: 'admin@example.com',
  username: 'admin',
  is_active: true,
  created_at: new Date().toISOString()
};

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  register: (email: string, username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const navigate = useNavigate();
  const { isDevMode } = useDevMode();

  useEffect(() => {
    if (isDevMode) {
      setUser(DEV_USER);
      localStorage.setItem('whis_token', 'dev_token');
      setIsLoading(false);
      return;
    }

    const token = localStorage.getItem('whis_token');
    if (token) {
      auth.getCurrentUser()
        .then(user => setUser(user))
        .catch(() => {
          localStorage.removeItem('whis_token');
          navigate('/login');
        })
        .finally(() => setIsLoading(false));
    } else {
      setIsLoading(false);
    }
  }, [navigate, isDevMode]);

  const login = async (username: string, password: string) => {
    if (isDevMode) {
      setUser(DEV_USER);
      localStorage.setItem('whis_token', 'dev_token');
      navigate('/');
      return;
    }

    const response = await auth.login({ username, password });
    localStorage.setItem('whis_token', response.access_token);
    const user = await auth.getCurrentUser();
    setUser(user);
    navigate('/');
  };

  const register = async (email: string, username: string, password: string) => {
    if (isDevMode) {
      setUser(DEV_USER);
      localStorage.setItem('whis_token', 'dev_token');
      navigate('/');
      return;
    }

    await auth.register({ email, username, password });
    await login(username, password);
  };

  const logout = () => {
    if (isDevMode) {
      setUser(DEV_USER);
      return;
    }

    localStorage.removeItem('whis_token');
    setUser(null);
    navigate('/login');
  };

  return (
    <AuthContext.Provider value={{ user, isLoading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

export function RequireAuth({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth();
  const { isDevMode } = useDevMode();
  const navigate = useNavigate();

  useEffect(() => {
    if (!isLoading && !user && !isDevMode) {
      navigate('/login');
    }
  }, [user, isLoading, navigate, isDevMode]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  return isDevMode || user ? <>{children}</> : null;
}
