/**
 * Error boundary components for WHIS.
 *
 * Two flavors:
 *
 *   - ``RouteErrorBoundary`` — designed for React Router v7's
 *     ``errorElement`` slot. Reads ``useRouteError`` to render a fallback
 *     for both loader errors and render-time throws.
 *
 *   - ``SectionErrorBoundary`` — wraps a risky subtree (barcode scanner,
 *     camera capture, etc.) using ``react-error-boundary``. If the subtree
 *     throws, the rest of the page keeps rendering; the broken section
 *     shows a compact fallback with a "Try again" button.
 *
 * Prior to v2.3 any uncaught React error escaped all the way up and left
 * the user with a blank page. These components make failures recoverable
 * (or at least localized) without wiring error-handling into every
 * component.
 */

import { ReactNode } from 'react';
import {
  ErrorBoundary as ReactErrorBoundary,
  FallbackProps,
} from 'react-error-boundary';
import { isRouteErrorResponse, useRouteError } from 'react-router-dom';

import { ApiError, isApiError } from '../api/errors';
import { logger } from '../lib/logger';

// ---------------------------------------------------------------------------
// Route-level
// ---------------------------------------------------------------------------

export function RouteErrorBoundary() {
  const error = useRouteError();
  logger.error('RouteErrorBoundary caught', error);

  let title = 'Something went wrong';
  let detail = 'An unexpected error happened. Try reloading the page.';

  if (isRouteErrorResponse(error)) {
    title = `${error.status} ${error.statusText || ''}`.trim();
    detail = typeof error.data === 'string' ? error.data : detail;
  } else if (isApiError(error)) {
    title = apiErrorTitle(error);
    detail = error.detail;
  } else if (error instanceof Error) {
    detail = error.message;
  }

  return (
    <div className="flex min-h-[50vh] flex-col items-center justify-center px-4">
      <div className="max-w-md rounded-lg border border-red-200 bg-red-50 p-6 text-center">
        <h1 className="mb-2 text-lg font-semibold text-red-800">{title}</h1>
        <p className="mb-4 text-sm text-red-700">{detail}</p>
        <button
          onClick={() => window.location.reload()}
          className="rounded bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700"
        >
          Reload
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Section-level
// ---------------------------------------------------------------------------

interface SectionBoundaryProps {
  /** Short label shown in the fallback ("Barcode scanner", "Image gallery", ...). */
  label: string;
  children: ReactNode;
  /** Optional custom fallback override. */
  fallback?: (props: FallbackProps) => ReactNode;
  /** Optional reset trigger — any value change forces the boundary to re-render children. */
  resetKey?: unknown;
}

function DefaultSectionFallback({
  label,
  error,
  resetErrorBoundary,
}: FallbackProps & { label: string }) {
  const detail = isApiError(error)
    ? error.detail
    : error instanceof Error
      ? error.message
      : 'Unexpected error';
  return (
    <div
      role="alert"
      className="rounded border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900"
    >
      <p className="font-semibold">{label} failed to load</p>
      <p className="mt-1 text-xs">{detail}</p>
      <button
        onClick={resetErrorBoundary}
        className="mt-2 rounded border border-amber-500 bg-amber-100 px-2 py-1 text-xs font-medium text-amber-900 hover:bg-amber-200"
      >
        Try again
      </button>
    </div>
  );
}

export function SectionErrorBoundary({
  label,
  children,
  fallback,
  resetKey,
}: SectionBoundaryProps) {
  const renderFallback =
    fallback ??
    ((props: FallbackProps) => (
      <DefaultSectionFallback {...props} label={label} />
    ));

  return (
    <ReactErrorBoundary
      fallbackRender={renderFallback}
      onError={(error: unknown) =>
        logger.error(`SectionErrorBoundary(${label})`, error)
      }
      resetKeys={resetKey !== undefined ? [resetKey] : undefined}
    >
      {children}
    </ReactErrorBoundary>
  );
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function apiErrorTitle(err: ApiError): string {
  if (err.statusCode === 401) return 'You need to sign in';
  if (err.statusCode === 403) return "You don't have access to this";
  if (err.statusCode === 404) return 'Not found';
  if (err.statusCode === 429) return 'Too many requests';
  if (err.statusCode >= 500) return 'Server error';
  return 'Something went wrong';
}
