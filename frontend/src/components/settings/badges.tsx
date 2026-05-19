/**
 * Small presentational tags used across the Settings tabs.
 *
 * - CapabilityBadge: tri-state ✓ / ✗ / ? badge for a model capability.
 * - SourceTag: per-field provenance marker (db / env / default).
 */

export function CapabilityBadge({
  label,
  state,
}: {
  label: string;
  state: boolean | null | undefined;
}) {
  if (state === true) {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-success-subtle text-success">
        ✓ {label}
      </span>
    );
  }
  if (state === false) {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-danger-subtle text-danger">
        ✗ {label}
      </span>
    );
  }
  return (
    <span
      className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-surface-muted text-muted"
      title="Provider didn't expose a capability flag for this model. Use the Test tab to verify."
    >
      ? {label}
    </span>
  );
}

export function SourceTag({ source }: { source: string | undefined }) {
  if (source === 'db') {
    return (
      <span className="text-[11px] uppercase tracking-wide text-primary-hover">
        ● set in app
      </span>
    );
  }
  if (source === 'env') {
    return (
      <span className="text-[11px] uppercase tracking-wide text-subtle">
        ○ from .env
      </span>
    );
  }
  return (
    <span className="text-[11px] uppercase tracking-wide text-subtle">
      ○ default
    </span>
  );
}
