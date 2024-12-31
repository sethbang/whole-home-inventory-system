<div align="center">
  <img src="images/whis_logo_web.svg" alt="WHIS Logo" width="256" height="256">
</div>

# Whole-Home Inventory System (WHIS)

WHIS is a self-hosted platform for managing household inventories. It centralizes item information—descriptions, photos, locations, purchase details, valuations, warranties—into a local database accessible from multiple devices via a web interface.

## Features

- 📱 **Progressive Web App (PWA)**: Offline access and mobile app-like experience
- 📸 **Photo Management**: Multiple images per item with camera integration
- 🔍 **Advanced Search**: Filter and sort by any field
- 🏷️ **Custom Fields**: Define your own data fields and categories
- 🔒 **Privacy-Focused**: Self-hosted with local data storage
- 📱 **Mobile-Optimized**: Camera integration and quick-add functionality
- 📊 **Analytics & Reports**: Generate detailed reports about your inventory
- 🔄 **Backup & Restore**: Automated backup system with restore capabilities
- 📷 **Barcode/QR Scanning**: Quick item lookup and entry using barcodes
- 🔄 **Data Migration**: Import/export functionality for various formats

## Screenshots

<div align="center">
  <img src="images/screenshots/WHIS - Whole-Home Inventory System.jpeg" alt="WHIS Dashboard" width="800">
  <p><em>Main Dashboard - Overview of your inventory items</em></p>
  
  <img src="images/screenshots/WHIS - Whole-Home Inventory System · 5.08pm · 12-22.jpeg" alt="WHIS Item Details" width="800">
  <p><em>Item Details View - Comprehensive information about each item</em></p>
  
  <img src="images/screenshots/WHIS - Whole-Home Inventory System · 5.08pm · 12-22 (1).jpeg" alt="WHIS Add Item" width="800">
  <p><em>Add Item Form - Easy item entry with custom fields</em></p>
  
  <img src="images/screenshots/WHIS - Whole-Home Inventory System · 5.08pm · 12-22 (2).jpeg" alt="WHIS Reports" width="800">
  <p><em>Analytics Dashboard - Detailed insights about your inventory</em></p>
</div>

## Tech Stack

### Backend
- Python 3.11
- FastAPI
- SQLite
- Uvicorn
- Alembic (Database migrations)

### Frontend
- React 18
- TypeScript
- Tailwind CSS
- Vite
- PWA Support

## Prerequisites

- Python 3.11 or higher
- Node.js 16 or higher
- npm or yarn
- Git

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/whis.git
cd whis
```

2. Set up the backend:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head  # Initialize the database
```

3. Set up the frontend:
```bash
cd frontend
npm install
```

## Development Setup

### Certificate Setup (Required)

> ⚠️ **Important**: WHIS uses HTTPS for secure communication. You must set up the development certificates before running the application.

1. Generate the development certificates:
```bash
cd frontend
node scripts/generate-certs.js
```
This will create:
- A root Certificate Authority (CA) certificate
- Server certificates for local development
- All certificates are stored in the `certs` directory

2. Install the CA certificate on your development machine:

#### macOS:
```bash
cd ../certs
sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain whis-dev-ca.crt
```

#### Linux:
```bash
cd ../certs
sudo cp whis-dev-ca.crt /usr/local/share/ca-certificates/
sudo update-ca-certificates
```

#### Windows:
1. Navigate to the `certs` directory
2. Double-click `whis-dev-ca.crt`
3. Click "Install Certificate"
4. Select "Local Machine"
5. Choose "Trusted Root Certification Authorities"
6. Complete the installation wizard

For detailed instructions including mobile devices and NAS setup, see `certs/CERTIFICATE-SETUP.md`.

> 📝 **Note**: The certificate needs to be installed on each device that will access WHIS.

3. Start the backend server:
```bash
cd backend
source venv/bin/activate  # On Windows use: venv\Scripts\activate
uvicorn app.main:app --reload
```

4. Start the frontend development server:
```bash
cd frontend
npm run dev
```

The application will be available at:
- Local development: https://localhost:5173
- Network access: https://[your-ip]:5173 or https://[your-nas]:5173

### Network Deployment Notes

When running WHIS on a network server (like a Synology NAS):
1. Install the CA certificate on the NAS itself (see `CERTIFICATE-SETUP.md`)
2. Distribute and install the CA certificate on all devices that need access
3. The server certificate automatically includes:
   - All local network IP addresses
   - Common NAS hostnames
   - Standard development hostnames (localhost)

This ensures secure access from any device on your network without certificate warnings.

The application will be available at:
- Frontend: https://localhost:5173
- Backend API: https://localhost:27182
- API Documentation: https://localhost:27182/docs

### Development Mode

The application includes a development mode that can be enabled to access additional features:
- Test data generation
- Quick user creation
- Database verification tools
- Sample data import/export testing

### Test Data

The `test_data/samples` directory contains various sample datasets for testing the import functionality:
- CSV and JSON format examples
- Different inventory scenarios (office, home electronics, garage tools, collectibles)
- Edge cases and minimal field samples

## Production Deployment

### Docker Deployment
The easiest way to deploy WHIS is using Docker:

1. Make sure you have Docker and Docker Compose installed on your system.

2. Build and start the containers:
```bash
docker compose up --build
```

3. Access the application:
- Frontend: https://localhost:5173
- Backend API: https://localhost:27182
- API Documentation: https://localhost:27182/docs

> ⚠️ **Important**: Before accessing the application, make sure to install the development CA certificate. See the "Development Certificate Setup" section above for instructions.

The Docker setup includes:
- Automatic container orchestration
- Volume mounts for persistent data (database, uploads, backups)
- Network configuration for service communication
- Production-ready Nginx configuration for the frontend

### Alternative Setup (Manual Installation)
- Hardware: Raspberry Pi 4 (2GB+ RAM) or equivalent
- OS: Raspberry Pi OS Lite or Ubuntu Server
- Network: Local network with optional VPN for remote access

## Usage

1. **First Time Setup**
   - Create an admin account using the registration page
   - Log in to access the dashboard

2. **Adding Items**
   - Click the "Add Item" button
   - Fill in the item details
   - Add photos using upload or camera capture
   - Use barcode scanner for quick entry
   - Save the item

3. **Managing Items**
   - Browse items from the dashboard
   - Use search and filters to find specific items
   - Click on items to view/edit details
   - Add custom fields as needed

4. **Data Management**
    - Create automatic backups of your data
    - Download backups for safekeeping
    - Upload backup files to restore data on another system
    - Restore from any backup with a single click
    - Import/export data using the migration tools
    - Generate reports and analytics

## Future Features

🚀 The following features are planned for future releases:

- 📱 **Mobile Apps**: Native mobile applications for iOS and Android
- 🤖 **AI Integration**: Automated item categorization and description generation
- 🏷️ **Smart Tags**: Automated tagging system based on item characteristics
- 📅 **Maintenance Reminders**: Schedule and track item maintenance
- 📈 **Value Tracking**: Track item depreciation and current market values
- 🔗 **API Integration**: Connect with home automation and insurance systems
- 🔌 **Plugin System**: Extensible architecture for community contributions

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- UI powered by [React](https://reactjs.org/)
- Styled with [Tailwind CSS](https://tailwindcss.com/)