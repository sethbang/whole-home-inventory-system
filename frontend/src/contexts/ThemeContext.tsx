import React, { createContext, useCallback, useEffect, useState } from 'react';

export type ThemeMode = 'day' | 'night' | 'system';
export type ResolvedTheme = 'day' | 'night';

export interface ThemeContextType {
  mode: ThemeMode;
  resolvedMode: ResolvedTheme;
  setMode: (mode: ThemeMode) => void;
}

export const ThemeContext = createContext<ThemeContextType | undefined>(
  undefined,
);

const STORAGE_KEY = 'whis-theme';
const DARK_CLASS = 'dark';
const MEDIA_QUERY = '(prefers-color-scheme: dark)';

function isThemeMode(value: unknown): value is ThemeMode {
  return value === 'day' || value === 'night' || value === 'system';
}

function readStoredMode(): ThemeMode {
  if (typeof window === 'undefined') return 'system';
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    return isThemeMode(raw) ? raw : 'system';
  } catch {
    return 'system';
  }
}

function getSystemPrefersDark(): boolean {
  if (typeof window === 'undefined' || !window.matchMedia) return false;
  return window.matchMedia(MEDIA_QUERY).matches;
}

function applyDarkClass(resolved: ResolvedTheme) {
  if (typeof document === 'undefined') return;
  document.documentElement.classList.toggle(DARK_CLASS, resolved === 'night');
}

function syncThemeColorMeta() {
  if (typeof document === 'undefined' || typeof window === 'undefined') return;
  const meta = document.querySelector<HTMLMetaElement>('meta[name="theme-color"]');
  if (!meta) return;
  const surface = window
    .getComputedStyle(document.documentElement)
    .getPropertyValue('--color-surface-raised')
    .trim();
  if (surface) {
    meta.setAttribute('content', surface);
  }
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [mode, setModeState] = useState<ThemeMode>(() => readStoredMode());
  const [systemPrefersDark, setSystemPrefersDark] = useState<boolean>(() =>
    getSystemPrefersDark(),
  );

  const resolvedMode: ResolvedTheme =
    mode === 'system' ? (systemPrefersDark ? 'night' : 'day') : mode;

  // Persist + apply class + update theme-color meta whenever the resolved
  // theme changes (covers user toggle, system flip, and initial mount).
  useEffect(() => {
    applyDarkClass(resolvedMode);
    syncThemeColorMeta();
  }, [resolvedMode]);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    try {
      window.localStorage.setItem(STORAGE_KEY, mode);
    } catch {
      // localStorage is best-effort — failures (private mode, quota) are
      // not user-facing.
    }
  }, [mode]);

  // Always listen to system-preference changes; resolvedMode only consumes
  // the value when ``mode === 'system'`` so it's harmless to keep the
  // listener attached and lets the user toggle to System-sync mid-session
  // and pick up the current OS state instantly.
  useEffect(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return;
    const mql = window.matchMedia(MEDIA_QUERY);
    const handler = (event: MediaQueryListEvent) => {
      setSystemPrefersDark(event.matches);
    };
    // Some older browsers expose ``addListener`` instead of
    // ``addEventListener``; jsdom honors the standard.
    mql.addEventListener('change', handler);
    return () => mql.removeEventListener('change', handler);
  }, []);

  const setMode = useCallback((next: ThemeMode) => {
    setModeState(next);
  }, []);

  return (
    <ThemeContext.Provider value={{ mode, resolvedMode, setMode }}>
      {children}
    </ThemeContext.Provider>
  );
}
