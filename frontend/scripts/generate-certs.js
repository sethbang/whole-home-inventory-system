#!/usr/bin/env node
import { execSync } from 'child_process';
import {
  mkdirSync,
  existsSync,
  writeFileSync,
  readFileSync,
  chmodSync,
  copyFileSync,
  statSync,
} from 'fs';
import { join } from 'path';
import { networkInterfaces } from 'os';
import { createHash } from 'crypto';

// Use environment variable for output directory or default to ./certs
const outputDir = process.env.CERT_OUTPUT_DIR || join(process.cwd(), 'certs');
const certsDir = join(process.cwd(), 'certs');

// Create all necessary directories
[certsDir, outputDir].forEach(dir => {
  if (!existsSync(dir)) {
    mkdirSync(dir, { recursive: true });
  }
});

// Build the SAN list from a hostname-only base plus env-driven host-specific
// additions. `WHIS_LAN_IP` is the host's LAN IPv4 (detected by `bin/whis` on
// the host and passed in — never trustworthy when this script runs inside a
// container, which is why we short-circuit on `isInContainer` further down).
// `WHIS_EXTRA_SANS` is a comma-separated escape hatch for any additional
// hostname or IP (a Mac's `<computer-name>.local` from `scutil --get
// LocalHostName`, a secondary LAN, a VPN address). The base list stays
// identical across every install so the canonical `https://whis.local:5173`
// URL works in every household.
const buildSanList = () => {
  const base = [
    'localhost',
    '*.localhost',
    'whis.local',
    '*.whis.local',
    'nas.local',
    '*.nas.local',
    '127.0.0.1',
    '::1',
  ];
  const lan = process.env.WHIS_LAN_IP ? [process.env.WHIS_LAN_IP.trim()] : [];
  const extra = (process.env.WHIS_EXTRA_SANS || '')
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean);
  // Dedup while preserving order so a stable signature can be computed below.
  return Array.from(new Set([...base, ...lan, ...extra]));
};

const SAN_LIST = buildSanList();

// Render the OpenSSL [alt_names] block from the SAN list. IP entries (v4 or
// v6) take the IP.N slot; everything else goes into DNS.N. The mkcert path
// just consumes SAN_LIST directly so it doesn't need this helper.
const isIpv4 = (s) => /^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/.test(s);
const isIpAddress = (s) => isIpv4(s) || (s.includes(':') && !s.includes('.'));
const buildAltNamesBlock = () => {
  const lines = [];
  let dnsIdx = 1;
  let ipIdx = 1;
  for (const san of SAN_LIST) {
    if (isIpAddress(san)) {
      lines.push(`IP.${ipIdx++} = ${san}`);
    } else {
      lines.push(`DNS.${dnsIdx++} = ${san}`);
    }
  }
  return lines.join('\n');
};

// Drift check — only regenerate when the SAN set changes or the server cert
// is older than 350 days (gives us 15 days of warning before the 365-day cert
// expires). The signature is the sha256 of the sorted SAN list, written next
// to the certs so re-runs of `bin/whis up` are cheap.
const signaturePath = join(certsDir, '.san-signature');
const signatureFor = (sans) =>
  createHash('sha256').update([...sans].sort().join('\n')).digest('hex');

const certIsFresh = () => {
  const certPath = join(certsDir, 'cert.pem');
  const keyPath = join(certsDir, 'key.pem');
  if (!existsSync(certPath) || !existsSync(keyPath)) return false;
  if (!existsSync(signaturePath)) return false;
  const recorded = readFileSync(signaturePath, 'utf-8').trim();
  if (recorded !== signatureFor(SAN_LIST)) return false;
  const ageMs = Date.now() - statSync(certPath).mtimeMs;
  if (ageMs > 350 * 24 * 60 * 60 * 1000) return false;
  return true;
};

const writeSignature = () => {
  writeFileSync(signaturePath, signatureFor(SAN_LIST) + '\n');
  chmodSync(signaturePath, 0o644);
};

// v2.4: prefer mkcert when it's on PATH. mkcert generates certs trusted
// by the system root store automatically — no manual CA install step per
// device. Falls back to the OpenSSL CA flow below when mkcert isn't
// available (CI, slim containers, fresh VMs).
const isMkcertAvailable = () => {
  try {
    execSync('which mkcert', { stdio: 'ignore' });
    return true;
  } catch {
    return false;
  }
};

const isInContainer = existsSync('/.dockerenv');

