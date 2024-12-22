import React, { createContext, useContext, useEffect, useState } from 'react';
import { User, auth } from '../api/client';
import { useNavigate } from 'react-router-dom';

// Development flag to bypass authentication
const BYPASS_AUTH = false;

// Default admin user for development
const DEV_USER: User = {
  id: 'admin',
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

  useEffect(() => {
    if (BYPASS_AUTH) {
      setUser(DEV_USER);
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
  }, [navigate]);

  const login = async (username: string, password: string) => {
    if (BYPASS_AUTH) {
      setUser(DEV_USER);
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
    if (BYPASS_AUTH) {
      setUser(DEV_USER);
      navigate('/');
      return;
    }

    await auth.register({ email, username, password });
    await login(username, password);
  };

  const logout = () => {
    if (BYPASS_AUTH) {
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
  const navigate = useNavigate();

  useEffect(() => {
    if (!isLoading && !user && !BYPASS_AUTH) {
      navigate('/login');
    }
  }, [user, isLoading, navigate]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  return BYPASS_AUTH || user ? <>{children}</> : null;
}
