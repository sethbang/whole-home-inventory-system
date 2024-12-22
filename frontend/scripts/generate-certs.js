#!/usr/bin/env node
import { execSync } from 'child_process';
import { mkdirSync, existsSync, writeFileSync } from 'fs';
import { join } from 'path';

const certsDir = join(process.cwd(), 'certs');

// Create certs directory if it doesn't exist
if (!existsSync(certsDir)) {
  mkdirSync(certsDir, { recursive: true });
}

// Create OpenSSL config with SAN
const opensslConfig = `
[req]
default_bits = 2048
prompt = no
default_md = sha256
x509_extensions = v3_req
distinguished_name = dn

[dn]
C = US
ST = State
L = City
O = Organization
CN = localhost

[v3_req]
subjectAltName = @alt_names

[alt_names]
DNS.1 = localhost
IP.1 = 127.0.0.1
IP.2 = 192.168.1.15
`;

const configPath = join(certsDir, 'openssl.cnf');
writeFileSync(configPath, opensslConfig);

// Generate self-signed certificate
console.log('Generating self-signed certificate...');
try {
  execSync(
    `openssl req -x509 -newkey rsa:2048 -keyout ${join(certsDir, 'key.pem')} -out ${join(
      certsDir,
      'cert.pem'
    )} -days 365 -nodes -config ${configPath}`,
    { stdio: 'inherit' }
  );
  console.log('Certificate generated successfully!');
} catch (error) {
  console.error('Failed to generate certificate:', error);
  process.exit(1);
}