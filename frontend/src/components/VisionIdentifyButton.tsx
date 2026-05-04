/**
 * Button that gates the whole vision-identify flow:
 *
 *   [Identify with AI] → file picker → POST /api/vision/identify
 *   → (sync) VisionResult | (async) poll useJobPoll → render panel
 *
 * Parent pages mount this and receive the final VisionResult via
 * onResult. The button owns the ephemeral state (pending job, errors);
 * the parent owns the persistent form state.
 */

import { useMemo, useRef, useState } from 'react';
import { useMutation } from '@tanstack/react-query';

import { apiErrorMessage } from '../api/errors';
import { isJobReference, useJobPoll } from '../api/jobs';
import { vision } from '../api/vision';
import type { VisionResult } from '../api/types';

export interface VisionIdentifyButtonProps {
  onResult: (result: VisionResult) => void;
  /** Optional hints handed to the LLM (e.g. existing brand / category). */
  hints?: Record<string, unknown>;
  /** Accepted file types for the picker. */
  accept?: string;
  /** Label on the button. Defaults to 'Identify with AI'. */
  label?: string;
  /** Max files (enforced client-side; server enforces again). */
  maxFiles?: number;
}

export default function VisionIdentifyButton({
  onResult,
  hints,
  accept = 'image/*',
  label = 'Identify with AI',
  maxFiles = 4,
}: VisionIdentifyButtonProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [serverError, setServerError] = useState<string | null>(null);
  const [pendingJobId, setPendingJobId] = useState<string | null>(null);

  const identify = useMutation({
    mutationFn: (files: File[]) => vision.identify({ images: files, hints }),
    onSuccess: (response) => {
      setServerError(null);
      if (isJobReference(response)) {
        setPendingJobId(response.job_id);
        return;
      }
      // After the JobReference check the only remaining union member is
      // VisionResult; TypeScript's narrowing struggles because the
      // generated JobReference marks ``kind`` as optional so the shapes
      // overlap structurally. Cast once, here.
      onResult(response as VisionResult);
    },
    onError: (err) => {
      setServerError(apiErrorMessage(err, 'Vision identification failed'));
    },
  });

  const jobPoll = useJobPoll(pendingJobId);

  useMemo(() => {
    if (!pendingJobId || !jobPoll.data) return;
    const { status, result, error } = jobPoll.data;
    if (status === 'complete' && result) {
      setPendingJobId(null);
      onResult(result as unknown as VisionResult);
    } else if (status === 'failed' || status === 'not_found') {
      setPendingJobId(null);
      setServerError(error ?? 'Vision job failed');
    }
  }, [jobPoll.data, pendingJobId, onResult]);

  const handleFiles = (event: React.ChangeEvent<HTMLInputElement>) => {
    const picked = Array.from(event.target.files ?? []).slice(0, maxFiles);
    event.target.value = ''; // allow re-picking the same file
    if (picked.length === 0) return;
    setServerError(null);
    identify.mutate(picked);
  };

  const working = identify.isPending || pendingJobId !== null;

  return (
    <div className="flex flex-col items-start gap-2">
      <input
        ref={fileInputRef}
        type="file"
        accept={accept}
        multiple
        onChange={handleFiles}
        className="sr-only"
        aria-label="Select photos to identify"
      />
      <button
        type="button"
        onClick={() => fileInputRef.current?.click()}
        disabled={working}
        className="inline-flex items-center gap-2 rounded-md border border-primary bg-primary-subtle px-3 py-1.5 text-sm font-medium text-primary hover:bg-primary-subtle-hover disabled:opacity-60"
      >
        {working ? (
          <>
            <span
              aria-hidden="true"
              className="h-3 w-3 animate-spin rounded-full border-2 border-primary border-t-transparent"
            />
            Identifying…
          </>
        ) : (
          label
        )}
      </button>
      {serverError && (
        <p role="alert" className="text-xs text-danger">
          {serverError}
        </p>
      )}
    </div>
  );
}
