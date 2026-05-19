/**
 * useVisionPricingChain (v3.3)
 *
 * Owns the "vision → pricing" orchestration extracted from
 * ``AddItem.tsx``. After the user applies a vision suggestion the page
 * calls ``estimateFromMetadata(metadata)`` to fetch a resale-value
 * estimate so the "current value" field can be pre-filled.
 *
 * The pricing endpoint returns a discriminated union:
 *   - ``JobReference`` — the worker enqueued the lookup; poll via
 *     ``useJobPoll`` until the envelope arrives under ``data.result``.
 *   - ``PriceEstimateEnvelope`` — answered inline (cache hit / sync
 *     fallback).
 *
 * Stale-response guard
 * --------------------
 * Each call to ``estimateFromMetadata`` bumps a generation counter held
 * in a ref. The mutation ``onSuccess`` callback and the job-resolution
 * effect both capture the generation that was current when their
 * request started; a captured generation that no longer matches the ref
 * is a superseded request and its result is dropped. This prevents a
 * slow first response from overwriting a newer one.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { useMutation } from '@tanstack/react-query';

import { isJobReference, useJobPoll } from '../api/jobs';
import { pricing } from '../api/pricing';
import type { PriceEstimateEnvelope } from '../api/types';

export interface UseVisionPricingChain {
  /** Latest (non-superseded) resale-value envelope, or null. */
  priceEnvelope: PriceEstimateEnvelope | null;
  /** True while a request is pending or a job is still polling. */
  isPricing: boolean;
  /** Start a metadata-based pricing lookup. */
  estimateFromMetadata: (metadata: Record<string, unknown>) => void;
}

export function useVisionPricingChain(): UseVisionPricingChain {
  const [priceEnvelope, setPriceEnvelope] =
    useState<PriceEstimateEnvelope | null>(null);
  const [priceJobId, setPriceJobId] = useState<string | null>(null);

  // Generation counter. Incremented on every new request; both the
  // mutation onSuccess and the job-resolution effect capture the value
  // that was current when their request began and bail if it has since
  // advanced.
  const generationRef = useRef(0);
  // Generation that owns the in-flight job (set when a JobReference is
  // received) so the poll effect can validate against it.
  const jobGenerationRef = useRef(0);

  const estimatePriceFromMetadata = useMutation({
    mutationFn: (params: {
      metadata: Record<string, unknown>;
      generation: number;
    }) => pricing.estimate({ metadata: params.metadata }),
    onSuccess: (response, variables) => {
      // Drop a response whose request has been superseded.
      if (variables.generation !== generationRef.current) return;
      if (isJobReference(response)) {
        jobGenerationRef.current = variables.generation;
        setPriceJobId(response.job_id);
        return;
      }
      setPriceEnvelope(response as PriceEstimateEnvelope);
    },
  });

  const priceJob = useJobPoll(priceJobId);
  useEffect(() => {
    if (!priceJobId || !priceJob.data) return;
    const { status, result } = priceJob.data;
    const stale = jobGenerationRef.current !== generationRef.current;
    if (status === 'complete' && result) {
      setPriceJobId(null);
      if (!stale) {
        setPriceEnvelope(result as unknown as PriceEstimateEnvelope);
      }
    } else if (status === 'failed' || status === 'not_found') {
      setPriceJobId(null);
    }
  }, [priceJob.data, priceJobId]);

  const estimateFromMetadata = useCallback(
    (metadata: Record<string, unknown>) => {
      const generation = generationRef.current + 1;
      generationRef.current = generation;
      estimatePriceFromMetadata.mutate({ metadata, generation });
    },
    [estimatePriceFromMetadata],
  );

  return {
    priceEnvelope,
    isPricing: estimatePriceFromMetadata.isPending || priceJobId !== null,
    estimateFromMetadata,
  };
}
