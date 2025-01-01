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

### Backend Architecture

```
backend/
├── app/
│   ├── routers/         # API routes
│   ├── models/          # Database models
│   ├── schemas/         # Pydantic schemas
│   ├── services/        # Business logic
│   ├── core/            # Core functionality
│   └── utils/           # Utilities
```

#### Key Components

1. **API Layer**
   - Route handlers
   - Request validation
   - Response formatting
   - Error handling

2. **Service Layer**
   - Business logic
   - Data processing
   - External integrations
   - Caching logic

3. **Data Layer**
   - Database models
   - Data access
   - Migrations
   - Query optimization

## Data Architecture

### Database Schema

```sql
-- Core Tables
CREATE TABLE users (
    id UUID PRIMARY KEY,
    username TEXT UNIQUE,
    password_hash TEXT,
    email TEXT,
    created_at TIMESTAMP
);

CREATE TABLE items (
    id UUID PRIMARY KEY,
    name TEXT,
    category TEXT,
    location TEXT,
    description TEXT,
    purchase_date DATE,
    purchase_price DECIMAL,
    current_value DECIMAL,
    user_id UUID REFERENCES users(id),
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE images (
    id UUID PRIMARY KEY,
    item_id UUID REFERENCES items(id),
    filename TEXT,
    path TEXT,
    created_at TIMESTAMP
);

CREATE TABLE custom_fields (
    id UUID PRIMARY KEY,
    item_id UUID REFERENCES items(id),
    field_name TEXT,
    field_value TEXT,
    created_at TIMESTAMP
);
```

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

1. **Network Security**
   - HTTPS only
   - CORS policy
   - Rate limiting
   - Request validation

2. **Application Security**
   - Input sanitization
   - Output encoding
   - Error handling
   - Logging

3. **Data Security**
   - Encryption at rest
   - Secure backups
   - Access control
   - Audit logging

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

3. **Integration**
   - External APIs
   - Authentication providers
   - Cloud storage
   - Analytics

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