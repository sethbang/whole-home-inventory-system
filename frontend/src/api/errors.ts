/**
 * Typed API error model.
 *
 * Pages used to `catch (error: any)` and probe ``error.response?.data?.detail``,
 * which is why roughly half of the 47 pre-existing ESLint warnings were
 * ``@typescript-eslint/no-explicit-any``. ApiError gives the error shape a
 * name so callers narrow via ``isApiError`` and the lint bar goes up.
 *
 * The axios response interceptor in ``client.ts`` normalizes every network
 * failure into an ApiError before rejecting, so hooks and components can
 * trust the type.
 */

export class ApiError extends Error {
  readonly statusCode: number;
  readonly detail: string;
  readonly fieldErrors?: Record<string, string[]>;

  constructor(
    statusCode: number,
    detail: string,
    fieldErrors?: Record<string, string[]>,
  ) {
    super(detail);
    this.name = 'ApiError';
    this.statusCode = statusCode;
    this.detail = detail;
    this.fieldErrors = fieldErrors;
  }
}

export function isApiError(e: unknown): e is ApiError {
  return e instanceof ApiError;
}

/**
 * Best-effort extraction of a human-readable message from an unknown error.
 * Use when you need to surface a fallback string to the user without
 * caring what the underlying error type is.
 */
export function apiErrorMessage(e: unknown, fallback = 'Something went wrong'): string {
  if (isApiError(e)) return e.detail;
  if (e instanceof Error) return e.message;
  return fallback;
}
