#!/usr/bin/env python3
import os
import subprocess
from pathlib import Path

def main():
    certs_dir = Path(__file__).parent.parent / "certs"
    certs_dir.mkdir(exist_ok=True)
    
    key_path = certs_dir / "key.pem"
    cert_path = certs_dir / "cert.pem"
    config_path = certs_dir / "openssl.cnf"
    
    # Create OpenSSL config with SAN
    openssl_config = """
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
"""
    
    # Write OpenSSL config
    with open(config_path, 'w') as f:
        f.write(openssl_config)
    
    print("Generating self-signed certificate...")
    subprocess.run([
        "openssl", "req", "-x509", "-newkey", "rsa:2048",
        "-keyout", str(key_path),
        "-out", str(cert_path),
        "-days", "365", "-nodes",
        "-config", str(config_path)
    ], check=True)
    print("Certificate generated successfully!")

if __name__ == "__main__":
    main()