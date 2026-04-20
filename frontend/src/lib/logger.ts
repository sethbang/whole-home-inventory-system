/**
 * Minimal logger that no-ops in production builds.
 *
 * The api client used to call `console.log` / `console.error` directly, which
 * (a) leaked request/response details including credentials into browser
 * DevTools visible to anyone looking over the user's shoulder, and (b) made
 * production noise impossible to silence. This wrapper keeps dev-time
 * observability while ensuring production builds stay quiet.
 *
 * In production, errors are still surfaced via thrown exceptions / React Query
 * error states / toasts — the UI layer is the right place to show them, not
 * the browser console.
 */

type LogFn = (...args: unknown[]) => void;

// NODE_ENV is replaced at build time by Vite (to 'production' in prod builds)
// and is always set by Node/Jest. We avoid `import.meta.env.DEV` here so that
// this module is also importable under ts-jest's CommonJS target without any
// transform gymnastics.
const isDev =
  typeof process !== 'undefined' && process.env?.NODE_ENV !== 'production';

const noop: LogFn = () => {
  /* intentionally empty */
};

export interface Logger {
  debug: LogFn;
  info: LogFn;
  warn: LogFn;
  error: LogFn;
}

export const logger: Logger = {
  debug: isDev ? (...args) => console.debug(...args) : noop,
  info: isDev ? (...args) => console.info(...args) : noop,
  // Warnings and errors are still emitted in production — they're actionable
  // signals, not chatty dev output. Flip to `noop` if you want full silence.
  warn: (...args) => console.warn(...args),
  error: (...args) => console.error(...args),
};
