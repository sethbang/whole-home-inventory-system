import { ApiError, apiErrorMessage, isApiError } from '../errors';

describe('ApiError', () => {
  it('carries statusCode and detail', () => {
    const err = new ApiError(422, 'validation failed');
    expect(err.statusCode).toBe(422);
    expect(err.detail).toBe('validation failed');
    expect(err.message).toBe('validation failed');
    expect(err.name).toBe('ApiError');
  });

  it('optionally carries field errors', () => {
    const err = new ApiError(422, 'bad input', { name: ['required'] });
    expect(err.fieldErrors).toEqual({ name: ['required'] });
  });
});

describe('isApiError', () => {
  it('returns true for ApiError instances', () => {
    expect(isApiError(new ApiError(500, 'oops'))).toBe(true);
  });

  it('returns false for plain Errors', () => {
    expect(isApiError(new Error('plain'))).toBe(false);
  });

  it('returns false for non-Error values', () => {
    expect(isApiError(null)).toBe(false);
    expect(isApiError(undefined)).toBe(false);
    expect(isApiError('a string')).toBe(false);
    expect(isApiError({ statusCode: 500, detail: 'spoofed' })).toBe(false);
  });

  it('narrows the type in a conditional', () => {
    const e: unknown = new ApiError(404, 'not found');
    if (isApiError(e)) {
      // Inside the guard, e.statusCode is accessible without casting.
      expect(e.statusCode).toBe(404);
    } else {
      throw new Error('narrowing guard failed');
    }
  });
});

describe('apiErrorMessage', () => {
  it('returns detail for ApiError', () => {
    expect(apiErrorMessage(new ApiError(500, 'db gone'))).toBe('db gone');
  });

  it('returns message for plain Error', () => {
    expect(apiErrorMessage(new Error('boom'))).toBe('boom');
  });

  it('returns fallback for unknown', () => {
    expect(apiErrorMessage(null)).toBe('Something went wrong');
    expect(apiErrorMessage(null, 'custom')).toBe('custom');
  });
});
