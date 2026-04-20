# WHIS Architecture Documentation

This document provides a comprehensive overview of the WHIS (Whole-Home Inventory System) architecture, including system design, components, patterns, and technical decisions.

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Principles](#architecture-principles)
3. [System Components](#system-components)
4. [Data Architecture](#data-architecture)
5. [Security Architecture](#security-architecture)
6. [Integration Architecture](#integration-architecture)
7. [Deployment Architecture](#deployment-architecture)
8. [Performance Architecture](#performance-architecture)

## System Overview

### High-Level Architecture

WHIS uses a modern client-server architecture with these key components:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    Frontend     │     │     Backend     │     │    Database     │
│   React + TS    │────▶│   FastAPI + Py  │────▶│     SQLite     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        ▲                       ▲                        ▲
        │                       │                        │
        │                       │                        │
    UI Layer              Service Layer            Data Layer
```

### Key Design Decisions

1. **Backend Framework**: FastAPI
   - High performance
   - Modern Python features
   - Automatic OpenAPI docs
   - Type safety with Pydantic

2. **Frontend Framework**: React
   - Component-based architecture
   - Virtual DOM for performance
   - Rich ecosystem
   - TypeScript support

3. **Database**: SQLite
   - Self-contained
   - Zero configuration
   - File-based storage
   - ACID compliance

4. **Authentication**: JWT
   - Stateless authentication
   - Secure token-based system
   - Easy client integration

## Architecture Principles

### Design Principles

1. **Separation of Concerns**
   - Clear component boundaries
   - Modular design
   - Independent scaling
   - Loose coupling

2. **Single Responsibility**
   - Focused components
   - Clear interfaces
   - Maintainable code
   - Easy testing

3. **Don't Repeat Yourself (DRY)**
   - Reusable components
   - Shared utilities
   - Consistent patterns
   - Maintainable codebase

4. **SOLID Principles**
   - Single responsibility
   - Open/closed principle
   - Liskov substitution
   - Interface segregation
   - Dependency inversion

### Technical Principles

1. **Security First**
   - HTTPS everywhere
   - JWT authentication
   - Input validation
   - Secure defaults

2. **Performance Focused**
   - Optimized queries
   - Efficient caching
   - Lazy loading
   - Code splitting

3. **Developer Experience**
   - Clear documentation
   - Type safety
   - Automated testing
   - Easy setup

## System Components

### Frontend Architecture

```
frontend/
├── src/
│   ├── components/       # Reusable UI components
│   │   ├── common/      # Shared components
│   │   ├── forms/       # Form components
│   │   └── layout/      # Layout components
│   ├── pages/           # Page components
│   ├── contexts/        # React contexts
│   ├── hooks/           # Custom hooks
│   ├── api/             # API client
│   ├── utils/           # Utilities
│   └── types/           # TypeScript types
```

#### Key Components

1. **Component Layer**
   - Presentational components
   - Container components
   - HOCs and providers
   - Custom hooks

2. **State Management**
   - React Context
   - Local state
   - Form state
   - Cache state

3. **API Integration**
   - Axios client
   - Type-safe requests
   - Error handling
   - Request caching

### Backend Architecture (actual layout, 2.0.0)

```
backend/
├── alembic/
│   ├── env.py
│   └── versions/
│       └── 20260420_0001_baseline.py   # idempotent baseline
├── app/
│   ├── routers/         # auth, items, images, analytics, backups, ebay
│   ├── ebay/            # eBay CSV export submodule
│   ├── models.py        # single-file SQLAlchemy models
│   ├── schemas.py       # single-file Pydantic schemas (ConfigDict-based)
│   ├── database.py      # engine + SessionLocal; reads DATABASE_URL from settings
│   ├── settings.py      # pydantic-settings singleton; fail-fast on SECRET_KEY
│   ├── security.py      # PyJWT auth, BYPASS_AUTH short-circuit
│   └── main.py          # FastAPI app factory + middleware + exception handlers
├── scripts/
│   └── bootstrap.py     # reconciles legacy alembic stamps, runs upgrade head
├── tests/               # pytest suite with in-memory SQLite conftest
├── .env.example
├── Dockerfile
└── requirements.txt
```

A dedicated `services/` layer does not exist today — business logic sits in the router modules. Extraction (particularly for `routers/items.py`) is deferred work documented in CLAUDE.md.

#### Key Components

1. **API Layer** — route handlers in `app/routers/*`, Pydantic request/response schemas, FastAPI dependency injection for DB sessions and auth.

2. **Settings Layer** — `app/settings.py` provides a `Settings` singleton backed by `pydantic-settings`. All operator-tunable knobs (auth bypass, secret key, upload dir, CORS, logging, debug) flow through it. Fail-fast at import time if `BYPASS_AUTH=false` and `SECRET_KEY` is missing or a known placeholder.

3. **Data Layer** — SQLAlchemy 2.x models with a custom `UUID` TypeDecorator that stores UUIDs as 36-char strings and coerces non-v4 UUIDs to v4. Alembic is the sole source of truth for schema (no `create_all()` at startup).

## Data Architecture

### Database Schema

Current schema (mirrors `backend/app/models.py`; produced by Alembic baseline `20260420_0001`). All UUID columns are stored as 36-char `VARCHAR` by the custom `UUID` TypeDecorator.

```sql
CREATE TABLE users (
    id               VARCHAR(36) PRIMARY KEY,
    email            VARCHAR,
    username         VARCHAR,
    hashed_password  VARCHAR,
    is_active        BOOLEAN,
    created_at       DATETIME
);
CREATE UNIQUE INDEX ix_users_email    ON users(email);
CREATE UNIQUE INDEX ix_users_username ON users(username);

CREATE TABLE items (
    id                  VARCHAR(36) PRIMARY KEY,
    name                VARCHAR,
    category            VARCHAR,
    location            VARCHAR,
    brand               VARCHAR,
    model_number        VARCHAR,
    serial_number       VARCHAR,
    barcode             VARCHAR,
    purchase_date       DATETIME,
    purchase_price      FLOAT,
    current_value       FLOAT,
    warranty_expiration DATETIME,
    notes               VARCHAR,
    custom_fields       JSON,                          -- per-item blob, not a separate table
    created_at          DATETIME,
    updated_at          DATETIME,
    owner_id            VARCHAR(36) REFERENCES users(id)
);
CREATE INDEX ix_items_name     ON items(name);
CREATE INDEX ix_items_category ON items(category);
CREATE INDEX ix_items_location ON items(location);
CREATE INDEX ix_items_barcode  ON items(barcode);

CREATE TABLE item_images (
    id          VARCHAR(36) PRIMARY KEY,
    item_id     VARCHAR(36) REFERENCES items(id),
    filename    VARCHAR,
    file_path   VARCHAR,
    created_at  DATETIME
);

CREATE TABLE backups (
    id             VARCHAR(36) PRIMARY KEY,
    owner_id       VARCHAR(36) REFERENCES users(id),
    filename       VARCHAR,
    file_path      VARCHAR,
    size_bytes     INTEGER,
    item_count     INTEGER,
    image_count    INTEGER,
    created_at     DATETIME,
    status         VARCHAR,           -- 'completed' | 'failed' | 'in_progress'
    error_message  VARCHAR
);
```

**Note:** `custom_fields` is a JSON column on `items`, not a separate table. Earlier versions of this doc described a normalized `custom_fields` table — that was aspirational and never shipped.

### Data Flow

1. **Create Item Flow**
```
Client Request
     ↓
Input Validation
     ↓
Business Logic
     ↓
Database Transaction
     ↓
File Storage (images)
     ↓
Response Formation
```

2. **Query Flow**
```
Client Request
     ↓
Query Parameters
     ↓
Query Building
     ↓
Database Query
     ↓
Data Transform
     ↓
Response
```

## Security Architecture

### Authentication Flow

```
Login Request
     ↓
Credential Validation
     ↓
JWT Generation
     ↓
Token Response
     ↓
Client Storage
     ↓
Request Authorization
```

### Security Layers

See `SECURITY.md` for the full posture. Summary of what the app itself provides vs. what is expected to be terminated at the reverse proxy / host layer:

1. **Network Security (app-provided)**
   - HTTPS-only origins in CORS defaults
   - Origin whitelist via `CORS_ORIGINS`
   - Pydantic request validation

2. **Network Security (operator-provided)**
   - Rate limiting, WAF, HSTS, DDoS protection — the application does not include these; terminate at the reverse proxy

3. **Application Security**
   - PyJWT signature verification with `SECRET_KEY` (HS256 by default)
   - bcrypt password hashing via passlib
   - Pillow magic-byte upload validation with size + dimension caps
   - Redacted exception responses (stack traces gated on `DEBUG=true`)
   - `logging` module throughout server code — no `print()` leaking sensitive data

4. **Data Security**
   - SQLite file protected by OS-level filesystem permissions
   - Backups are zip archives — **not** encrypted at rest; encrypt the host volume or the backup destination if threat model requires it
   - No audit log layer; standard application logs only

## Integration Architecture

### External Systems

1. **File Storage**
```
Upload Request
     ↓
File Validation
     ↓
File Processing
     ↓
Storage Write
     ↓
Database Update
```

2. **Backup System**
```
Backup Trigger
     ↓
Data Export
     ↓
File Compression
     ↓
Storage Write
     ↓
Cleanup
```

3. **eBay Integration**
```
Phase 1: Seller Hub Export
     ↓
Item Selection
     ↓
Category Mapping
     ↓
CSV Generation
     ↓
Image URL Processing
     ↓
Export File

Phase 2: API Integration (Future)
     ↓
OAuth Authentication
     ↓
Direct API Calls
     ↓
Real-time Sync
     ↓
Order Management
```

### API Integration

1. **REST API**
   - Resource-based URLs
   - Standard HTTP methods
   - JSON responses
   - Error handling

2. **WebSocket (Future)**
   - Real-time updates
   - Bi-directional
   - Event-based
   - Connection management

3. **eBay Integration API (Future)**
   - OAuth 2.0 authentication
   - Trading API integration
   - Inventory API integration
   - Order management
   - Bulk operations

### Data Transformations

1. **eBay Export Flow**
```
Item Data
     ↓
Field Mapping
     ↓
Category Translation
     ↓
Image Processing
     ↓
CSV/Feed Generation
     ↓
Export File
```

## Deployment Architecture

### Development Environment

```
Local Machine
     ↓
Development Server
     ↓
SQLite Database
     ↓
Local File Storage
```

### Production Environment

```
Docker Container
     ↓
Production Server
     ↓
Volume Mounts
     ↓
Reverse Proxy
```

### Deployment Options

1. **Docker Deployment**
```yaml
services:
  backend:
    build: ./backend
    volumes:
      - data:/app/data
    ports:
      - "27182:27182"

  frontend:
    build: ./frontend
    ports:
      - "5173:80"
    depends_on:
      - backend
```

2. **Manual Deployment**
```
System Setup
     ↓
Dependencies
     ↓
Configuration
     ↓
Service Setup
     ↓
SSL/TLS
```

## Performance Architecture

### Caching Strategy

1. **Backend Caching**
   - Query results
   - Static responses
   - File cache
   - Memory cache

2. **Frontend Caching**
   - API responses
   - Static assets
   - Component state
   - Form data

### Optimization Techniques

1. **Database Optimization**
   - Indexed queries
   - Efficient joins
   - Query planning
   - Connection pooling

2. **API Optimization**
   - Response compression
   - Batch operations
   - Pagination
   - Field selection

3. **Frontend Optimization**
   - Code splitting
   - Lazy loading
   - Image optimization
   - Bundle optimization

## Future Architecture Considerations

1. **Scalability**
   - Database sharding
   - Load balancing
   - Service workers
   - CDN integration

2. **Features**
   - Mobile apps
   - Offline support
   - Real-time updates
   - AI integration
   - Enhanced eBay integration

3. **Integration**
   - External APIs
   - Authentication providers
   - Cloud storage
   - Analytics
   - Additional marketplace integrations

## Architecture Decision Records

### ADR 1: Choice of SQLite

**Context:**
- Self-hosted system
- Single-user focus
- Simple deployment
- File-based storage

**Decision:**
Use SQLite as the primary database.

**Consequences:**
+ Simple deployment
+ Zero configuration
+ File-based backups
- Limited concurrency
- No built-in replication

### ADR 2: JWT Authentication

**Context:**
- Stateless architecture
- Multiple clients
- Security requirements

**Decision:**
Use JWT for authentication.

**Consequences:**
+ Stateless authentication
+ Easy client integration
+ Standard security
- Token size
- Revocation complexity

## Monitoring and Maintenance

### Monitoring Points

1. **Application Monitoring**
   - Error rates
   - Response times
   - Resource usage
   - User activity

2. **System Monitoring**
   - Disk usage
   - Memory usage
   - CPU usage
   - Network traffic

### Maintenance Procedures

1. **Backup Procedures**
   - Database backups
   - File backups
   - Configuration backups
   - Verification

2. **Update Procedures**
   - Version control
   - Database migrations
   - Configuration updates
   - Dependency updates

## Documentation Standards

1. **Code Documentation**
   - Inline comments
   - Function documentation
   - Type hints
   - Examples

2. **API Documentation**
   - OpenAPI/Swagger
   - Request/response examples
   - Error documentation
   - Authentication details

3. **Architecture Documentation**
   - Component diagrams
   - Data flow diagrams
   - Sequence diagrams
   - Decision records