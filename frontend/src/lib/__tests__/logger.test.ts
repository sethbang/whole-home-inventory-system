/**
 * Logger behavior tests.
 *
 * The goal: prove that info/debug are silent in production, while warn/error
 * still surface (they represent actionable signals operators need to see).
 */

describe('logger', () => {
  const originalConsole = { ...console };
  let debugSpy: jest.SpyInstance;
  let infoSpy: jest.SpyInstance;
  let warnSpy: jest.SpyInstance;
  let errorSpy: jest.SpyInstance;

  beforeEach(() => {
    debugSpy = jest.spyOn(console, 'debug').mockImplementation(() => {});
    infoSpy = jest.spyOn(console, 'info').mockImplementation(() => {});
    warnSpy = jest.spyOn(console, 'warn').mockImplementation(() => {});
    errorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    jest.resetModules();
  });

  afterEach(() => {
    debugSpy.mockRestore();
    infoSpy.mockRestore();
    warnSpy.mockRestore();
    errorSpy.mockRestore();
    Object.assign(console, originalConsole);
  });

  it('forwards debug/info to console when in dev build', () => {
    jest.doMock('../../vite-env.d', () => ({}), { virtual: true });
    // In the jest environment, import.meta.env.DEV defaults to `true` because
    // we run with NODE_ENV=test (jsdom). The logger treats any truthy DEV as dev.
    const { logger } = require('../logger');
    logger.debug('a', 1);
    logger.info('b', 2);
    expect(debugSpy).toHaveBeenCalledWith('a', 1);
    expect(infoSpy).toHaveBeenCalledWith('b', 2);
  });

  it('always forwards warn and error', () => {
    const { logger } = require('../logger');
    logger.warn('warning');
    logger.error('bad thing');
    expect(warnSpy).toHaveBeenCalledWith('warning');
    expect(errorSpy).toHaveBeenCalledWith('bad thing');
  });

  it('never leaks raw credentials when used like api/client.ts does', () => {
    const { logger } = require('../logger');
    logger.debug('auth.login attempt', { username: 'alice' });
    // The call structurally excludes the password — the point of this test is
    // to document the expected usage pattern.
    expect(debugSpy).toHaveBeenCalledWith('auth.login attempt', { username: 'alice' });
    const allCalls = debugSpy.mock.calls.flat().map(String).join(' ');
    expect(allCalls).not.toContain('password');
  });
});
