import { describe, expect, it } from 'vitest';

import { isJobReference } from '../jobs';

describe('isJobReference', () => {
  it('accepts the canonical discriminator shape', () => {
    expect(isJobReference({ kind: 'job', job_id: 'abc' })).toBe(true);
  });

  it('rejects non-objects', () => {
    expect(isJobReference(null)).toBe(false);
    expect(isJobReference(undefined)).toBe(false);
    expect(isJobReference('job')).toBe(false);
    expect(isJobReference(42)).toBe(false);
  });

  it('rejects a missing or wrong kind', () => {
    expect(isJobReference({ job_id: 'abc' })).toBe(false);
    expect(isJobReference({ kind: 'other', job_id: 'abc' })).toBe(false);
  });

  it('rejects a missing or non-string job_id', () => {
    expect(isJobReference({ kind: 'job' })).toBe(false);
    expect(isJobReference({ kind: 'job', job_id: 123 })).toBe(false);
  });

  it('narrows the type when true', () => {
    const v: unknown = { kind: 'job', job_id: 'xyz' };
    if (isJobReference(v)) {
      // Type narrowing check — if this compiles, the type predicate works.
      expect(v.job_id).toBe('xyz');
    }
  });
});
