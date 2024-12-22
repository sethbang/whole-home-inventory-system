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
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

## Production Deployment

### Recommended Setup
- Hardware: Raspberry Pi 4 (2GB+ RAM) or equivalent
- OS: Raspberry Pi OS Lite or Ubuntu Server
- Network: Local network with optional VPN for remote access

Detailed deployment instructions coming soon.

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
   - Use the backup feature to create data backups
   - Restore from backups when needed
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