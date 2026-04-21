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

// v2.4: restored to `import.meta.env.DEV` now that Vitest is the test
// runner. The v2.1 NODE_ENV workaround existed only because ts-jest
// compiled this module as CommonJS and couldn't parse `import.meta`.
const isDev = import.meta.env.DEV;

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
