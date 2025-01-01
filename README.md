<div align="center">
  <img src="images/whis_logo_web.svg" alt="WHIS Logo" width="256" height="256">
</div>

# Whole-Home Inventory System (WHIS)

WHIS is a self-hosted platform for managing household inventories. It centralizes item information—descriptions, photos, locations, purchase details, valuations, warranties—into a local database accessible from multiple devices via a web interface.

## Documentation

📚 **[View Full Documentation](#documentation-suite)**

- 📖 [Architecture Overview](ARCHITECTURE.md)
- 🔧 [Development Guide](DEVELOPMENT.md)
- 🧪 [Testing Guide](TESTING.md)
- 🤝 [Contributing Guidelines](CONTRIBUTING.md)
- 📜 [API Documentation](API.md)
- 🔒 [Security Policy](SECURITY.md)
- 📋 [Changelog](CHANGELOG.md)
- 📦 [Deployment Guide](DEPLOYMENT.md)

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

## Documentation Suite

WHIS provides comprehensive documentation to help you understand, use, and contribute to the project:

### For Users

- **[User Guide](docs/USER_GUIDE.md)**: Complete guide to using WHIS
- **[Installation Guide](#installation)**: Step-by-step installation instructions
- **[Deployment Guide](DEPLOYMENT.md)**: Production deployment instructions
- **[Security Policy](SECURITY.md)**: Security information and best practices
- **[Changelog](CHANGELOG.md)**: Version history and updates

### For Developers

- **[Architecture Overview](ARCHITECTURE.md)**: System design and technical decisions
- **[Development Guide](DEVELOPMENT.md)**: Setting up development environment
- **[Contributing Guidelines](CONTRIBUTING.md)**: How to contribute to WHIS
- **[Testing Guide](TESTING.md)**: Testing procedures and guidelines
- **[API Documentation](API.md)**: Complete API reference

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

## Quick Start Guide

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
    - Upload backup files to restore data
    - Import/export data using migration tools
    - Generate reports and analytics

## Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details on:
- Code of Conduct
- Development process
- Pull request procedure
- Coding standards

## Support

- 📖 [Documentation](#documentation-suite)
- 🐛 [Issue Tracker](https://github.com/yourusername/whis/issues)
- 💬 [Discussions](https://github.com/yourusername/whis/discussions)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- UI powered by [React](https://reactjs.org/)
- Styled with [Tailwind CSS](https://tailwindcss.com/)