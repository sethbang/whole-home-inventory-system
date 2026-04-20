# Changelog

All notable changes to WHIS will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.0.0] - 2026-04-20

Major remediation and modernization release. Addresses the findings of the
2026-04-19 project audit across security, schema hygiene, testability, and
dependency freshness. **Contains breaking changes that require operator
action on upgrade — see _Upgrade notes_ below.**

### Added
- Typed settings module (`backend/app/settings.py`) backed by
  `pydantic-settings`, with fail-fast validation that refuses to start when
  `BYPASS_AUTH=false` and `SECRET_KEY` is unset or a known placeholder.
- `backend/.env.example` and `frontend/.env.example` documenting every
  environment variable.
- Idempotent Alembic baseline migration (`20260420_0001_baseline`) that is
  safe to apply against both fresh databases and databases previously
  bootstrapped via `Base.metadata.create_all()`.
- `backend/scripts/bootstrap.py` reconciles legacy `alembic_version` stamps
  (clears any unknown revision) before running `alembic upgrade head`.
  Container startup (`Dockerfile` CMD) now invokes it in place of a direct
  `alembic upgrade`.
- Server-side image upload hardening: Pillow magic-byte validation, a
  `MAX_UPLOAD_BYTES` cap (default 10 MB) that returns 413, an 8000×8000
  dimension ceiling, and a whitelist of JPEG / PNG / WebP / HEIC formats.
- Backend test suite (`backend/tests/`): `conftest.py` with in-memory SQLite
  + user / `auth_headers` fixtures, and coverage of auth round-trip,
  item CRUD, image upload validation, and token-required endpoints.
- GitHub Actions CI (`.github/workflows/ci.yml`) running pytest against
  Python 3.11 and 3.12 plus frontend lint / test.
- Frontend API modules for `backups` and `analytics` plus their response
  types (`Backup`, `ValueByCategory`, `ValueByLocation`, `WarrantyItem`,
  `ValueTrends`, `WarrantyStatus`, `AgeAnalysis`). The Backups and Reports
  pages had been importing these from `api/client.ts` but they never
  existed — builds failed at esbuild time.
- `VITE_BACKEND_URL` environment variable for overriding the dev-server
  proxy target (enables local-only `npm run dev` without Docker).
- Lazy loading for `BarcodeScanner` via `React.lazy` / `Suspense`. The
  `@zxing/*` bundles (~400 KB gzipped) now load only when the user opens
  the scanner.
- eBay integration (Phase 1): Seller Hub CSV export, category mapping,
  eBay-specific custom fields, and multi-image support for listings.
- Barcode / QR scanning in the Add Item flow.
- Expanded documentation suite (API, security, development workflow,
  testing, architecture, eBay integration).

### Changed
- React upgraded from 18.3.1 to 19.0.0 (and `@types/react` / `@types/react-dom`
  aligned). No `forwardRef` migrations were needed.
- Backend dependencies bumped: FastAPI 0.104 → 0.115, Uvicorn 0.24 → 0.32,
  SQLAlchemy 2.0.23 → 2.0.36, Pydantic 2.5 → 2.10+, pandas 2.1 → 2.2+,
  `python-multipart` 0.0.6 → 0.0.12, `python-dotenv` 1.0.0 → 1.0.1. Pillow
  pinned to `>=10.4,<12`. Alembic pinned (was previously used without being
  listed). Bcrypt pinned to `>=3.2,<4` for passlib 1.7.4 compatibility.
- All Pydantic schemas migrated from `class Config: from_attributes = True`
  to `model_config = ConfigDict(from_attributes=True)`.
- Deprecated Pydantic `regex=` argument in `items.py` replaced with
  `pattern=`.
- Global exception handler no longer leaks stack traces in HTTP responses
  by default. Verbose tracebacks are gated on `DEBUG=true` (dev only);
  production responses are `{"detail": "Internal server error"}`.
- `print()` calls replaced with the `logging` module across `main.py`,
  `routers/auth.py`, `routers/images.py`, `routers/backups.py`, and
  `routers/items.py`. Password length, verification result, and login
  success logs were removed entirely.
- `UPLOAD_DIR` and `BACKUP_DIR` are now sourced from settings instead of
  being hardcoded to `/app/backend/uploads` in two separate files.
- PWA service worker disabled in development
  (`devOptions.enabled: false`) to eliminate stale-asset bugs between dev
  sessions.
- Workbox `runtimeCaching.urlPattern` changed from the never-matching
  `/^https:\/\/api\.*/i` regex to a function matcher that actually
  matches runtime `/api/*` requests.
