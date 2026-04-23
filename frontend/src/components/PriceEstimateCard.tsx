/**
 * Render a PriceEstimateEnvelope with a low/median/high band,
 * source citations, and an optional "Refresh" / "Apply median"
 * action pair. The parent owns the estimate lifecycle — this
 * component is presentation plus wired buttons.
 */

import type { PriceEstimateEnvelope } from '../api/types';

export interface PriceEstimateCardProps {
  envelope: PriceEstimateEnvelope;
  /** If provided, Refresh button fires this handler. */
  onRefresh?: () => void;
  /** If provided, "Apply median as current value" fires with median. */
  onApplyMedian?: (median: number) => void;
  /** True while a refresh is in flight. */
  refreshing?: boolean;
}

function formatUsd(n: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(n);
}

function formatDate(iso: string | null | undefined): string {
  if (!iso) return '';
  try {
    return new Intl.DateTimeFormat('en-US', {
      dateStyle: 'medium',
      timeStyle: 'short',
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

export default function PriceEstimateCard({
  envelope,
  onRefresh,
  onApplyMedian,
  refreshing,
}: PriceEstimateCardProps) {
  const { estimate } = envelope;
  const confidencePct = Math.round((estimate.confidence ?? 0) * 100);
  const confidenceTone =
    confidencePct >= 75
      ? 'bg-green-100 text-green-800'
      : confidencePct >= 50
      ? 'bg-yellow-100 text-yellow-800'
      : 'bg-red-100 text-red-800';

  return (
    <section
      aria-labelledby="price-estimate-title"
      className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm"
    >
      <header className="flex items-start justify-between gap-2">
        <div>
          <h3
            id="price-estimate-title"
            className="text-sm font-semibold text-gray-900"
          >
            Estimated resale value
          </h3>
          <p className="text-xs text-gray-500">
            {envelope.provider} · {formatDate(envelope.queried_at)}
            {envelope.cache_hit && ' · cached'}
          </p>
        </div>
        <span
          className={`rounded px-2 py-0.5 text-xs font-medium ${confidenceTone}`}
          aria-label={`Confidence ${confidencePct}%`}
        >
          {confidencePct}% confident
        </span>
      </header>

      <div className="mt-3 grid grid-cols-3 gap-2 text-center">
        <div className="rounded bg-gray-50 p-2">
          <div className="text-xs text-gray-500">low</div>
          <div className="text-lg font-semibold text-gray-800">
            {formatUsd(estimate.low)}
          </div>
        </div>
        <div className="rounded bg-primary-subtle p-2">
          <div className="text-xs text-primary">median</div>
          <div className="text-lg font-semibold text-primary">
            {formatUsd(estimate.median)}
          </div>
        </div>
        <div className="rounded bg-gray-50 p-2">
          <div className="text-xs text-gray-500">high</div>
          <div className="text-lg font-semibold text-gray-800">
            {formatUsd(estimate.high)}
          </div>
        </div>
      </div>

      <p className="mt-2 text-xs text-gray-600">
        Based on {estimate.sample_count} comparable
        {estimate.sample_count === 1 ? '' : 's'}.
      </p>

      {estimate.sources && estimate.sources.length > 0 && (
        <details className="mt-2 text-sm">
          <summary className="cursor-pointer text-xs text-primary hover:underline">
            View comparables
          </summary>
          <ul className="mt-2 space-y-1 text-xs">
            {estimate.sources.slice(0, 6).map((source, idx) => (
              <li key={idx} className="flex justify-between gap-2">
                <a
                  href={source.url}
                  target="_blank"
                  rel="noreferrer noopener"
                  className="truncate text-primary hover:underline"
                  title={source.title}
                >
                  {source.title}
                </a>
                <span className="whitespace-nowrap text-gray-700">
                  {formatUsd(source.price)}
                  {source.condition ? ` · ${source.condition}` : ''}
                </span>
              </li>
            ))}
          </ul>
        </details>
      )}

      {(onRefresh || onApplyMedian) && (
        <div className="mt-3 flex flex-wrap gap-2">
          {onRefresh && (
            <button
              type="button"
              onClick={onRefresh}
              disabled={refreshing}
              className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-60"
            >
              {refreshing ? 'Refreshing…' : 'Refresh'}
            </button>
          )}
          {onApplyMedian && (
            <button
              type="button"
              onClick={() => onApplyMedian(estimate.median)}
              className="rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-white hover:bg-primary-hover"
            >
              Apply median as current value
            </button>
          )}
        </div>
      )}
    </section>
  );
}
