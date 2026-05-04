import { act, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { ThemeProvider } from '../ThemeContext';
import { useTheme } from '../useTheme';

type MqlListener = (event: MediaQueryListEvent) => void;

interface MockMql {
  matches: boolean;
  media: string;
  onchange: null;
  addEventListener: (type: 'change', listener: MqlListener) => void;
  removeEventListener: (type: 'change', listener: MqlListener) => void;
  addListener: (listener: MqlListener) => void;
  removeListener: (listener: MqlListener) => void;
  dispatchEvent: (event: Event) => boolean;
  /** Test helper — flips ``matches`` and notifies subscribers. */
  __setMatches: (matches: boolean) => void;
}

function createMockMql(initial: boolean): MockMql {
  let matches = initial;
  const listeners = new Set<MqlListener>();
  return {
    get matches() {
      return matches;
    },
    set matches(value: boolean) {
      matches = value;
    },
    media: '(prefers-color-scheme: dark)',
    onchange: null,
    addEventListener: (type, listener) => {
      if (type === 'change') listeners.add(listener);
    },
    removeEventListener: (type, listener) => {
      if (type === 'change') listeners.delete(listener);
    },
    addListener: (listener) => listeners.add(listener),
    removeListener: (listener) => listeners.delete(listener),
    dispatchEvent: () => true,
    __setMatches: (next: boolean) => {
      matches = next;
      listeners.forEach((listener) =>
        listener({ matches: next, media: '(prefers-color-scheme: dark)' } as MediaQueryListEvent),
      );
    },
  };
}

let mockMql: MockMql;

function ThemeProbe() {
  const { mode, resolvedMode, setMode } = useTheme();
  return (
    <div>
      <span data-testid="mode">{mode}</span>
      <span data-testid="resolved">{resolvedMode}</span>
      <button onClick={() => setMode('day')}>set-day</button>
      <button onClick={() => setMode('night')}>set-night</button>
      <button onClick={() => setMode('system')}>set-system</button>
    </div>
  );
}

function renderProbe() {
  return render(
    <ThemeProvider>
      <ThemeProbe />
    </ThemeProvider>,
  );
}

describe('ThemeContext', () => {
  beforeEach(() => {
    mockMql = createMockMql(false);
    Object.defineProperty(window, 'matchMedia', {
      configurable: true,
      writable: true,
      value: vi.fn().mockImplementation(() => mockMql),
    });
    window.localStorage.clear();
    document.documentElement.classList.remove('dark');
    // theme-color meta isn't in the test document by default; insert one
    // so the side-effect that updates it has somewhere to land.
    const existing = document.head.querySelector('meta[name="theme-color"]');
    if (existing) existing.remove();
    const meta = document.createElement('meta');
    meta.setAttribute('name', 'theme-color');
    meta.setAttribute('content', '#ffffff');
    document.head.appendChild(meta);
  });

  afterEach(() => {
    document.documentElement.classList.remove('dark');
  });

  it('defaults to system when localStorage is empty', () => {
    renderProbe();
    expect(screen.getByTestId('mode').textContent).toBe('system');
  });

  it('reads a previously persisted mode', () => {
    window.localStorage.setItem('whis-theme', 'night');
    renderProbe();
    expect(screen.getByTestId('mode').textContent).toBe('night');
    expect(screen.getByTestId('resolved').textContent).toBe('night');
    expect(document.documentElement.classList.contains('dark')).toBe(true);
  });

  it('ignores unrecognized stored values and falls back to system', () => {
    window.localStorage.setItem('whis-theme', 'midnight-mode');
    renderProbe();
    expect(screen.getByTestId('mode').textContent).toBe('system');
  });

  it('setMode("night") persists and adds the dark class', () => {
    renderProbe();
    act(() => {
      screen.getByText('set-night').click();
    });
    expect(window.localStorage.getItem('whis-theme')).toBe('night');
    expect(document.documentElement.classList.contains('dark')).toBe(true);
    expect(screen.getByTestId('resolved').textContent).toBe('night');
  });

  it('setMode("day") removes the dark class', () => {
    window.localStorage.setItem('whis-theme', 'night');
    renderProbe();
    expect(document.documentElement.classList.contains('dark')).toBe(true);
    act(() => {
      screen.getByText('set-day').click();
    });
    expect(window.localStorage.getItem('whis-theme')).toBe('day');
    expect(document.documentElement.classList.contains('dark')).toBe(false);
  });

  it('system mode follows the OS preference at mount', () => {
    mockMql = createMockMql(true);
    renderProbe();
    expect(screen.getByTestId('mode').textContent).toBe('system');
    expect(screen.getByTestId('resolved').textContent).toBe('night');
    expect(document.documentElement.classList.contains('dark')).toBe(true);
  });

  it('system mode reacts to OS preference changes without a re-render', () => {
    renderProbe();
    expect(screen.getByTestId('resolved').textContent).toBe('day');
    expect(document.documentElement.classList.contains('dark')).toBe(false);
    act(() => {
      mockMql.__setMatches(true);
    });
    expect(screen.getByTestId('resolved').textContent).toBe('night');
    expect(document.documentElement.classList.contains('dark')).toBe(true);
  });

  it('explicit night/day overrides do not flip when the OS preference changes', () => {
    renderProbe();
    act(() => {
      screen.getByText('set-day').click();
    });
    expect(document.documentElement.classList.contains('dark')).toBe(false);
    act(() => {
      mockMql.__setMatches(true);
    });
    expect(document.documentElement.classList.contains('dark')).toBe(false);
  });

  it('cleans up the matchMedia listener on unmount', () => {
    const removeSpy = vi.spyOn(mockMql, 'removeEventListener');
    const { unmount } = renderProbe();
    unmount();
    expect(removeSpy).toHaveBeenCalledWith('change', expect.any(Function));
  });
});