const generateWithMkcert = () => {
  console.log('Found mkcert — using it instead of the OpenSSL CA flow.');
  const certPath = join(certsDir, 'cert.pem');
  const keyPath = join(certsDir, 'key.pem');

  // Install the mkcert CA into the system trust store (idempotent —
  // safe to run even if already installed). Skip inside containers
  // where there's no host trust store to touch.
  if (!isInContainer) {
    try {
      execSync('mkcert -install', { stdio: 'inherit' });
    } catch (err) {
      console.warn(
        'mkcert -install failed — continuing anyway, but you may need to trust the CA manually.',
      );
    }
  }

  // Generate the cert pair covering every SAN we care about.
  execSync(
    `mkcert -cert-file "${certPath}" -key-file "${keyPath}" ${SAN_LIST.map((s) => `"${s}"`).join(' ')}`,
    { stdio: 'inherit' },
  );
  chmodSync(keyPath, 0o600);
  chmodSync(certPath, 0o644);

  // Copy mkcert's CA cert into the distribution dir so the existing
  // "install on this device" docs still work for any browsers that
  // skipped the system root store (iOS, Android) and for distributing
  // to other household devices that don't have mkcert installed.
  let caCopied = false;
  try {
    const caroot = execSync('mkcert -CAROOT', { encoding: 'utf-8' }).trim();
    const mkcertCaCert = join(caroot, 'rootCA.pem');
    if (existsSync(mkcertCaCert)) {
      copyFileSync(mkcertCaCert, outputCaCertPath);
      chmodSync(outputCaCertPath, 0o644);
      console.log(`mkcert root CA copied to ${outputCaCertPath} for device installs.`);
      caCopied = true;
    }
  } catch {
    // Non-fatal — the script will still emit a setup doc, just without
    // the canonical CA copy beside it.
  }

  // Always (re)write the setup doc so it reflects the path actually
  // used and stays in sync with whatever this version of the script
  // emits — the file used to be skipped on re-runs of an already-
  // initialized cert directory.
  writeSetupInstructions('mkcert', { caCopied });

  console.log('\nmkcert certificates generated successfully.');
  console.log(`Setup instructions written to ${readmePath}.`);
};

// Create OpenSSL config for CA
const caConfig = `
[req]
default_bits = 4096
prompt = no
default_md = sha384
x509_extensions = v3_ca
distinguished_name = dn

[dn]
C = US
ST = Colorado
L = Denver
O = WHIS Development CA
OU = Development
CN = WHIS Local Development Root CA
emailAddress = dev@whis.local

[v3_ca]
subjectKeyIdentifier = hash
authorityKeyIdentifier = keyid:always,issuer
basicConstraints = critical, CA:true
keyUsage = critical, digitalSignature, cRLSign, keyCertSign
`;

// Create OpenSSL config for server certificate
const serverConfig = `
[req]
default_bits = 4096
prompt = no
default_md = sha384
req_extensions = v3_req
distinguished_name = dn

[dn]
C = US
ST = Colorado
L = Denver
O = WHIS Development
OU = Development
CN = localhost
emailAddress = dev@whis.local

[v3_req]
basicConstraints = CA:FALSE
keyUsage = digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth, clientAuth
subjectAltName = @alt_names

[alt_names]
${buildAltNamesBlock()}
`;

const caConfigPath = join(certsDir, 'ca.cnf');
const serverConfigPath = join(certsDir, 'server.cnf');
const caKeyPath = join(certsDir, 'ca.key');
const caCertPath = join(certsDir, 'ca.crt');
const outputCaCertPath = join(outputDir, 'whis-dev-ca.crt');
const readmePath = join(outputDir, 'CERTIFICATE-SETUP.md');

// Function to check if CA already exists
const caExists = () => {
  try {
    return existsSync(caKeyPath) && existsSync(caCertPath);
  } catch (error) {
    return false;
  }
};

// Per-OS install snippets shared by both the mkcert and OpenSSL setup
// docs. Trust steps are identical at the OS level — the only difference
// between the two paths is whether the host running this script also
// needs to follow them (mkcert handles its own host with `mkcert
// -install`; OpenSSL doesn't).
const PER_DEVICE_INSTRUCTIONS = `### Desktop Browsers

#### macOS
\`\`\`bash
sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain whis-dev-ca.crt
\`\`\`

#### Linux
\`\`\`bash
sudo cp whis-dev-ca.crt /usr/local/share/ca-certificates/
sudo update-ca-certificates
\`\`\`

#### Windows
1. Double click \`whis-dev-ca.crt\`
2. Click "Install Certificate"
3. Select "Local Machine"
4. Select "Place all certificates in the following store"
5. Click "Browse" and select "Trusted Root Certification Authorities"
6. Click "Next" and then "Finish"

#### Firefox
Firefox uses its own trust store rather than the OS root store. Either install \`mkcert\` and run \`mkcert -install\` (which patches Firefox automatically), or import \`whis-dev-ca.crt\` manually under *Settings → Privacy & Security → Certificates → View Certificates → Authorities → Import*.

### Mobile Devices

#### iOS
1. Email \`whis-dev-ca.crt\` to yourself or host it on a local web server
2. Open the certificate file on your iOS device
3. Open Settings → "Profile Downloaded" at the top → Install
4. Settings → General → About → Certificate Trust Settings → enable full trust for the WHIS CA

#### Android
1. Copy \`whis-dev-ca.crt\` to your Android device
2. Settings → Security → Install from storage (exact path varies by device)
3. Select the file, name it (e.g. "WHIS Development CA"), confirm

### Network Attached Storage (NAS)

#### Synology DSM
Control Panel → Security → Certificate → Import → select \`whis-dev-ca.crt\`, then restart any services that proxy WHIS.`;

