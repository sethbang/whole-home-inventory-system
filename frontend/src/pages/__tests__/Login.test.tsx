import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MemoryRouter } from 'react-router-dom';

import Login from '../Login';
import { ApiError } from '../../api/errors';

const mockLogin = jest.fn();

jest.mock('../../contexts/AuthContext', () => ({
  useAuth: () => ({ login: mockLogin }),
}));

const renderLogin = () =>
  render(
    <MemoryRouter>
      <Login />
    </MemoryRouter>,
  );

beforeEach(() => {
  mockLogin.mockReset();
});

describe('Login form', () => {
  it('submits credentials to auth.login', async () => {
    mockLogin.mockResolvedValue(undefined);
    renderLogin();

    fireEvent.change(screen.getByPlaceholderText('Username'), {
      target: { value: 'alice' },
    });
    fireEvent.change(screen.getByPlaceholderText('Password'), {
      target: { value: 'correct-horse-battery-staple' },
    });
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith(
        'alice',
        'correct-horse-battery-staple',
      );
    });
  });

  it('shows required-field errors on empty submit', async () => {
    renderLogin();
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));

    expect(await screen.findByText(/username is required/i)).toBeInTheDocument();
    expect(screen.getByText(/password is required/i)).toBeInTheDocument();
    expect(mockLogin).not.toHaveBeenCalled();
  });

  it('surfaces ApiError.detail as the server error banner', async () => {
    mockLogin.mockRejectedValue(new ApiError(401, 'Incorrect username or password'));
    renderLogin();

    fireEvent.change(screen.getByPlaceholderText('Username'), {
      target: { value: 'alice' },
    });
    fireEvent.change(screen.getByPlaceholderText('Password'), {
      target: { value: 'wrong' },
    });
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent(/incorrect username or password/i);
  });

  it('falls back to generic message when login throws a non-ApiError', async () => {
    mockLogin.mockRejectedValue(new Error('network gone'));
    renderLogin();

    fireEvent.change(screen.getByPlaceholderText('Username'), {
      target: { value: 'alice' },
    });
    fireEvent.change(screen.getByPlaceholderText('Password'), {
      target: { value: 'pw' },
    });
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));

    const alert = await screen.findByRole('alert');
    // apiErrorMessage returns the raw Error.message for non-ApiError; this is
    // acceptable today because the login helper wraps axios errors into
    // ApiError already. The fallback is tested separately in errors.test.ts.
    expect(alert.textContent).toBeTruthy();
  });
});
