import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';

import { useAuth } from '../contexts/useAuth';
import { apiErrorMessage } from '../api/errors';
import { type RegisterFormValues, registerSchema } from './Register.schema';

export default function Register() {
  const { register: registerUser } = useAuth();
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RegisterFormValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      email: '',
      username: '',
      password: '',
      confirmPassword: '',
    },
  });

  const onSubmit = async (values: RegisterFormValues) => {
    setServerError(null);
    try {
      await registerUser(values.email, values.username, values.password);
    } catch (err) {
      setServerError(apiErrorMessage(err, 'Registration failed'));
    }
  };

  const fieldErrorClass = (hasError: boolean, position: 'top' | 'middle' | 'bottom') => {
    const radius =
      position === 'top'
        ? 'rounded-t-md'
        : position === 'bottom'
          ? 'rounded-b-md'
          : '';
    const border = hasError ? 'border-red-300' : 'border-gray-300';
    return `appearance-none rounded-none relative block w-full px-3 py-2 border ${border} placeholder-gray-500 text-gray-900 ${radius} focus:outline-none focus:ring-primary-500 focus:border-primary-500 focus:z-10 sm:text-sm`;
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <h2 className="mt-6 text-center text-3xl font-bold tracking-tight text-gray-900">
            Create your account
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            Or{' '}
            <Link
              to="/login"
              className="font-medium text-primary-600 hover:text-primary-500"
            >
              sign in to your account
            </Link>
          </p>
        </div>
        <form className="mt-8 space-y-6" onSubmit={handleSubmit(onSubmit)} noValidate>
          {serverError && (
            <div role="alert" className="rounded-md bg-red-50 p-4">
              <div className="text-sm text-red-700">{serverError}</div>
            </div>
          )}
          <div className="rounded-md shadow-sm -space-y-px">
            <div>
              <label htmlFor="email" className="sr-only">
                Email address
              </label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                aria-invalid={errors.email ? 'true' : 'false'}
                className={fieldErrorClass(!!errors.email, 'top')}
                placeholder="Email address"
                {...register('email')}
              />
              {errors.email && (
                <div className="text-red-500 text-xs mt-1">{errors.email.message}</div>
              )}
            </div>
            <div>
              <label htmlFor="username" className="sr-only">
                Username
              </label>
              <input
                id="username"
                type="text"
                autoComplete="username"
                aria-invalid={errors.username ? 'true' : 'false'}
                className={fieldErrorClass(!!errors.username, 'middle')}
                placeholder="Username"
                {...register('username')}
              />
              {errors.username && (
                <div className="text-red-500 text-xs mt-1">
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
                autoComplete="new-password"
                aria-invalid={errors.password ? 'true' : 'false'}
                className={fieldErrorClass(!!errors.password, 'middle')}
                placeholder="Password"
                {...register('password')}
              />
              {errors.password && (
                <div className="text-red-500 text-xs mt-1">
                  {errors.password.message}
                </div>
              )}
            </div>
            <div>
              <label htmlFor="confirmPassword" className="sr-only">
                Confirm Password
              </label>
              <input
                id="confirmPassword"
                type="password"
                autoComplete="new-password"
                aria-invalid={errors.confirmPassword ? 'true' : 'false'}
                className={fieldErrorClass(!!errors.confirmPassword, 'bottom')}
                placeholder="Confirm Password"
                {...register('confirmPassword')}
              />
              {errors.confirmPassword && (
                <div className="text-red-500 text-xs mt-1">
                  {errors.confirmPassword.message}
                </div>
              )}
            </div>
          </div>

          <div>
            <button
              type="submit"
              disabled={isSubmitting}
              className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-60"
            >
              {isSubmitting ? 'Creating account...' : 'Create account'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
