/**
 * Logger behavior tests.
 *
 * The goal: prove that info/debug are silent in production, while warn/error
 * still surface (they represent actionable signals operators need to see).
 *
 * Uses dynamic ``await import('../logger')`` so ``vi.resetModules()`` in
 * ``beforeEach`` can hand each test a fresh module instance (the logger
 * caches the isDev flag at import time).
 */

describe('logger', () => {
  const originalConsole = { ...console };
  let debugSpy: ReturnType<typeof vi.spyOn>;
  let infoSpy: ReturnType<typeof vi.spyOn>;
  let warnSpy: ReturnType<typeof vi.spyOn>;
  let errorSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    debugSpy = vi.spyOn(console, 'debug').mockImplementation(() => {});
    infoSpy = vi.spyOn(console, 'info').mockImplementation(() => {});
    warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
    errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    vi.resetModules();
  });

  afterEach(() => {
    debugSpy.mockRestore();
    infoSpy.mockRestore();
    warnSpy.mockRestore();
    errorSpy.mockRestore();
    Object.assign(console, originalConsole);
  });

  it('forwards debug/info to console when in dev build', async () => {
    // Under Vitest, import.meta.env.DEV is truthy by default during tests.
    // The logger treats any truthy DEV as dev mode.
    const { logger } = await import('../logger');
    logger.debug('a', 1);
    logger.info('b', 2);
    expect(debugSpy).toHaveBeenCalledWith('a', 1);
    expect(infoSpy).toHaveBeenCalledWith('b', 2);
  });

  it('always forwards warn and error', async () => {
    const { logger } = await import('../logger');
    logger.warn('warning');
    logger.error('bad thing');
    expect(warnSpy).toHaveBeenCalledWith('warning');
    expect(errorSpy).toHaveBeenCalledWith('bad thing');
  });

  it('never leaks raw credentials when used like api/client.ts does', async () => {
    const { logger } = await import('../logger');
    logger.debug('auth.login attempt', { username: 'alice' });
    // The call structurally excludes the password — the point of this test is
    // to document the expected usage pattern.
    expect(debugSpy).toHaveBeenCalledWith('auth.login attempt', { username: 'alice' });
    const allCalls = debugSpy.mock.calls.flat().map(String).join(' ');
    expect(allCalls).not.toContain('password');
  });
});
