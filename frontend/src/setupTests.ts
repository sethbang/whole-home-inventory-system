import '@testing-library/jest-dom/vitest';
import { afterEach } from 'vitest';
import { cleanup } from '@testing-library/react';

// React Testing Library doesn't auto-cleanup under Vitest the way it does
// under Jest; wire it up explicitly so elements from a prior test don't
// leak into the next.
afterEach(() => {
  cleanup();
});