- `docker-compose.yml` now wires `BYPASS_AUTH`, `SECRET_KEY`, `UPLOAD_DIR`,
  `BACKUP_DIR`, `DEBUG`, and `LOG_LEVEL` through to the backend container,
  and fixes the broken `./backend/backend/uploads` double-prefix volume
  path.
- `docker-compose.nas.yml` aligned with the new settings contract:
  `BYPASS_AUTH=false` hardcoded, `SECRET_KEY` required via env,
  `DATABASE_URL` absolute, HTTPS-only CORS defaults with `NAS_ORIGINS`
  override.
- Backend Dockerfile CMD now runs `scripts/bootstrap.py` before exec'ing
  uvicorn, so container starts survive legacy Alembic stamps.
- `alembic/env.py` cleaned up (duplicate imports removed; explicit
  `import app.models` added so autogenerate sees the metadata).

### Fixed
- **Critical:** Alembic migration `cafb3d2c47a1_initial.py` dropped every
  table in `upgrade()` — running `alembic upgrade head` against any
  populated database was a data-loss event. Replaced with an idempotent
  baseline (`20260420_0001_baseline`).
- **Critical:** `BYPASS_AUTH = True` hardcoded in `security.py` meant
  auth was off by default; shipping required a code change, not a config
  change. Now env-gated via settings.
- **Critical:** `SECRET_KEY = "your-secret-key-stored-in-env"` — a
  placeholder string was the actual JWT signing key. Now required from
  env with placeholder rejection.
- **Critical:** Global exception handler returned full stack traces
  (file paths, line numbers, code snippets) in HTTP 500 response bodies.
- File uploads accepted any bytes with a spoofable `image/*` content type,
  had no size cap, and no dimension cap. Now validated by Pillow magic
  bytes, capped at 10 MB, and checked against an 8000×8000 ceiling.
- Frontend `DevModeContext` persisted `isDevMode=true` in localStorage
  across sessions and was not gated on `import.meta.env.DEV`. A production
  build honoring a stale localStorage flag would have bypassed auth.
  Now gated on dev builds only; the provider is a no-op in production.
- `backups.py` defined its own `get_db()` instead of importing from
  `database`; also had debug prints on every session lifecycle event.
  Removed the duplicate and the prints.
- Restore flow wrote to `os.path.join("backend", "uploads", …)` (relative
  to CWD) instead of the configured upload directory. Now uses
  `settings.upload_path`.
- Broken imports in `Backups.tsx` and `Reports.tsx` (`backups`,
  `analytics`, `Backup`, `ValueByCategory`, `ValueByLocation`,
  `WarrantyItem`) — referenced exports that never existed in
  `api/client.ts`. Both pages now typecheck and build.
- Pre-existing TypeScript error count dropped from 22 to 0.
- `docker-compose.yml` volume path `./backend/backend/uploads`
  (double-prefix) corrected to `./backend/uploads`.

### Security
- JWT library swapped from unmaintained `python-jose==3.3.0` (last
  release 2022, open algorithm-confusion CVEs) to actively maintained
  `pyjwt[crypto]==2.9.0`.
- CORS defaults restricted to HTTPS origins only. HTTP variants of
  `localhost:5173` / `192.168.1.122:5173` removed from defaults.
- Backend `ACCESS_TOKEN_EXPIRE_MINUTES` is now settings-driven rather
  than duplicated between `security.py` constant and `auth.py` import.
- Login endpoint (`/api/token`) no longer logs the submitted username or
  password length; successful / failed attempt details reduced to a
  structured log line without sensitive payloads.
- `DEBUG=true` (verbose exception responses) no longer possible without
  explicit operator opt-in.

### Removed
- `python-jose[cryptography]` dependency.
- `sharp` (~30 MB native binary) — was in frontend `dependencies` but
  never imported.
- `jszip` — was in frontend `dependencies` but never imported.
- Hardcoded `BYPASS_AUTH = true` constant in `frontend/src/api/client.ts`
  (dead code).
- `Base.metadata.create_all()` calls in both `database.py` and `main.py`.
  Alembic is now the single source of truth for schema state.
- The `cafb3d2c47a1_initial` Alembic migration (destructive — see
  _Fixed_).

### Upgrade notes
1. **Create a `SECRET_KEY`.** On any host that will run the backend
   without `BYPASS_AUTH=true`:
   ```
   python -c "import secrets; print(secrets.token_urlsafe(64))"
   ```
   Put the value in `backend/.env` (for local dev) and/or the project-root
   `.env` (for `docker compose`). Copy `backend/.env.example` as a starting
   template.
2. **Existing databases are auto-reconciled.** The first container start
   after upgrade runs `scripts/bootstrap.py`, which clears any leftover
   `cafb3d2c47a1` stamp and runs the idempotent baseline migration. No
   manual `alembic stamp` step required.
