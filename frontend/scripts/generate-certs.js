#!/usr/bin/env node
import { execSync } from 'child_process';
import { mkdirSync, existsSync, writeFileSync, chmodSync, copyFileSync } from 'fs';
import { join } from 'path';
import { networkInterfaces } from 'os';

// Use environment variable for output directory or default to ./certs
const outputDir = process.env.CERT_OUTPUT_DIR || join(process.cwd(), 'certs');
const certsDir = join(process.cwd(), 'certs');

// Create all necessary directories
[certsDir, outputDir].forEach(dir => {
  if (!existsSync(dir)) {
    mkdirSync(dir, { recursive: true });
  }
});

// SAN list shared by both the mkcert and OpenSSL paths. Keep in sync
// with the [alt_names] block in the OpenSSL server config below.
const SAN_LIST = [
  'localhost',
  '*.localhost',
  'whis.local',
  '*.whis.local',
  'nas.local',
  '*.nas.local',
  '127.0.0.1',
  '::1',
  '192.168.1.15',
  '172.17.0.1',
  '172.18.0.1',
];

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

const generateWithMkcert = () => {
  console.log('Found mkcert — using it instead of the OpenSSL CA flow.');
  const certPath = join(certsDir, 'cert.pem');
  const keyPath = join(certsDir, 'key.pem');

  // Install the mkcert CA into the system trust store (idempotent —
  // safe to run even if already installed). Skip inside containers
  // where there's no host trust store to touch.
  const isInContainer = existsSync('/.dockerenv');
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
  // skipped the system root store (iOS, Android).
  try {
    const caroot = execSync('mkcert -CAROOT', { encoding: 'utf-8' }).trim();
    const mkcertCaCert = join(caroot, 'rootCA.pem');
    if (existsSync(mkcertCaCert)) {
      const outCa = join(outputDir, 'whis-dev-ca.crt');
      copyFileSync(mkcertCaCert, outCa);
      chmodSync(outCa, 0o644);
      console.log(`mkcert root CA copied to ${outCa} for device installs.`);
    }
  } catch {
    // Non-fatal — the device docs still make sense without the CA copy.
  }

  console.log('\nmkcert certificates generated successfully.');
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
DNS.1 = localhost
DNS.2 = *.localhost
DNS.3 = whis.local
DNS.4 = *.whis.local
DNS.5 = nas.local
DNS.6 = *.nas.local
IP.1 = 127.0.0.1
IP.2 = ::1
IP.3 = 192.168.1.15
IP.4 = 172.17.0.1
IP.5 = 172.18.0.1
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

// Create instructions for different devices
const createInstructions = () => {
  const content = `# WHIS Development Certificate Setup

This directory contains the root Certificate Authority (CA) certificate needed to securely access WHIS when running on your local network.

## Certificate Location
The CA certificate is located at: \`whis-dev-ca.crt\`

## Installation Instructions

### Desktop Browsers

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

### Mobile Devices

#### iOS
1. Email the \`whis-dev-ca.crt\` file to yourself or host it on a local web server
2. Open the certificate file on your iOS device
3. Go to Settings
4. Tap "Profile Downloaded" at the top
5. Tap "Install" in the top right
6. Enter your device passcode
7. Tap "Install" again
8. Tap "Install" one final time
9. Go to Settings > General > About > Certificate Trust Settings
10. Enable full trust for the WHIS Development CA certificate

#### Android
1. Copy the \`whis-dev-ca.crt\` file to your Android device
2. Go to Settings > Security > Install from storage (exact path may vary by device)
3. Find and select the certificate file
4. Name the certificate (e.g., "WHIS Development CA")
5. Select "VPN and apps" or "CA certificate" when prompted
6. Confirm installation

### Network Attached Storage (NAS)

#### Synology NAS
1. Log in to DSM
2. Go to Control Panel > Security > Certificate
3. Click "Import" and select the \`whis-dev-ca.crt\` file
4. Restart any necessary services

## Verification

After installing the certificate, you can verify it's working by:
1. Restarting your browser
2. Visiting https://localhost:5173 or https://[your-nas-ip]:5173
3. The connection should show as secure with no warnings

## Security Note

This certificate is for development purposes only. It should:
- Only be used on your local network
- Not be exposed to the public internet
- Be regenerated periodically (current expiration: 10 years)
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

    // Copy CA certificate to output directory with proper permissions
    execSync(`cp ${caCertPath} ${outputCaCertPath}`);
    chmodSync(outputCaCertPath, 0o644);
    
    // Create instructions file
    createInstructions();
    
    console.log('\nRoot CA certificate generated successfully!');
    console.log('\nIMPORTANT: Certificate files have been created in two locations:');
    console.log(`1. Development certificates: ${certsDir}`);
    console.log(`2. Distribution certificates: ${outputDir}`);
    console.log('\nPlease read the instructions in:');
    console.log(readmePath);
    console.log('\nFor immediate local testing run:');
    console.log(`sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain ${outputCaCertPath}`);
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
if (isMkcertAvailable()) {
  generateWithMkcert();
} else {
  console.log('mkcert not on PATH — falling back to the OpenSSL CA flow.');
  ensureCA();
  generateServerCertificate();
}

// Show network information
try {
  const interfaces = networkInterfaces();
  const addresses = [];
  
  for (const iface of Object.values(interfaces)) {
    for (const addr of iface || []) {
      if (addr.family === 'IPv4' && !addr.internal) {
        addresses.push(addr.address);
      }
    }
  }
  
  console.log('\nNetwork Information:');
  console.log('Local IP Addresses:', addresses.join(', '));
  console.log('\nThe server certificate includes these addresses in its SANs.');
  console.log('Devices on your network can access WHIS using these URLs:');
  addresses.forEach(ip => {
    console.log(`https://${ip}:5173`);
  });
} catch (error) {
  // Ignore network interface errors
}