# Whole-Home Inventory System (WHIS)

**Version:** 1.3 (Implementation Progress Update)  
**Author:** S. Bang  
**Last Updated:** 12/19/2024

## 1. Introduction

### 1.1 Overview

WHIS is a self-hosted platform for managing household inventories. It centralizes item information—descriptions, photos, locations, purchase details, valuations, warranties—into a local database accessible from multiple devices via a web interface. This ensures users maintain a clear, up-to-date record of their possessions.

### 1.2 Goals & Objectives

- ✓ **Centralized Inventory:** Provide a unified repository for all household item data.
- ✓ **Intuitive Interface:** Offer easy browsing, searching, and filtering of items.
- ✓ **Simplified Data Entry:** Streamline adding new items with photo uploads and automated IDs.
- ✓ **Customization:** Allow users to define custom fields and categories.
- ✓ **Data Security & Privacy:** Store data locally, granting users full control.

### 1.3 Target Audience

- Homeowners and renters seeking organized inventory management.
- Small businesses tracking equipment and supplies.

### 1.4 Non-Goals

- Automatic cloud synchronization (though user-configurable options may be explored later).
- Third-party e-commerce integration.
- Enterprise-scale deployments.

## 2. System Architecture

### 2.1 High-Level Design

WHIS uses a client-server model:

- ✓ **Server:** Runs on a Raspberry Pi 4 (recommended), local PC, NAS, or VM. Manages the database and image storage.
- ✓ **Client:** Browser-based web client (desktop and mobile). Future consideration for a Progressive Web App (PWA).
- ✓ **Network:** Designed for local network use. Remote access requires user-configured VPN or a reverse proxy.

### 2.2 Components

1. ✓ **Backend (Server):**
   - ✓ **API:** RESTful API implemented with Python and FastAPI.
   - ✓ **Database:** SQLite for simplicity and portability.
   - ✓ **Authentication:** Simple username/password authentication.

2. ✓ **Frontend (Web Client):**
   - ✓ **Inventory Browser:** A React Single Page Application for viewing, searching, and editing items.
   - ✓ **Inventory Creator:** A dedicated React component for adding new items with image uploads and validation.

3. ✓ **Storage:**
   - ✓ **Images:** Stored locally on the server's filesystem.
   - ✓ **Database:** A single SQLite database file on the server.

### 2.3 Deployment Model

- ✓ Primarily self-hosted on a Raspberry Pi 4.
- Docker image will be provided for simplified deployment on alternative platforms (Upcoming).

## 3. Feature Specifications

### 3.1 Core Features

- ✓ **CRUD Operations:** Create, Read, Update, and Delete items. Each item is identified by a UUID.
- ✓ **Data Fields:** Includes Name, Category, Location, Brand, Model/Serial Number, Purchase Date/Price, Value, Warranty Expiration, Notes, and user-defined custom fields.
- ✓ **Photo Support:** Multiple JPEG/PNG images per item, stored locally.
- ✓ **Browsing & Searching:** Filter by any field, sort items in ascending or descending order, and perform case-insensitive full-text searches.

## 4. Technology Stack

- ✓ **Backend:** Python 3.11, FastAPI, SQLite, Uvicorn
- ✓ **Frontend:** React 18, Tailwind CSS, Axios
- **Deployment:** Docker, Docker Compose (Upcoming)

## 5. User Interface

### 5.1 Desktop

- ✓ **Dashboard:** Overview of items and quick filters.
- ✓ **Item Listing:** Grid/List view with thumbnails (search/filtering in progress).
- ✓ **Item Detail:** Displays all metadata and images with edit/delete controls.
- ✓ **Add New Item:** A step-by-step form with image uploads and validation.
- **Accessibility:** (Upcoming) WCAG-compliant color contrast, keyboard navigation.

### 5.2 Mobile

- ✓ **Responsive Design:** Optimized for smaller screens.
- ✓ **Quick Add:** A dedicated button to rapidly add new items.
- ✓ **Camera Integration:** Supports using the device's camera for photo capture.

## 6. Security & Privacy

- ✓ Runs on a local network by default.
- ✓ Username/password authentication with hashed and salted credentials.
- HTTPS support via a reverse proxy configuration (documentation upcoming).

## 7. Performance & Scalability

- ✓ SQLite indexing for optimized queries.
- Target performance: Up to 10,000 items on a Raspberry Pi 4 (to be tested).
- Future Consideration: Database migration to PostgreSQL for larger datasets.

## 8. Maintenance & Extensibility

- ✓ Well-documented API using OpenAPI/Swagger.
- Unit and integration tests (In Progress).
- End-to-end tests for critical UI flows (Upcoming).
- Future Consideration: A plugin architecture for community contributions.

## 9. Roadmap

### Phase 1 (MVP) - ✓ Completed
- ✓ Core CRUD operations
- ✓ Photo upload and storage
- ✓ Basic UI implementation
- ✓ Authentication system

### Phase 2 (Current Phase)
- ✓ Custom fields system
- ✓ Advanced search and filtering
- Barcode/QR code scanning (In Progress)
- Unit and integration tests (In Progress)

### Phase 3 (Upcoming)
- Backup/restore functionality
- Reporting features
- PWA implementation
- Docker deployment

## 10. Open-Source

WHIS will be released under the MIT License to encourage community contributions and broader adoption.

---

**End of Document**
