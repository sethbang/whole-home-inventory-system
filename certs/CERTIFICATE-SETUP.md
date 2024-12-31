# WHIS Development Certificate Setup

This directory contains the root Certificate Authority (CA) certificate needed to securely access WHIS when running on your local network.

## Certificate Location
The CA certificate is located at: `whis-dev-ca.crt`

## Installation Instructions

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

### Mobile Devices

#### iOS
1. Email the `whis-dev-ca.crt` file to yourself or host it on a local web server
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
1. Copy the `whis-dev-ca.crt` file to your Android device
2. Go to Settings > Security > Install from storage (exact path may vary by device)
3. Find and select the certificate file
4. Name the certificate (e.g., "WHIS Development CA")
5. Select "VPN and apps" or "CA certificate" when prompted
6. Confirm installation

### Network Attached Storage (NAS)

#### Synology NAS
1. Log in to DSM
2. Go to Control Panel > Security > Certificate
3. Click "Import" and select the `whis-dev-ca.crt` file
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