const VERIFICATION_AND_SECURITY = `## Verification

After installing the certificate:
1. Restart your browser (full quit, not just close — Cmd+Q on macOS)
2. Visit https://localhost:5173 (or your NAS hostname/IP)
3. The connection should show as secure with no warnings

## Security Notes

This certificate is for **local-network development use only**. The CA root that signs it is in this directory — anyone who copies it onto your network can issue certs your browsers will trust.

- Don't expose any host serving these certs to the public internet
- Don't share the \`*.key\` files outside the household
- Rotate by deleting the \`certs/\` directory and rerunning \`npm run dev\` (CA validity is 10 years; server cert is 1 year)
- For public-internet deployments, use the \`docker-compose.nas.yml\` + Caddy + Let's Encrypt path instead (see the project README)`;

// Path-aware setup-instruction writer. Idempotent — safe to call on
// every script run. ``mode`` is either ``"mkcert"`` or ``"openssl"``;
// the host-side trust steps differ, the per-device steps don't.
const writeSetupInstructions = (mode, opts = {}) => {
  const { caCopied = true } = opts;

  const mkcertHostNote = `## This Host

\`mkcert -install\` ran during cert generation, so this machine already trusts the WHIS CA — no further action needed for browsers that read the system trust store. Firefox is patched too (mkcert installs into NSS when available).

If the trust step was skipped (running inside a Docker container, or \`mkcert -install\` failed), follow the per-device instructions below for this host.`;

  const opensslHostNote = `## This Host

This script generated a self-signed root CA using OpenSSL. The host **does not yet trust it** — your browser will show \`NET::ERR_CERT_AUTHORITY_INVALID\` until you install \`whis-dev-ca.crt\` into the system trust store using the per-device instructions below.

The friendlier alternative is to install \`mkcert\` (\`brew install mkcert nss\` on macOS, then \`mkcert -install\`) and rerun \`npm run dev\` — mkcert handles the trust step for the host automatically and only requires the per-device steps for *other* devices on your network.`;

  const hostNote = mode === 'mkcert' ? mkcertHostNote : opensslHostNote;

  const caLocationLine = caCopied
    ? 'The CA certificate is located at: `whis-dev-ca.crt`'
    : 'No CA certificate was copied into this directory (the source CA may live elsewhere — check the script output).';

  const content = `# WHIS Development Certificate Setup

This directory contains the certificates your browser uses to talk to WHIS over HTTPS on your local network. The accompanying root CA (\`whis-dev-ca.crt\`) is what each device on the network trusts so the per-host server cert validates cleanly.

## Certificate Location
${caLocationLine}

${hostNote}

## Installing on Other Devices

Every additional device that browses to WHIS — phones, tablets, other workstations, the NAS web UI — needs to install the CA once. Reuse \`whis-dev-ca.crt\` from this directory.

${PER_DEVICE_INSTRUCTIONS}

${VERIFICATION_AND_SECURITY}
`;

  writeFileSync(readmePath, content);
  chmodSync(readmePath, 0o644);
};

// Function to create CA if it doesn't exist
const ensureCA = () => {
  if (!caExists()) {
    console.log('Generating root CA certificate...');
    writeFileSync(caConfigPath, caConfig);

    // Generate CA private key
    execSync(
      `openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:4096 -out ${caKeyPath}`,
      { stdio: 'inherit' }
    );

    // Generate CA certificate
    execSync(
      `openssl req -x509 -new -nodes -key ${caKeyPath} -sha384 -days 3650 -out ${caCertPath} -config ${caConfigPath}`,
      { stdio: 'inherit' }
    );

    console.log('\nRoot CA certificate generated successfully!');
    console.log('\nFor immediate local testing run:');
    console.log(`sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain ${outputCaCertPath}`);
  }

  // Always (re)copy the canonical distribution filename so end-user
  // docs and downstream scripts can rely on it. This used to live
  // inside the !caExists() branch above, which meant the copy never
  // happened on subsequent runs and earlier installs sometimes ended
  // up without ``whis-dev-ca.crt`` at all.
  if (existsSync(caCertPath)) {
    copyFileSync(caCertPath, outputCaCertPath);
    chmodSync(outputCaCertPath, 0o644);
  }
};

