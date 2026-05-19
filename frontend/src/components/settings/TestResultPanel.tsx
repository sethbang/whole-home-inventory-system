/**
 * Renders the pass/fail result of a quick or vision connection test.
 */

import type { LLMTestResponse, LLMVisionTestResponse } from '../../api/types';

export default function TestResultPanel({
  result,
  kind,
}: {
  result: LLMTestResponse | LLMVisionTestResponse;
  kind: 'quick' | 'vision';
}) {
  const ok = result.ok;
  return (
    <div
      className={`mt-3 rounded-md p-3 text-sm ${
        ok ? 'bg-success-subtle text-success' : 'bg-danger-subtle text-danger'
      }`}
    >
      <div className="font-medium">
        {ok ? '✓ Passed' : '✗ Failed'} — {result.model}
      </div>
      {result.detail && <div className="mt-1 text-xs">{result.detail}</div>}
      {kind === 'quick' && 'checks' in result && result.checks && (
        <pre className="mt-2 text-xs bg-surface-raised/50 rounded p-2 whitespace-pre-wrap">
          {JSON.stringify(result.checks, null, 2)}
        </pre>
      )}
      {kind === 'vision' && 'parsed_response' in result && result.parsed_response && (
        <pre className="mt-2 text-xs bg-surface-raised/50 rounded p-2 whitespace-pre-wrap">
          {JSON.stringify(result.parsed_response, null, 2)}
        </pre>
      )}
      {kind === 'vision' && 'usage' in result && result.usage && (
        <p className="mt-1 text-xs">
          Tokens in: {Number(result.usage.prompt_tokens ?? 0)} · out:{' '}
          {Number(result.usage.completion_tokens ?? 0)} · cost: $
          {(result.cost_usd ?? 0).toFixed(6)}
        </p>
      )}
    </div>
  );
}
