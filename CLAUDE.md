# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

WHIS (Whole-Home Inventory System) — self-hosted household inventory. FastAPI + SQLite backend, React 19 + TypeScript + Tailwind + Vite PWA frontend. Served over HTTPS only (even in dev).

Current version: **2.0.0** (see `CHANGELOG.md`).

## Common commands

### Backend (from `backend/`)
```bash
source venv/bin/activate
uvicorn app.main:app --reload --port 27182   # dev server
python scripts/bootstrap.py                   # migrate + reconcile legacy alembic stamps
alembic upgrade head                          # apply migrations (use bootstrap.py if upgrading from <2.0.0)
alembic revision -m "msg"                     # new migration
alembic downgrade -1                          # revert last
python create_dev_user.py                     # seed dev user (only useful when BYPASS_AUTH=false)
pytest                                        # run tests (10 tests, all passing)
pytest tests/test_items.py::test_item_crud_round_trip  # single test
pytest --cov=app tests/                       # with coverage
```

### Frontend (from `frontend/`)
```bash
npm run dev       # regenerates certs, then starts Vite on :5173 (HTTPS)
npm run build     # tsc --noEmit + vite build
npm run lint      # eslint . (47 pre-existing warnings/errors — advisory in CI)
npm test          # jest (19 tests, all passing under React 19)
npm test -- path/to/file.test.tsx   # single test file
```

Test config lives inline in `frontend/package.json` (jest preset `ts-jest`, jsdom, matches `**/__tests__/**/*.test.[jt]s?(x)`). Uses `tsconfig.test.json`.

### Docker
```bash
docker compose up --build                           # full dev stack (backend + frontend on one network)
docker compose -f docker-compose.nas.yml up -d      # NAS deployment variant
```

Both compose files require `SECRET_KEY` in the shell env or a sibling `.env` file. Generate one with:
```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

### CI
GitHub Actions workflow at `.github/workflows/ci.yml` runs pytest (Python 3.11 + 3.12 matrix) and the frontend jest suite on push/PR to `main`. Lint is advisory (continue-on-error) due to 47 pre-existing warnings.

### Certificates (required — app will not start without them)
```bash
cd frontend && node scripts/generate-certs.js
# then trust certs/whis-dev-ca.crt on each device (see README for OS steps)
```

## Architecture

### Request flow
Browser (HTTPS :5173) → Vite dev server → proxies `/api` and `/uploads` to `https://backend:27182` (target overridable via `VITE_BACKEND_URL`) → FastAPI → SQLite at `backend/database/whis.db`. In production the frontend container's nginx serves static assets and proxies to the backend.

### Backend layout (`backend/app/`)
- `main.py` — FastAPI app factory. Mounts `/uploads` static dir, configures CORS, registers all routers with `prefix="/api"`. **Routers themselves do not include the `/api` prefix** — it is added here. Also defines custom middleware for trailing-slash tolerance and global exception handling. The global handler redacts stack traces from HTTP responses unless `DEBUG=true`.
- `settings.py` — `pydantic-settings`-backed `Settings` singleton. Reads env (and `backend/.env`). Fail-fast: refuses to load if `BYPASS_AUTH=false` and `SECRET_KEY` is unset or matches a known placeholder. All operator-tunable values (BYPASS_AUTH, SECRET_KEY, UPLOAD_DIR, BACKUP_DIR, DATABASE_URL, CORS_*, MAX_UPLOAD_BYTES, MAX_IMAGE_DIMENSION, LOG_LEVEL, DEBUG) flow through this module.
- `models.py` — single-file SQLAlchemy models. Note the custom `UUID` TypeDecorator (stores UUIDs as 36-char strings in SQLite and coerces non-v4 values to v4). Core entities: `User`, `Item`, `ItemImage`, `Backup`.
- `schemas.py` — Pydantic v2 schemas. Uses `model_config = ConfigDict(from_attributes=True)` (migrated from `class Config` in 2.0.0). Use `model_dump()` not `dict()`.
- `database.py` — SQLite engine, configurable via `DATABASE_URL`. **No longer calls `Base.metadata.create_all()` — Alembic is now the sole source of truth for schema.**
- `security.py` — JWT via **PyJWT** (swapped from unmaintained `python-jose` in 2.0.0). All bypass/secret logic is driven by `settings.BYPASS_AUTH` / `settings.SECRET_KEY`. `DEV_USER` and `DEV_USER_ID` still exist for the bypass path.
- `routers/` — one file per resource: `auth`, `items`, `images`, `analytics`, `backups`, `ebay`. Upload validation in `images.py` uses Pillow magic-byte verification + `settings.MAX_UPLOAD_BYTES` + `settings.MAX_IMAGE_DIMENSION`.
- `ebay/` — subpackage with its own `schemas.py` and `category_mapping.py` for eBay CSV export (Phase 1; direct API integration is future work).
- `alembic/versions/20260420_0001_baseline.py` — idempotent baseline migration. Checks existing tables/indexes before creating each one, so it is safe against both fresh DBs and DBs previously bootstrapped via `create_all()`.
- `scripts/bootstrap.py` — runtime startup script (invoked by the Dockerfile CMD before uvicorn). Clears any unknown Alembic revision stamp (e.g., the pre-2.0.0 `cafb3d2c47a1`) then runs `alembic upgrade head`.
- `tests/` — pytest suite with in-memory SQLite `conftest.py` (user + `auth_headers` fixtures). Tests: `test_auth.py`, `test_items.py`, `test_images.py`.
- Upload dir is `settings.UPLOAD_DIR` (default `./uploads`, overridden to `/app/backend/uploads` in compose).

