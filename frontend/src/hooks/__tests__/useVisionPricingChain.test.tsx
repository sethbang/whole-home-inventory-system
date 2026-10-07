import React from 'react';
import { renderHook, act, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import { useVisionPricingChain } from '../useVisionPricingChain';
import { pricing } from '../../api/pricing';
import { apiClient } from '../../api/http';
import type { JobDetail } from '../../api/jobs';
import type { PriceEstimateEnvelope } from '../../api/types';

vi.mock('../../api/pricing', () => ({
  pricing: {
    estimate: vi.fn(),
    refresh: vi.fn(),
    getCached: vi.fn(),
  },
}));

// useJobPoll (kept real — task forbids modifying it) calls jobs.get which
// in turn hits apiClient.get. Mock the http client so the whole real
// poll path runs against controllable responses.
vi.mock('../../api/http', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

const estimateMock = pricing.estimate as ReturnType<typeof vi.fn>;
const apiGetMock = apiClient.get as ReturnType<typeof vi.fn>;

/** Stub the next `GET /api/jobs/:id` poll with a JobDetail payload. */
const stubJobGet = (detail: JobDetail) => {
  apiGetMock.mockResolvedValue({ data: detail });
};

/** Build a minimal envelope; only `tag` matters for assertions. */
const envelope = (tag: string): PriceEstimateEnvelope =>
  ({
    estimate: {
      currency: 'USD',
      low: 1,
      median: 2,
      high: 3,
      confidence: 'low',
      sample_size: 0,
      sources: [],
      // marker used by tests to distinguish responses
      generated_at: tag,
    },
    cached: false,
    stale: false,
  }) as unknown as PriceEstimateEnvelope;

const tagOf = (env: PriceEstimateEnvelope | null): string | undefined =>
  (env?.estimate as { generated_at?: string } | undefined)?.generated_at;

const makeWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );
  };
};

beforeEach(() => {
  vi.clearAllMocks();
});

describe('useVisionPricingChain', () => {
  it('resolves the inline-envelope happy path', async () => {
    estimateMock.mockResolvedValue(envelope('A'));

    const { result } = renderHook(() => useVisionPricingChain(), {
      wrapper: makeWrapper(),
    });

    act(() => {
      result.current.estimateFromMetadata({ brand: 'Acme', model_number: 'X' });
    });

    await waitFor(() => expect(result.current.priceEnvelope).not.toBeNull());
    expect(tagOf(result.current.priceEnvelope)).toBe('A');
    expect(result.current.isPricing).toBe(false);
  });

  it('resolves the job-reference path via polling', async () => {
    estimateMock.mockResolvedValue({ kind: 'job', job_id: 'job-1' });
    stubJobGet({
      job_id: 'job-1',
      status: 'complete',
      result: envelope('JOB') as unknown as Record<string, unknown>,
    });

    const { result } = renderHook(() => useVisionPricingChain(), {
      wrapper: makeWrapper(),
    });

    act(() => {
      result.current.estimateFromMetadata({ brand: 'Acme', model_number: 'X' });
    });

    await waitFor(() => expect(result.current.priceEnvelope).not.toBeNull());
    expect(tagOf(result.current.priceEnvelope)).toBe('JOB');
  });

  it('ignores a stale slow first response when a newer one already landed', async () => {
    // Request A: a promise we control and resolve LATE.
    let resolveA!: (v: PriceEstimateEnvelope) => void;
    const promiseA = new Promise<PriceEstimateEnvelope>((res) => {
      resolveA = res;
    });
    // Request B: resolves immediately.
    estimateMock
      .mockReturnValueOnce(promiseA)
      .mockResolvedValueOnce(envelope('B'));

    const { result } = renderHook(() => useVisionPricingChain(), {
      wrapper: makeWrapper(),
    });

    // Fire A, then B.
    act(() => {
      result.current.estimateFromMetadata({ brand: 'Acme', model_number: 'A' });
    });
    act(() => {
      result.current.estimateFromMetadata({ brand: 'Acme', model_number: 'B' });
    });

    // B lands first.
    await waitFor(() => expect(tagOf(result.current.priceEnvelope)).toBe('B'));

    // Now the slow A response arrives — it must NOT clobber B.
    await act(async () => {
      resolveA(envelope('A'));
      await promiseA;
    });

    // Give any pending effects a chance to (incorrectly) run.
    await new Promise((r) => setTimeout(r, 20));

    expect(tagOf(result.current.priceEnvelope)).toBe('B');
  });
});
