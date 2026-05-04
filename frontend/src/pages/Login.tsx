import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';

import { useAuth } from '../contexts/useAuth';
import { apiErrorMessage } from '../api/errors';
import { type LoginFormValues, loginSchema } from './Login.schema';

export default function Login() {
  const { login } = useAuth();
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { username: '', password: '' },
  });

  const onSubmit = async (values: LoginFormValues) => {
    setServerError(null);
    try {
      await login(values.username, values.password);
    } catch (err) {
      setServerError(apiErrorMessage(err, 'Invalid username or password'));
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-surface-muted py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <h2 className="mt-6 text-center text-3xl font-bold tracking-tight text-fg">
            Sign in to WHIS
          </h2>
          <p className="mt-2 text-center text-sm text-muted">
            Or{' '}
            <Link
              to="/register"
              className="font-medium text-primary hover:text-primary"
            >
              create a new account
            </Link>
          </p>
        </div>
        <form className="mt-8 space-y-6" onSubmit={handleSubmit(onSubmit)} noValidate>
          {serverError && (
            <div role="alert" className="rounded-md bg-danger-subtle p-4">
              <div className="text-sm text-danger">{serverError}</div>
            </div>
          )}
          <div className="rounded-md shadow-sm -space-y-px">
            <div>
              <label htmlFor="username" className="sr-only">
                Username
              </label>
              <input
                id="username"
                type="text"
                autoComplete="username"
                aria-invalid={errors.username ? 'true' : 'false'}
                className="appearance-none rounded-none relative block w-full px-3 py-2 border border-line-strong placeholder-subtle text-fg rounded-t-md focus:outline-none focus:ring-primary focus:border-primary focus:z-10 sm:text-sm"
                placeholder="Username"
                {...register('username')}
              />
              {errors.username && (
                <div className="text-danger text-xs mt-1">
                  {errors.username.message}
                </div>
              )}
            </div>
            <div>
              <label htmlFor="password" className="sr-only">
                Password
              </label>
              <input
                id="password"
                type="password"
                autoComplete="current-password"
                aria-invalid={errors.password ? 'true' : 'false'}
                className="appearance-none rounded-none relative block w-full px-3 py-2 border border-line-strong placeholder-subtle text-fg rounded-b-md focus:outline-none focus:ring-primary focus:border-primary focus:z-10 sm:text-sm"
                placeholder="Password"
                {...register('password')}
              />
              {errors.password && (
                <div className="text-danger text-xs mt-1">
                  {errors.password.message}
                </div>
              )}
            </div>
          </div>

          <div>
            <button
              type="submit"
              disabled={isSubmitting}
              className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-primary hover:bg-primary-hover focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary disabled:opacity-60"
            >
              {isSubmitting ? 'Signing in...' : 'Sign in'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