### Frontend layout (`frontend/src/`)
- `App.tsx` — React Router v7 routes. All non-auth routes wrapped in `<RequireAuth>` + `<Layout>`. React Query client configured here (retries=1, no refetch on focus). Still on the legacy `<BrowserRouter><Routes>` pattern; `createBrowserRouter` migration is deferred.
- `contexts/AuthContext.tsx` — auth state. Dev-mode bypass requires **both** `import.meta.env.DEV === true` and `isDevMode === true`; production builds can never bypass regardless of localStorage state.
- `contexts/DevModeContext.tsx` — dev-only UI toggle. Gated on `import.meta.env.DEV`; no-op in production builds.
- `api/client.ts` — axios instance + typed request helpers. Exports: `auth`, `items`, `images`, `backups`, `analytics`, `ebay`. `api/ebay.ts` retained for the eBay export endpoints.
- `pages/` — one file per route (`Dashboard`, `AddItem`, `ItemDetail`, `Reports`, `Backups`, `Login`, `Register`).
- `components/` — shared UI: `Layout`, `BarcodeScanner` (lazy-loaded via `React.lazy` in `AddItem.tsx`, uses `@zxing/browser`), `CameraCapture`, `CustomFields`, `DataMigration`, `EbayFields`, `ImageGallery`.
- Forms use Formik + Yup (Formik→RHF migration deferred). Data fetching uses `@tanstack/react-query`. Styling is Tailwind v3 with `@tailwindcss/forms`.
- PWA is enabled via `vite-plugin-pwa` with `registerType: 'autoUpdate'`. **Service worker is disabled in dev** (`devOptions.enabled: false`) to prevent stale-asset bugs. Workbox `runtimeCaching` uses a function matcher (`url.pathname.startsWith('/api/')`) that actually matches API requests; prior regex was broken.

### Data model quirks
- `Item.custom_fields` is a `JSON` column, so custom user-defined fields are denormalized per-item (not a separate `custom_fields` table as the ARCHITECTURE.md SQL snippet historically suggested — that part of the architecture doc is aspirational).
- UUIDs everywhere; the `UUID` TypeDecorator silently replaces any non-v4 UUID with a new v4 — be aware if you pass UUIDs from other sources.
- Images are stored on disk at `settings.UPLOAD_DIR` and referenced by `ItemImage.file_path`; deleting an item cascades to its images (`cascade="all, delete-orphan"`).

### CORS
`CORS_ORIGINS` env var (comma-separated) controls allowed origins. Default is HTTPS-only: `https://localhost:5173,https://192.168.1.122:5173`. The NAS compose file provides `${NAS_ORIGINS:-...}` for overriding once a reverse proxy is added.

## Known deferred work
- `Backups.tsx` and `Reports.tsx` once had 22 broken TS imports — fixed in 2.0.0 by adding `backups` and `analytics` to `api/client.ts`. Runtime behavior of those pages has not been end-to-end verified yet.
- Formik → React Hook Form migration (React 19 strict-mode warnings expected).
- React Router v7 data-router (`createBrowserRouter`) migration.
- `items.py` router service-layer extraction (currently 410+ lines).
- SQLAlchemy 2.x `select()` style migration across routers (currently uses legacy `db.query()`).
- Tailwind v4 evaluation.

## Conventions

- Python: Black (88 cols), isort, type hints, PEP 8. `logging` module only — no `print()` in server code.
- TS/React: functional components, ESLint flat config (`eslint.config.js`), 80 cols, relative imports preferred.
- Keep router endpoints thin; Pydantic schemas for all request/response shapes.
- When adding a model field: update `models.py`, `schemas.py`, create an Alembic migration, then update the corresponding router and frontend types.
- When touching operator-visible behavior (env vars, Docker, migrations, auth), update `CHANGELOG.md` and `backend/.env.example` / `frontend/.env.example` in the same commit.