3. **Frontend deps:** run `npm install` in `frontend/` to pick up React 19
   and purge the removed `sharp` / `jszip` modules.
4. **Docker:** `docker compose up --build` (or
   `docker compose -f docker-compose.nas.yml up --build -d` on the NAS).
   Both compose files now require `SECRET_KEY` in the shell / `.env`
   environment and will refuse to start without it.
5. **Frontend dev outside Docker:** set
   `VITE_BACKEND_URL=https://localhost:27182` in `frontend/.env` so the
   Vite proxy targets the local backend instead of the docker service
   hostname.

## [1.3.0] - 2024-12-19

### Added
- Custom fields system for items
- Advanced search and filtering capabilities
- Automated backup system
- Image gallery with multi-select
- Data migration tools
- Analytics dashboard

### Changed
- Improved mobile responsiveness
- Enhanced security measures
- Optimized database queries
- Updated UI components
- Refined error messages

### Fixed
- Authentication token refresh
- Image upload handling
- Search performance
- Date handling in forms
- Category management

## [1.2.0] - 2024-11-15

### Added
- Progressive Web App (PWA) support
- Offline functionality
- Camera integration for photos
- Multi-device synchronization
- Export functionality

### Changed
- Updated React components
- Improved TypeScript types
- Enhanced error handling
- Optimized image processing
- Refined user interface

### Fixed
- Login persistence
- Form validation
- Image caching
- Search functionality
- Date formatting

## [1.1.0] - 2024-10-01

### Added
- Multiple image support per item
- Advanced filtering options
- Batch operations
- Quick add functionality
- Basic analytics

### Changed
- Improved database schema
- Enhanced security features
- Updated UI/UX design
- Optimized API responses
- Better error handling

### Fixed
- Authentication issues
- Data validation
- Image upload bugs
- Search performance
- Mobile layout issues

## [1.0.0] - 2024-09-01

### Added
- Initial release
- Basic CRUD operations for items
- User authentication
- Image upload
- Search functionality
- Category management
- Location tracking
- Basic reporting
- SQLite database
- FastAPI backend
- React frontend
- Docker support
- Basic documentation

### Security
- JWT authentication
- Password hashing
- Input validation
- HTTPS support
- File upload validation

## Types of Changes

- `Added` for new features
- `Changed` for changes in existing functionality
- `Deprecated` for soon-to-be removed features
- `Removed` for now removed features
- `Fixed` for any bug fixes
- `Security` for vulnerability fixes

## Versioning

WHIS follows semantic versioning:
- MAJOR version for incompatible API changes
- MINOR version for added functionality in a backward compatible manner
- PATCH version for backward compatible bug fixes

## Issue References

Each change links to relevant GitHub issues where applicable:
- Issue #123: Feature description
- PR #456: Change description

## Upgrade Guide

### Upgrading to 1.3.0
1. Backup your database
2. Update dependencies
3. Run database migrations
4. Clear browser cache
5. Update configuration

### Upgrading to 1.2.0
1. Install new dependencies
2. Update environment variables
3. Run database migrations
4. Clear application cache
5. Verify PWA setup

### Upgrading to 1.1.0
1. Backup existing data
2. Update application files
3. Run database migrations
4. Verify image storage
5. Test new features

## Breaking Changes

### Version 1.3.0
- Custom fields schema changes
- API endpoint modifications
- Authentication flow updates

### Version 1.2.0
- PWA implementation requirements
- Database schema updates
- API response format changes

### Version 1.1.0
- Multiple image handling changes
- Database structure updates
- API endpoint modifications

## Deprecation Notices

### Version 1.3.0
- Legacy search endpoints
- Old backup format
- Previous image storage method

### Version 1.2.0
- Single image per item
- Basic search functionality
- Simple backup system

## Future Plans

### Version 1.4.0 (Planned)
- AI-powered categorization
- Enhanced analytics
- Mobile applications
- Cloud integration options
- Plugin system
- eBay integration Phase 2
  - Direct API integration
  - Real-time sync
  - Order management
  - Automated listing

### Version 1.5.0 (Planned)
- Value tracking
- Insurance integration
- Home automation
- Extended API
- Enhanced security

## Support Policy

- Latest version: Full support
- Previous version: Security updates
- Older versions: No support

## Reporting Issues

Please report issues via:
1. GitHub Issues
2. Security vulnerabilities: security@example.com
3. Documentation issues: docs@example.com

## Contributing

See CONTRIBUTING.md for:
- How to submit changes
- Coding standards
- Commit message format
- Pull request process