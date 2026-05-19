/**
 * Test tab — tiered connection checks for the configured LLM provider:
 * a token-free quick test and a token-spending end-to-end vision test.
 */

import type { LLMTestResponse, LLMVisionTestResponse } from '../../api/types';
import TestResultPanel from './TestResultPanel';

interface TestTabProps {
  quickResult: LLMTestResponse | null;
  quickIsPending: boolean;
  quickError: string | null;
  onQuick: () => void;
  visionResult: LLMVisionTestResponse | null;
  visionIsPending: boolean;
  visionError: string | null;
  onVision: () => void;
}

export default function TestTab({
  quickResult,
  quickIsPending,
  quickError,
  onQuick,
  visionResult,
  visionIsPending,
  visionError,
  onVision,
}: TestTabProps) {
  return (
    <div className="space-y-6">
      <section>
        <h3 className="text-sm font-medium text-fg">Quick test</h3>
        <p className="text-sm text-muted mt-1">
          Lists the provider's models and confirms the configured Default,
          Vision, and Pricing models all exist. Doesn't spend tokens.
        </p>
        <button
          type="button"
          onClick={onQuick}
          disabled={quickIsPending}
          className="mt-2 inline-flex items-center px-3 py-1.5 border border-line-strong text-sm font-medium rounded-md text-muted bg-surface-raised hover:bg-surface-muted disabled:opacity-50"
        >
          {quickIsPending ? 'Running…' : 'Run quick test'}
        </button>
        {quickError && (
          <pre className="mt-2 text-xs whitespace-pre-wrap rounded-md bg-danger-subtle text-danger p-3">
            {quickError}
          </pre>
        )}
        {quickResult && <TestResultPanel result={quickResult} kind="quick" />}
      </section>

      <section className="border-t pt-5">
        <h3 className="text-sm font-medium text-fg">Run vision test</h3>
        <p className="text-sm text-muted mt-1">
          Sends a tiny embedded test image through the configured Vision
          model with a strict JSON schema. Costs a small amount of tokens
          but proves end-to-end vision + strict-schema support.
        </p>
        <button
          type="button"
          onClick={onVision}
          disabled={visionIsPending}
          className="mt-2 inline-flex items-center px-3 py-1.5 border border-line-strong text-sm font-medium rounded-md text-muted bg-surface-raised hover:bg-surface-muted disabled:opacity-50"
        >
          {visionIsPending ? 'Running…' : 'Run vision test'}
        </button>
        {visionError && (
          <pre className="mt-2 text-xs whitespace-pre-wrap rounded-md bg-danger-subtle text-danger p-3">
            {visionError}
          </pre>
        )}
        {visionResult && (
          <TestResultPanel result={visionResult} kind="vision" />
        )}
      </section>
    </div>
  );
}
