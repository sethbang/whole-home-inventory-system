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

1. Start the backend server:
```bash
cd backend
source venv/bin/activate  # On Windows use: venv\Scripts\activate
uvicorn app.main:app --reload
```

2. Start the frontend development server:
```bash
cd frontend
npm run dev
```

The application will be available at:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

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
- Frontend: http://localhost:5173
- Backend API: http://localhost:27182
- API Documentation: http://localhost:27182/docs

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