import type {
  AuthResponse,
  LoginCredentials,
  RegisterData,
  User,
} from './types';
import { apiClient } from './http';
import { logger } from '../lib/logger';

export const auth = {
  login: async (credentials: LoginCredentials): Promise<AuthResponse> => {
    logger.debug('auth.login attempt', { username: credentials.username });

    const params = new URLSearchParams();
    params.append('grant_type', 'password');
    params.append('username', credentials.username);
    params.append('password', credentials.password);

    const response = await apiClient.post<AuthResponse>('/api/token', params, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });

    logger.debug('auth.login succeeded', { username: credentials.username });
    return response.data;
  },

  register: async (data: RegisterData): Promise<User> => {
    const response = await apiClient.post<User>('/api/register', data);
    return response.data;
  },

  getCurrentUser: async (): Promise<User> => {
    const response = await apiClient.get<User>('/api/users/me');
    return response.data;
  },
};

export type { AuthResponse, LoginCredentials, RegisterData, User };