// Generate server certificate
const generateServerCertificate = () => {
  console.log('Generating server certificate...');
  writeFileSync(serverConfigPath, serverConfig);
  
  const keyPath = join(certsDir, 'key.pem');
  const csrPath = join(certsDir, 'server.csr');
  const certPath = join(certsDir, 'cert.pem');
  
  // Generate server private key
  execSync(
    `openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:4096 -out ${keyPath}`,
    { stdio: 'inherit' }
  );
  
  // Generate CSR
  execSync(
    `openssl req -new -key ${keyPath} -out ${csrPath} -config ${serverConfigPath}`,
    { stdio: 'inherit' }
  );
  
  // Sign the CSR with our CA
  execSync(
    `openssl x509 -req -in ${csrPath} -CA ${caCertPath} -CAkey ${caKeyPath} -CAcreateserial -out ${certPath} -days 365 -sha384 -extensions v3_req -extfile ${serverConfigPath}`,
    { stdio: 'inherit' }
  );
  
  // Clean up CSR
  try {
    execSync(`rm ${csrPath}`);
  } catch (error) {
    // Ignore cleanup errors
  }
  
  // Set proper permissions
  chmodSync(keyPath, 0o600);
  chmodSync(certPath, 0o644);
  
  // Verify the certificate chain
  try {
    execSync(`openssl verify -CAfile ${caCertPath} ${certPath}`, { stdio: 'inherit' });
    console.log('Server certificate verified successfully!');
  } catch (error) {
    console.error('Warning: Server certificate verification failed');
  }
};

// Main execution
console.log('Setting up development certificates...\n');

// Inside a container `os.networkInterfaces()` returns the container's bridge
// addresses, not the host's LAN IP — historically that produced certs whose
// SANs were unreachable from any other device on the network. The host-side
// `bin/whis` wrapper is now the sanctioned entry point. Skip cleanly here so
// `npm run dev`'s `&& vite` chain still proceeds (vite reads the host-mounted
// certs from the volume).
if (isInContainer) {
  console.log(
    'Running inside a container — skipping cert generation. Certs are expected '
      + 'to come from the host-mounted ./frontend/certs volume. Generate them on '
      + 'the host first with `./bin/whis certs` (or `cd frontend && node '
      + 'scripts/generate-certs.js`).',
  );
  process.exit(0);
}

if (certIsFresh()) {
  console.log(
    'Certs current — skipping (SAN signature matches and cert mtime is fresh).',
  );
  console.log(`SAN list: ${SAN_LIST.join(', ')}`);
  process.exit(0);
}

if (isMkcertAvailable()) {
  generateWithMkcert();
} else {
  console.log('mkcert not on PATH — falling back to the OpenSSL CA flow.');
  ensureCA();
  generateServerCertificate();
  // Always (re)write the setup doc so it tracks the path actually
  // used and stays current with whatever this version of the script
  // emits — same as the mkcert branch.
  writeSetupInstructions('openssl', { caCopied: existsSync(outputCaCertPath) });
  console.log(`\nSetup instructions written to ${readmePath}.`);
}

writeSignature();

// Show network information. Prefer the host's detected LAN IP (passed in via
// `WHIS_LAN_IP` by the wrapper) so the printed URL matches what's actually in
// the cert SAN. Fall back to interface scanning for the legacy
// `cd frontend && npm run dev` native path.
console.log('\nNetwork Information:');
const advertised = process.env.WHIS_LAN_IP
  ? [process.env.WHIS_LAN_IP.trim()]
  : (() => {
      const interfaces = networkInterfaces();
      const addresses = [];
      for (const iface of Object.values(interfaces)) {
        for (const addr of iface || []) {
          if (addr.family === 'IPv4' && !addr.internal) {
            addresses.push(addr.address);
          }
        }
      }
      return addresses;
    })();

console.log(
  'Once each device has trusted whis-dev-ca.crt (or mkcert\'s root CA),',
);
console.log('these URLs work from any browser on the same LAN:');
console.log('  https://localhost:5173             (this host only)');
console.log('  https://whis.local:5173            (mDNS — no DNS server needed)');
advertised.forEach((ip) => {
  console.log(`  https://${ip}:5173    (LAN-IP fallback)`);
});