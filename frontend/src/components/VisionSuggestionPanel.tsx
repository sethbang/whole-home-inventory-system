/**
 * Panel that renders a VisionSuggestion with per-field checkboxes so
 * the user can accept selectively. "Apply selected" calls the
 * onApply callback with just the checked fields; unchecked values
 * leave the caller's existing form state untouched.
 *
 * All AI-sourced values are labelled with a small "AI" chip so
 * downstream UI can visually distinguish edited-by-user vs
 * inferred-from-vision.
 */

import { useMemo, useState } from 'react';

import type { VisionSuggestion } from '../api/types';

export interface VisionSuggestionPanelProps {
  suggestion: VisionSuggestion;
  provider?: string;
  model?: string;
  /** Called with only the fields the user checked + whose AI value is non-empty. */
  onApply: (accepted: Partial<VisionSuggestion>) => void;
  onDismiss: () => void;
}

// Fields we surface as rows. Order matters — most-commonly-useful
// first so users can click through quickly.
const FIELD_ORDER: Array<keyof VisionSuggestion> = [
  'name',
  'brand',
  'model_number',
  'category',
  'condition',
  'year',
  'color',
  'dimensions',
  'description',
  'serial_number',
  'suggested_tags',
];

function isNonEmptyValue(value: unknown): boolean {
  if (value == null) return false;
  if (typeof value === 'string') return value.trim().length > 0;
  if (Array.isArray(value)) return value.length > 0;
  if (typeof value === 'object') return Object.keys(value as object).length > 0;
  return true;
}

function renderValue(value: unknown): string {
  if (value == null) return '—';
  if (Array.isArray(value)) return value.join(', ');
  return String(value);
}

export default function VisionSuggestionPanel({
  suggestion,
  provider,
  model,
  onApply,
  onDismiss,
}: VisionSuggestionPanelProps) {
  // Pre-select every field that has a non-empty value — that's
  // almost always what the user wants. Unchecks are explicit opt-out.
  const populated = useMemo(
    () =>
      FIELD_ORDER.filter((field) =>
        isNonEmptyValue(suggestion[field] as unknown),
      ),
    [suggestion],
  );
  const [selected, setSelected] = useState<Set<string>>(
    () => new Set(populated as string[]),
  );

  const toggle = (field: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(field)) next.delete(field);
      else next.add(field);
      return next;
    });
  };

  const handleApply = () => {
    const accepted: Partial<VisionSuggestion> = {};
    for (const field of populated) {
      if (selected.has(field as string)) {
        // Typed-unsafe but the keys come from FIELD_ORDER; each is a real field of VisionSuggestion.
        (accepted as Record<string, unknown>)[field as string] =
          suggestion[field];
      }
    }
    onApply(accepted);
  };

  const confidencePct = Math.round((suggestion.confidence ?? 0) * 100);
  const confidenceTone =
    confidencePct >= 80
      ? 'bg-success-subtle text-success'
      : confidencePct >= 50
      ? 'bg-warning-subtle text-warning'
      : 'bg-danger-subtle text-danger';

  return (
    <section
      aria-labelledby="vision-panel-title"
      className="rounded-lg border border-primary-subtle bg-primary-subtle p-4"
    >
      <header className="flex items-center justify-between">
        <h3 id="vision-panel-title" className="text-sm font-semibold text-primary">
          AI suggestions
        </h3>
        <div className="flex items-center gap-2">
          <span
            className={`rounded px-2 py-0.5 text-xs font-medium ${confidenceTone}`}
            aria-label={`Overall confidence ${confidencePct}%`}
          >
            {confidencePct}% confident
          </span>
          <button
            type="button"
            onClick={onDismiss}
            className="text-sm text-subtle hover:text-muted"
          >
            Dismiss
          </button>
        </div>
      </header>

      {provider && model && (
        <p className="mt-1 text-xs text-muted">
          {provider} · {model}
        </p>
      )}

      {suggestion.warnings && suggestion.warnings.length > 0 && (
        <ul
          aria-label="warnings"
          className="mt-3 list-disc space-y-0.5 pl-5 text-sm text-warning"
        >
          {suggestion.warnings.map((warning, idx) => (
            <li key={idx}>{warning}</li>
          ))}
        </ul>
      )}

      {populated.length === 0 ? (
        <p className="mt-4 text-sm text-muted">
          The model returned no confident suggestions. Try another photo?
        </p>
      ) : (
        <ul className="mt-4 space-y-2">
          {populated.map((field) => {
            const fieldKey = field as string;
            return (
              <li key={fieldKey} className="flex items-start gap-3">
                <input
                  id={`vision-apply-${fieldKey}`}
                  type="checkbox"
                  checked={selected.has(fieldKey)}
                  onChange={() => toggle(fieldKey)}
                  className="mt-1 rounded border-line-strong text-primary focus:ring-primary"
                />
                <label
                  htmlFor={`vision-apply-${fieldKey}`}
                  className="flex-1 text-sm"
                >
                  <span className="font-medium text-fg">{fieldKey}</span>
                  <span className="ml-2 text-muted">
                    {renderValue(suggestion[field])}
                  </span>
                </label>
              </li>
            );
          })}
        </ul>
      )}

      <div className="mt-4 flex justify-end gap-2">
        <button
          type="button"
          onClick={onDismiss}
          className="rounded-md border border-line-strong bg-surface-raised px-3 py-1.5 text-sm font-medium text-muted hover:bg-surface-muted"
        >
          Cancel
        </button>
        <button
          type="button"
          onClick={handleApply}
          disabled={selected.size === 0}
          className="rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-white hover:bg-primary-hover disabled:opacity-60"
        >
          Apply {selected.size} field{selected.size === 1 ? '' : 's'}
        </button>
      </div>
    </section>
  );
}
