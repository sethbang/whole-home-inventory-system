/**
 * Guard that decides whether dev-mode auth bypass is safe to apply.
 *
 * Bypass is NEVER safe in a production build (import.meta.env.DEV === false),
 * so that branch returns false regardless of anything else.
 *
 * In a dev build, bypass is only safe when the app is being accessed from a
 * loopback or private-LAN host — the WHIS dev workflow. If a user somehow
 * exposes a dev build to the public internet (e.g. via a tunnel), we refuse
 * to trust localStorage state to impersonate the admin account.
 */

const PRIVATE_V4_RANGES: Array<[number, number, number, number, number]> = [
  // [a, b, mask, c, d] — we expand inline below; keeping structure simple.
];

function isLoopback(host: string): boolean {
  if (host === 'localhost') return true;
  if (host === '127.0.0.1') return true;
  if (host === '::1') return true;
  // Any hostname ending in .localhost is loopback per RFC 6761.
  if (host.endsWith('.localhost')) return true;
  return false;
}

function isPrivateIPv4(host: string): boolean {
  const parts = host.split('.');
  if (parts.length !== 4) return false;
  const octets = parts.map((p) => Number.parseInt(p, 10));
  if (octets.some((n) => Number.isNaN(n) || n < 0 || n > 255)) return false;
  const [a, b] = octets;
  // 10.0.0.0/8
  if (a === 10) return true;
  // 172.16.0.0/12
  if (a === 172 && b >= 16 && b <= 31) return true;
  // 192.168.0.0/16
  if (a === 192 && b === 168) return true;
  return false;
}

/**
 * Returns true if dev bypass should be permitted for the given hostname.
 *
 * @param isDevBuild  — pass import.meta.env.DEV; ensures bypass can only ever
 *                      run in a dev build.
 * @param hostname    — pass window.location.hostname (injectable for tests).
 */
export function isDevBypassAllowed(isDevBuild: boolean, hostname: string): boolean {
  if (!isDevBuild) return false;
  if (!hostname) return false;
  return isLoopback(hostname) || isPrivateIPv4(hostname);
}

// Silence unused-variable lint in case the ranges table is needed later.
void PRIVATE_V4_RANGES;
