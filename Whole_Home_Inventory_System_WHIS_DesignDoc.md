# Whole-Home Inventory System (WHIS)

**Version:** 3.1.0
**Author:** S. Bang
**Last Updated:** 2026-05-03

## 1. Introduction

### 1.1 Overview

WHIS is a self-hosted platform for managing household inventories. It centralizes item information — descriptions, photos, locations, purchase details, valuations, warranties — into a local database accessible from multiple devices via a web interface. The v3.x line adds optional AI-assisted item identification (vision auto-fill) and resale-value pricing (eBay Browse + LLM with web search), all while keeping inventory data local.

### 1.2 Goals & Objectives

- ✓ **Centralized inventory:** Provide a unified repository for all household item data.
- ✓ **Intuitive interface:** Easy browsing, searching, and filtering — sub-100ms full-text search.
- ✓ **Simplified data entry:** Photo upload, camera capture, barcode scanning, and (v3.1) one-click vision auto-fill.
- ✓ **Customization:** User-defined fields and categories alongside strict-typed marketplace integration data.
- ✓ **Data security & privacy:** Local-first storage, optional LLM kill-switch (`LLM_ALLOW_CLOUD=false` enforces a private LLM host).
- ✓ **Marketplace assist:** v2.3 eBay CSV + Facebook copy-paste; v3.1 eBay Browse-API pricing.

### 1.3 Target Audience

- Homeowners and renters seeking organized inventory management.
- Small businesses tracking equipment and supplies.
- Households preparing for moves, insurance claims, or estate planning.

### 1.4 Non-Goals

- Cloud-managed SaaS deployment.
- Multi-tenant / enterprise-scale offerings (single-user role model only).
- E-commerce listing automation that requires WHIS to act as a user on a marketplace (v3.1 eBay Browse is server-to-server only, not on-behalf-of).

## 2. System Architecture

### 2.1 High-Level Design

WHIS is a client-server application with optional async-job and AI components:

