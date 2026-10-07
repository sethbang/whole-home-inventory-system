import { isDevBypassAllowed } from '../devBypass';

describe('isDevBypassAllowed', () => {
  it('refuses bypass in production regardless of hostname', () => {
    expect(isDevBypassAllowed(false, 'localhost')).toBe(false);
    expect(isDevBypassAllowed(false, '192.168.1.122')).toBe(false);
    expect(isDevBypassAllowed(false, '127.0.0.1')).toBe(false);
  });

  it('allows bypass on loopback hostnames in dev', () => {
    expect(isDevBypassAllowed(true, 'localhost')).toBe(true);
    expect(isDevBypassAllowed(true, '127.0.0.1')).toBe(true);
    expect(isDevBypassAllowed(true, '::1')).toBe(true);
    expect(isDevBypassAllowed(true, 'whis.localhost')).toBe(true);
  });

  it('allows bypass on RFC-1918 private IPv4 in dev', () => {
    expect(isDevBypassAllowed(true, '10.0.0.1')).toBe(true);
    expect(isDevBypassAllowed(true, '172.16.0.5')).toBe(true);
    expect(isDevBypassAllowed(true, '172.31.255.254')).toBe(true);
    expect(isDevBypassAllowed(true, '192.168.1.122')).toBe(true);
  });

  it('refuses 172.x outside the 16–31 private range', () => {
    expect(isDevBypassAllowed(true, '172.15.0.1')).toBe(false);
    expect(isDevBypassAllowed(true, '172.32.0.1')).toBe(false);
  });

  it('refuses bypass on public hostnames even in dev', () => {
    expect(isDevBypassAllowed(true, 'whis.example.com')).toBe(false);
    expect(isDevBypassAllowed(true, '8.8.8.8')).toBe(false);
    expect(isDevBypassAllowed(true, 'my-tunnel.ngrok.app')).toBe(false);
  });

  it('refuses bypass on empty or malformed hostnames', () => {
    expect(isDevBypassAllowed(true, '')).toBe(false);
    expect(isDevBypassAllowed(true, '192.168.not.a.valid.ip')).toBe(false);
    expect(isDevBypassAllowed(true, '999.999.999.999')).toBe(false);
  });
});
