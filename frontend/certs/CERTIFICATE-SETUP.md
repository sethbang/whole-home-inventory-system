# WHIS Development Certificate Setup

This directory contains the certificates your browser uses to talk to WHIS over HTTPS on your local network. The accompanying root CA (`whis-dev-ca.crt`) is what each device on the network trusts so the per-host server cert validates cleanly.

## Certificate Location
The CA certificate is located at: `whis-dev-ca.crt`

## This Host

`mkcert -install` ran during cert generation, so this machine already trusts the WHIS CA — no further action needed for browsers that read the system trust store. Firefox is patched too (mkcert installs into NSS when available).

If the trust step was skipped (running inside a Docker container, or `mkcert -install` failed), follow the per-device instructions below for this host.

## Installing on Other Devices

Every additional device that browses to WHIS — phones, tablets, other workstations, the NAS web UI — needs to install the CA once. Reuse `whis-dev-ca.crt` from this directory.

### Desktop Browsers

#### macOS
```bash
sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain whis-dev-ca.crt
```

#### Linux
```bash
sudo cp whis-dev-ca.crt /usr/local/share/ca-certificates/
sudo update-ca-certificates
```

#### Windows
1. Double click `whis-dev-ca.crt`
2. Click "Install Certificate"
3. Select "Local Machine"
4. Select "Place all certificates in the following store"
5. Click "Browse" and select "Trusted Root Certification Authorities"
6. Click "Next" and then "Finish"

#### Firefox
Firefox uses its own trust store rather than the OS root store. Either install `mkcert` and run `mkcert -install` (which patches Firefox automatically), or import `whis-dev-ca.crt` manually under *Settings → Privacy & Security → Certificates → View Certificates → Authorities → Import*.

### Mobile Devices

#### iOS
1. Email `whis-dev-ca.crt` to yourself or host it on a local web server
2. Open the certificate file on your iOS device
3. Open Settings → "Profile Downloaded" at the top → Install
4. Settings → General → About → Certificate Trust Settings → enable full trust for the WHIS CA

#### Android
1. Copy `whis-dev-ca.crt` to your Android device
2. Settings → Security → Install from storage (exact path varies by device)
3. Select the file, name it (e.g. "WHIS Development CA"), confirm

### Network Attached Storage (NAS)

#### Synology DSM
Control Panel → Security → Certificate → Import → select `whis-dev-ca.crt`, then restart any services that proxy WHIS.

## Verification

After installing the certificate:
1. Restart your browser (full quit, not just close — Cmd+Q on macOS)
2. Visit https://localhost:5173 (or your NAS hostname/IP)
3. The connection should show as secure with no warnings

## Security Notes

This certificate is for **local-network development use only**. The CA root that signs it is in this directory — anyone who copies it onto your network can issue certs your browsers will trust.

- Don't expose any host serving these certs to the public internet
- Don't share the `*.key` files outside the household
- Rotate by deleting the `certs/` directory and rerunning `npm run dev` (CA validity is 10 years; server cert is 1 year)
- For public-internet deployments, use the `docker-compose.nas.yml` + Caddy + Let's Encrypt path instead (see the project README)