- **Server**: FastAPI on Python 3.11/3.12. Default deployment is single-process; the v3.0 worker profile adds Redis + ARQ for heavy ops (backup, vision, pricing, thumbnails).
- **Client**: React 19 PWA — installable, offline-capable, mobile-optimized.
- **Database**: SQLite by default (zero config) or Postgres 16 (opt-in via `DATABASE_URL`).
- **Network**: Designed for LAN by default. Caddy in the NAS deployment fronts the stack on 80/443 with auto-TLS (Let's Encrypt for public hostnames, Caddy internal CA for `*.local`).

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full topology diagram and architecture decision records.

### 2.2 Components

1. **Backend (Server)**
   - **API**: FastAPI — thin routers delegating to a services/ layer
   - **Database**: SQLite default; Postgres opt-in. Alembic-managed schema (sole source of truth since 2.0.0)
   - **Authentication**: JWT bearer tokens via PyJWT (HS256)
   - **Job queue (v3.0)**: ARQ + Redis (worker profile); sync fallback when `REDIS_URL` is unset
   - **LLM layer (v3.1)**: OpenAI-compatible client; OpenRouter / Venice.ai / Ollama / LocalAI all supported

2. **Frontend (Web Client)**
   - React 19 + TypeScript 5 + Vite 6
   - React Router v7 data router with loaders
   - TanStack Query 5 for server state
   - Tailwind v4 (CSS-first config — no `tailwind.config.js`)
   - PWA via `vite-plugin-pwa`
   - Forms: react-hook-form + zod (Formik+Yup retired in v2.3)
   - Tests: Vitest (Jest retired in v2.4)

3. **Storage**
   - Images: Server filesystem (`UPLOAD_DIR`), with v3.0 thumbnail companion files
   - Backups: Server filesystem (`BACKUP_DIR`), zip archives with full-resolution images
   - Database: SQLite file or Postgres volume

### 2.3 Deployment Model

- **Local dev**: HTTPS-only on `localhost`, both backend and frontend
- **Docker compose (default)**: backend + frontend + SQLite, jobs sync — for casual local testing
- **Docker compose with profiles**: `--profile worker` (Redis + ARQ), `--profile postgres` (PG 16), or both
- **NAS deployment** (`docker-compose.nas.yml`): Caddy fronts the stack; Redis + worker always on; suitable for Synology / TrueNAS / generic Docker host

## 3. Feature Specifications

### 3.1 Core (v1.x – v2.x)

- ✓ **CRUD operations** keyed by UUID
- ✓ **Data fields**: Name, Category, Location, Brand, Model/Serial Number, Barcode, Purchase Date/Price, Current Value, Warranty Expiration, Notes, Custom Fields
- ✓ **Photo support**: Multiple JPEG/PNG/WebP/HEIC images per item, magic-byte-validated
- ✓ **Browsing & searching**: Filter by any field, sort, full-text search (v3.0 FTS5 / tsvector)
- ✓ **Custom fields**: Strict-typed top-level keys (`ebay`, `facebook`) plus free-form `user_defined`
- ✓ **Barcode/QR scanning**: lazy-loaded `@zxing/browser`
- ✓ **Backup/restore**: in-app zip archives, per-user
- ✓ **Reports & analytics**: value-by-category/location, value trends, warranty status, age analysis

### 3.2 Marketplace assist (v2.3)

- ✓ **eBay listing CSV**: per-item or bulk export to Seller Hub-compatible CSV; streamed (no intermediate file)
- ✓ **Facebook Marketplace**: copy-paste blocks for the Marketplace compose UI; Meta Commerce catalog CSV; image zip download

### 3.3 v3.0 — Scale & ops

- ✓ **Postgres support**: opt-in via `DATABASE_URL=postgresql+psycopg://...`; SQLite remains the default
- ✓ **ARQ background jobs**: Redis-backed queue for heavy ops; worker container shares the backend image
- ✓ **Image thumbnails**: server-side generation, served separately from full-res for fast galleries
- ✓ **Items FTS**: SQLite FTS5 / Postgres `tsvector` + GIN, sub-100ms search
- ✓ **OpenAPI codegen**: `frontend/src/api/openapi.d.ts` generated from live backend schema; CI's `contract-check` enforces drift detection

### 3.4 v3.1 — Intelligence (optional, off by default)

- ✓ **Vision auto-fill** (`/api/vision/identify`): photo → LLM → strict-JSON suggestion (name, brand, model, tags, eBay item specifics, FB item specifics). Per-day cost cap.
- ✓ **Pricing** (`/api/pricing/estimate`): item metadata → eBay Browse API (priority) → LLM provider (fallback with `openrouter:web_search`). Returns P10/P50/P90 + sample comparables. 14-day cache.
- ✓ **Privacy kill-switch**: `LLM_ALLOW_CLOUD=false` refuses to start unless `LLM_BASE_URL` resolves to a private host.
- ✓ **Daily cost caps**: per-(user, day) spend ceilings on vision and pricing. Over-cap returns HTTP 402.
- ✓ **eBay Marketplace Account Deletion exemption**: WHIS persists no eBay user data; load-bearing regression test guards the exemption (see [docs/EBAY_INTEGRATION.md](docs/EBAY_INTEGRATION.md)).

## 4. Technology Stack

### Backend
- **Python** 3.11 / 3.12 (CI matrix runs both)
- **FastAPI** (>=0.115)
- **SQLAlchemy 2.x**, **Pydantic v2**, **pydantic-settings**
- **SQLite** (default) or **Postgres 16** (opt-in via `DATABASE_URL`)
- **Alembic** — sole source of truth for schema
- **PyJWT** + **passlib/bcrypt**
- **ARQ** + **Redis** (v3.0; opt-in)
- **OpenAI Python SDK** (v3.1; targets any OpenAI-compatible endpoint)
- **structlog**, **slowapi** per-route rate limiting, **OpenTelemetry** (opt-in)

### Frontend
- **React 19**, **TypeScript 5**, **Vite 6**
- **Tailwind CSS v4** (CSS-first config)
- **React Router v7** (data router)
- **TanStack Query 5**
- **react-hook-form** + **zod**
- **Vitest**, **@testing-library/react**
- **vite-plugin-pwa**
- **`@zxing/browser`** (lazy-loaded)

### Infrastructure
- **Docker Compose** (with profiles)
- **Caddy** (NAS deployment, auto-TLS)
- **GitHub Actions** CI (backend matrix × SQLite/Postgres, blocking ESLint, pip-audit, npm audit, Trivy image scan, contract-check)

## 5. User Interface

### 5.1 Desktop

- ✓ **Dashboard**: overview tiles, recent items, value summaries, bulk export
- ✓ **Item Listing**: grid/list view with thumbnails (v3.0)
- ✓ **Item Detail**: full metadata, image gallery, marketplace tabs (eBay/Facebook), v3.1 pricing chip, "Auto-fill from image" button
- ✓ **Add New Item**: react-hook-form + zod validation; vision auto-fill flow
- ✓ **Reports**: value by category/location, warranty status, age analysis
- ✓ **Backups**: create / list / download / restore
- ⏳ **Accessibility**: WCAG-compliant color contrast, keyboard nav — in progress

### 5.2 Mobile / PWA

- ✓ **Responsive design**: optimized for phone screens
- ✓ **PWA install**: standalone display, app icon, splash
- ✓ **Camera capture**: native camera integration for photos
- ✓ **Barcode/QR scanning**: live camera-based scan
- ✓ **Offline shell**: service worker caches the app shell; read-only graceful degradation

## 6. Security & Privacy

- ✓ Runs on the operator's host; LAN-only by default
- ✓ JWT bearer tokens (PyJWT, HS256) with per-route rate limiting (slowapi)
- ✓ bcrypt password hashing via passlib
- ✓ HTTPS-only in dev and prod (refuses to start without certs)
- ✓ Fail-fast `SECRET_KEY` requirement when `BYPASS_AUTH=false`
- ✓ Pillow magic-byte upload validation with size + dimension caps
- ✓ Privacy kill-switch (`LLM_ALLOW_CLOUD=false`) blocks accidental egress to public LLM hosts
- ✓ Daily LLM cost caps (per-user, per-feature)
- ✓ eBay deletion-exemption regression-tested
- See [SECURITY.md](SECURITY.md) for the full posture; WAF / HSTS / IP-level rate limiting are operator-provided at the reverse proxy.

## 7. Performance & Scalability

- ✓ Indexed queries on routinely-filtered columns
- ✓ FTS5 (SQLite) / `tsvector` + GIN (Postgres) for sub-100ms search at typical inventory sizes
- ✓ ARQ async-by-default for heavy ops (15–60s backups, 3–10s vision/pricing)
- ✓ React Query loaders eliminate page-load flashes
- ✓ Image thumbnails for fast galleries
- ✓ PriceCache 14-day TTL minimizes provider API spend
- Postgres connection pool tuneable via `DB_POOL_*` env vars

## 8. Maintenance & Extensibility

- ✓ Auto-generated OpenAPI spec at `/openapi.json`; UI at `/docs`
- ✓ 336 backend pytest tests on SQLite + Postgres 16
- ✓ 95 vitest tests on the frontend
- ✓ ESLint blocking in CI; `pip-audit --strict`, Trivy image scan, contract-check all blocking
- ⏳ End-to-end tests (Playwright planned)
- ⏳ Coverage gates (currently reported but not failed-under)
- See [TESTING.md](TESTING.md) for the test surface; [DEVELOPMENT.md](DEVELOPMENT.md) for development workflow.

## 9. Roadmap

### Phase 1 (MVP) — ✓ Completed
- ✓ Core CRUD operations
- ✓ Photo upload and storage
- ✓ Basic UI implementation
- ✓ Authentication system

### Phase 2 — ✓ Completed
- ✓ Custom fields system (JSON column on `items`)
- ✓ Advanced search and filtering
- ✓ Barcode/QR code scanning
- ✓ Backend pytest suite + GitHub Actions CI

### Phase 3 — ✓ Completed
- ✓ Backup/restore functionality
- ✓ Reporting features
- ✓ PWA implementation
- ✓ Docker deployment (dev + NAS variants)

### Phase 4 — ✓ Completed (v2.0.0 audit remediation)
- ✓ Env-driven settings, `SECRET_KEY` required, auth bypass off by default
- ✓ Alembic rebaselined (destructive migration replaced with idempotent baseline + `bootstrap.py`)
- ✓ python-jose → PyJWT swap
- ✓ Upload hardening (magic-byte validation, size + dimension caps)
- ✓ React 18 → 19
- ✓ Dead deps removed; BarcodeScanner lazy-loaded

### Phase 5 — Marketplace assist — ✓ Completed (v2.3)
- ✓ eBay Seller Hub CSV export (per-item + bulk)
- ✓ Streaming CSV download (no intermediate disk file)
- ✓ Strict-typed `EbayFields` schema
- ✓ Facebook Marketplace copy-paste + Meta Commerce CSV
- ✓ Image zip download for Facebook upload

### Phase 6 — Scale & operations — ✓ Completed (v3.0)
- ✓ Postgres dialect plumbing + 4-leg CI matrix
- ✓ ARQ background job queue (worker profile)
- ✓ Backup create/restore moved to ARQ
- ✓ Image thumbnail pipeline
- ✓ Items full-text search (FTS5 / tsvector)
- ✓ OpenAPI → TypeScript codegen + contract-check CI gate

### Phase 7 — Intelligence — ✓ Completed (v3.1)
- ✓ Shared LLM layer (`app/llm/`) targeting any OpenAI-compatible provider
- ✓ Vision auto-fill (image → strict-JSON suggestion)
- ✓ Pricing service with eBay Browse API + LLM fallback
- ✓ PriceCache (composite PK: identity_hash + provider; 14-day TTL)
- ✓ LLM usage tracking + daily cost caps (per-user, per-feature)
- ✓ Privacy kill-switch (`LLM_ALLOW_CLOUD=false`)
- ✓ eBay Marketplace Account Deletion exemption + regression test
- ✓ Two-call flow for pricing (research + extraction; works around OpenRouter middleware)
- ✓ Defensive LLM parser (handles upstream-error-in-200 envelopes)
- ✓ Per-feature model override (`LLM_VISION_MODEL`, `LLM_PRICING_MODEL`)

### Future (genuinely not yet implemented)

- End-to-end tests (Playwright)
- Coverage gates in CI
- SQLAlchemy 2.x `select()`-style migration across remaining `db.query()` callsites
- Route-level `errorElement` wiring for every frontend route (a few still rely on the top-level error boundary)
- Analytics endpoints typed via Pydantic response models (currently hand-typed on the frontend)
- Real (non-zero) usage stamping for non-LLM providers (eBay) in the budget table
- Nightly CI contract test against a real LLM endpoint (gated by a CI secret) to catch provider API drift
- eBay Sell APIs (would require reversing the deletion exemption + standing up the callback listener)
- Refresh-token / session-management enhancements
- Plugin / extension architecture for community contributions

## 10. Open-Source

WHIS is released under the MIT License to encourage community contributions and broader adoption.

---

**End of Document**
