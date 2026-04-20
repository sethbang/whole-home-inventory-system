# Whole-Home Inventory System (WHIS)

**Version:** 2.0.0 (Audit Remediation & Modernization)
**Author:** S. Bang
**Last Updated:** 2026-04-20

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

- ✓ **Backend:** Python 3.11+, FastAPI 0.115, SQLAlchemy 2.0, SQLite, Uvicorn 0.32, Alembic, PyJWT, pydantic-settings
- ✓ **Frontend:** React 19, TypeScript 5.6, Tailwind CSS 3.4, Vite 6, Axios, TanStack Query, React Router v7
- ✓ **Deployment:** Docker, Docker Compose (dev + NAS variants shipped)

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
- ✓ Username/password authentication with JWT bearer tokens (PyJWT, HS256 by default).
- ✓ bcrypt password hashing via passlib.
- ✓ HTTPS in dev and prod (self-signed dev CA; operator-provided TLS at the reverse proxy in prod).
- ✓ `SECRET_KEY` required via environment; fail-fast on startup if unset/placeholder and `BYPASS_AUTH=false`.
- ✓ Image uploads validated by magic bytes (not trusted `Content-Type`) with size and dimension caps.
- Rate limiting / WAF / MFA are not provided by the application; terminate at the reverse proxy.

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

### Phase 1 (MVP) — ✓ Completed
- ✓ Core CRUD operations
- ✓ Photo upload and storage
- ✓ Basic UI implementation
- ✓ Authentication system

### Phase 2 — ✓ Completed
- ✓ Custom fields system (JSON column on `items`)
- ✓ Advanced search and filtering
- ✓ Barcode/QR code scanning (lazy-loaded `@zxing/browser`)
- ✓ Backend pytest suite + GitHub Actions CI

### Phase 3 — ✓ Completed
- ✓ Backup/restore functionality (zip archives + in-app UI)
- ✓ Reporting features (analytics endpoints + Reports page)
- ✓ PWA implementation (`vite-plugin-pwa`)
- ✓ Docker deployment (dev + NAS compose files)

### Phase 4 — ✓ Completed (v2.0.0 audit remediation)
- ✓ Env-driven settings, `SECRET_KEY` required, auth bypass removed as default
- ✓ Alembic rebaselined (destructive migration replaced with idempotent baseline + `bootstrap.py`)
- ✓ python-jose → PyJWT swap
- ✓ Upload hardening (magic-byte validation, size + dimension caps)
- ✓ React 18 → 19
- ✓ Dead deps removed (sharp, jszip); BarcodeScanner lazy-loaded

### Phase 5 — eBay integration (Phase 1 shipped in v2.0.0)
- ✓ Seller Hub CSV export
- ✓ Category mapping
- ✓ eBay-specific custom fields
- eBay API (OAuth / Trading / Inventory APIs) — deferred to a future release

### Future
- Formik → React Hook Form migration
- React Router v7 data-router (`createBrowserRouter`) migration
- SQLAlchemy 2.x `select()` style migration
- Tailwind v4 evaluation
- End-to-end tests (Playwright/Cypress)
- Coverage gates in CI

## 10. Open-Source

WHIS will be released under the MIT License to encourage community contributions and broader adoption.

---

**End of Document**
