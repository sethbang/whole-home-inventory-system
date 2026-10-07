# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

WHIS (Whole-Home Inventory System) — self-hosted household inventory. FastAPI + SQLite backend, React 19 + TypeScript + Tailwind + Vite PWA frontend. Served over HTTPS only (even in dev).

Current version: **3.3.1** (see `CHANGELOG.md`).

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
python scripts/test_venice_image.py           # smoke test the Venice.ai image-gen endpoint (writes one JPG)
SEED_USER=<u> python scripts/seed_items.py    # seed dev DB with 12 curated items + Venice.ai-generated photos
pytest                                        # run tests (409 tests, all passing on SQLite)
TEST_DATABASE_URL=postgresql+psycopg://... pytest  # run against Postgres (subset — LLM/pricing tests are mock-heavy and SQLite-only)
pytest tests/test_items.py::test_item_crud_round_trip  # single test
pytest --cov=app tests/                       # with coverage
```

### Frontend (from `frontend/`)
```bash
npm run dev             # starts Vite on :5173 (HTTPS). Cert generation now lives in
                        # `bin/whis certs` (host-side). The in-container path of this
                        # script is a deliberate no-op so the SAN can't capture the
                        # container's bridge IP instead of the host's LAN IP.
npm run build           # tsc --noEmit + vite build
npm run lint            # eslint . (0 errors; CI blocks on errors)
npm test                # vitest run (159 tests, all passing)
npm test -- src/path/to/file.test.tsx   # single test file
npm run test:watch      # vitest in watch mode
npm run codegen:api     # regenerate src/api/openapi.d.ts from the backend schema
npm run codegen:check   # fail if the committed openapi.d.ts is out of sync
```

Test config lives in `frontend/vitest.config.ts` (jsdom, globals enabled, setup file at `src/setupTests.ts`, matches `src/**/__tests__/**/*.test.{ts,tsx,js,jsx}`).

### Docker
```bash
./bin/whis up                                       # recommended: auto-detects LAN IP, mDNS, certs
./bin/whis up --profile worker                      # passthrough flag — equivalent of below
./bin/whis nas up                                   # NAS deployment variant (Redis + worker + mdns always on)

# Direct compose still works without the wrapper (CORS_ORIGINS falls back to localhost):
docker compose up --build                           # default: backend + frontend, SQLite, synchronous
docker compose --profile worker up --build          # + Redis + ARQ worker (async job queue)
docker compose --profile postgres up --build        # + Postgres 16
docker compose --profile postgres --profile worker up --build   # full v3.0 stack
docker compose -f docker-compose.nas.yml up -d      # NAS deployment variant
```

Both compose files require `SECRET_KEY` in the shell env or a sibling `.env` file. Generate one with:
```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

`bin/whis` writes `.env.generated` (gitignored) at the repo root with `WHIS_LAN_IP` + `WHIS_MDNS_HOSTNAME`. Compose interpolates these into `CORS_ORIGINS` and the `mdns` sidecar. On macOS the wrapper publishes `whis.local` via `dns-sd -P` (host-side, PID stashed in `.whis-mdns.pid`). On Linux the `mdns` profile activates an avahi-based sidecar with `network_mode: host`.

### CI
GitHub Actions workflow at `.github/workflows/ci.yml` runs on push/PR to `main`:
- `backend` job: pytest (Python 3.11 + 3.12 matrix × SQLite + Postgres matrix = 4 legs). Postgres 16-alpine runs as a service on every leg. `pip-audit --strict` gated to the 3.12/sqlite leg.
- `frontend` job: eslint (blocking), vitest, and `npm audit --omit=dev --audit-level=high`.
- `image-scan` job: builds the backend + Caddy images with buildx + GHA cache, scans both with Trivy. Fails on HIGH/CRITICAL (ignore-unfixed).
- `contract-check` job: regenerates `frontend/src/api/openapi.d.ts` from the live backend schema and fails if the committed file is out of sync.

### Certificates (required — app will not start without them)
```bash
./bin/whis certs           # auto-detects LAN IP, includes <hostname>.local on Mac, drift-checks
# then trust frontend/certs/whis-dev-ca.crt on each device (see README for OS steps)
```
The script also runs cleanly via `cd frontend && node scripts/generate-certs.js`; the wrapper just adds the LAN-IP + extra-SAN env vars. Re-runs are a no-op when the SAN signature in `frontend/certs/.san-signature` still matches and the cert is < 350 days old.

## Architecture

### Request flow
Browser (HTTPS :5173) → Vite dev server → proxies `/api` and `/uploads` to `https://backend:27182` (target overridable via `VITE_BACKEND_URL`) → FastAPI → SQLite at `backend/database/whis.db` *or* Postgres (when `DATABASE_URL=postgresql+psycopg://...`). Heavy endpoints (backup create/restore, thumbnail generation) enqueue into Redis via ARQ when the worker profile is active; the `whis-worker` service picks jobs off the queue. In the NAS deployment (`docker-compose.nas.yml`) Caddy replaces Vite on 80/443 and Redis + worker are always on.

### Backend layout (`backend/app/`)
- `main.py` — FastAPI app factory. Mounts `/uploads` static dir, configures CORS, registers all routers with `prefix="/api"`. **Routers themselves do not include the `/api` prefix** — it is added here. Also defines custom middleware for trailing-slash tolerance and global exception handling. The global handler redacts stack traces from HTTP responses unless `DEBUG=true`.
- `settings.py` — `pydantic-settings`-backed `Settings` singleton. Reads env (and `backend/.env`). Fail-fast: refuses to load if `BYPASS_AUTH=false` and `SECRET_KEY` is unset or matches a known placeholder. All operator-tunable values (BYPASS_AUTH, SECRET_KEY, UPLOAD_DIR, BACKUP_DIR, DATABASE_URL, CORS_*, MAX_UPLOAD_BYTES, MAX_IMAGE_DIMENSION, LOG_LEVEL, DEBUG) flow through this module.
- `models.py` — single-file SQLAlchemy models. Note the custom `UUID` TypeDecorator (stores UUIDs as 36-char strings in SQLite and coerces non-v4 values to v4). Core entities: `User`, `Item`, `ItemImage`, `Backup`.
- `schemas.py` — Pydantic v2 schemas. Uses `model_config = ConfigDict(from_attributes=True)` (migrated from `class Config` in 2.0.0). Use `model_dump()` not `dict()`.
- `database.py` — SQLite engine, configurable via `DATABASE_URL`. **No longer calls `Base.metadata.create_all()` — Alembic is now the sole source of truth for schema.**
- `security.py` — JWT via **PyJWT** (swapped from unmaintained `python-jose` in 2.0.0). All bypass/secret logic is driven by `settings.BYPASS_AUTH` / `settings.SECRET_KEY`. `DEV_USER` and `DEV_USER_ID` still exist for the bypass path.
- `routers/` — one file per resource: `auth`, `items`, `images`, `analytics`, `backups`, `ebay`, `facebook`, `jobs` (v3.0), `vision` + `pricing` (v3.1). Routers are thin — they delegate to `services/` for business logic and ownership enforcement. Upload validation in `images.py` uses Pillow magic-byte verification + `settings.MAX_UPLOAD_BYTES` + `settings.MAX_IMAGE_DIMENSION`. Per-route rate limits via `slowapi` are declared at the router / decorator level.
- `jobs/` — v3.0 ARQ job queue scaffold. `client.py` builds/caches the pool (returns None when `REDIS_URL` is unset so enqueuers fall back to synchronous execution). `worker.py` exports `WorkerSettings` for `arq app.jobs.worker.WorkerSettings`. `tasks/` hosts the task coroutines: `backups.py`, `images.py`, `vision.py` (v3.1), `pricing.py` (v3.1).
- `fts.py` — v3.0 full-text search DDL + helpers. Shared between the Alembic migration (`20260422_0004_items_fts.py`) and the test conftest so tests exercise the real FTS path without re-running migrations per session.
- `llm/` — v3.1 shared LLM layer. `openai_compatible.py` is the sole HTTP client for OpenRouter / Venice.ai / LocalAI / Ollama. `prompts.py` carries the versioned system prompts. `budget.py` is the daily-cost cap guard.
- `schemas_llm.py` — v3.1 Pydantic models for VisionSuggestion, VisionResult, PriceSource, PriceEstimate, PriceEstimateEnvelope. `model_json_schema()` output is handed directly to OpenRouter's `response_format: json_schema` strict mode.
- `vision/` — VisionService orchestrates image → LLM → structured suggestion.
- `pricing/` — PricingService + normalizer + cache + two concrete PriceProvider implementations (EbayBrowseProvider, LLMPricingProvider). aggregate_prices consolidates comparables to P10/P50/P90 (or min/median/max for N < 5).
- `services/` — domain logic extracted from routers in v2.2 (`items`, `backups`, `images`). Each service takes `(db, user)` and owns CRUD + ownership checks.
- `ebay/`, `facebook/` — marketplace subpackages with their own `schemas.py`, `category_mapping.py`, and `formatter.py`. Both are assist-only: eBay emits CSV, Facebook emits copy-paste blocks + Meta Commerce catalog CSV (Meta has no public listing API for individual sellers).
- `alembic/versions/` — migrations. `20260420_0001_baseline.py` is idempotent (checks existing tables/indexes), safe against both fresh DBs and DBs previously bootstrapped via `create_all()`. Later migrations (v2.2 pricing columns, v3.0 Postgres compat, items FTS, image thumbnails) stack on top and use `op.get_bind().dialect.name` for dialect branching where needed.
- `scripts/bootstrap.py` — runtime startup script (invoked by the Dockerfile CMD before uvicorn). Asserts the shared `certs/` volume is populated, clears any unknown Alembic revision stamp (e.g., the pre-2.0.0 `cafb3d2c47a1`), then runs `alembic upgrade head`.
- `tests/` — pytest suite with `conftest.py` that honors `TEST_DATABASE_URL` (defaults to in-memory SQLite + StaticPool). 409 tests on SQLite (v3.1: adds coverage for the LLM client, budget guard, schemas_llm, vision service/router, pricing normalizer/cache/aggregator, and both providers + the pricing service/router; v3.2 adds the LLM-config service/router + capabilities). Postgres matrix runs the subset that doesn't rely on provider mocks.
- Upload dir is `settings.UPLOAD_DIR` (default `./uploads`, overridden to `/app/backend/uploads` in compose).

### Frontend layout (`frontend/src/`)
- `App.tsx` — React Router v7 data router (`createBrowserRouter` + `RouterProvider`). Each route declares a `loader` that warms the React Query cache via `queryClient.ensureQueryData(...)` (see `router/loaders.ts`) so pages render without a loading flash. React Query client lives in `queryClient.ts` (retries=1, no refetch on focus).
- `contexts/AuthContext.tsx` + `useAuth.ts` — split provider/hook pair (v2.4 react-refresh fix). Dev-mode bypass requires **both** `import.meta.env.DEV === true` and `isDevMode === true`; production builds can never bypass regardless of localStorage state.
- `contexts/DevModeContext.tsx` + `useDevMode.ts` — dev-only UI toggle. Gated on `import.meta.env.DEV`; no-op in production builds.
- `api/` — split client: `client.ts` owns the axios instance + `ApiError` class; `items.ts`, `images.ts`, `analytics.ts`, `backups.ts`, `auth.ts`, `ebay.ts`, `facebook.ts`, `jobs.ts` (v3.0) are per-resource modules. `queryKeys.ts` is the hierarchical query-key factory used throughout loaders + `useQuery` calls.
- `api/openapi.d.ts` — generated by `npm run codegen:api` from the backend's `app.openapi()` dump. Committed so CI can diff-check it. Contains every Pydantic schema as a TS type.
- `api/types.ts` — re-exports `openapi.d.ts` schemas as ergonomic shorthands (e.g. `Item`, `Backup`, `JobDetail`). Also the home for the handful of types the backend doesn't emit (auth form shapes, analytics response shapes).
- `pages/` — one file per route (`Dashboard`, `Browse`, `AddItem`, `ItemDetail`, `Reports`, `Backups`, `Settings`, `Login`, `Register`). Each has a colocated `<Name>.schema.ts` Zod schema where relevant. Forms use `react-hook-form` + `@hookform/resolvers/zod` (Formik + Yup were removed in v2.3).
- `components/` — shared UI: `Layout`, `BarcodeScanner` (lazy-loaded, `@zxing/browser`), `CameraCapture`, `CustomFields`, `DataMigration`, `EbayFields`, `FacebookFields`, `FacebookCopyPasteDialog`, `ImageGallery`, `ErrorBoundary` (react-error-boundary wrapper).
- Styling is Tailwind v4 via `@tailwindcss/vite`, config lives in `src/index.css`'s `@theme` block. Two semantic-token groups: **primary** (`primary`, `primary-hover`, `primary-accent`, `primary-subtle`, `primary-subtle-hover`) and **neutrals + status** introduced in v3.3 (`fg`, `muted`, `subtle`, `inverse`, `surface`, `surface-raised`, `surface-muted`, `line`, `line-strong`, `overlay`, plus `danger`/`success`/`warning` with matching `-subtle` variants). The neutral + status tokens swap values inside `:root.dark { ... }` to deliver the Day / Night theme — components must use these tokens rather than `gray-*` / `dark:*` prefixes. `text-white` is intentionally still raw on primary/danger/success surfaces (fixed contrast). No `postcss.config.js` or `tailwind.config.js` — v4 reads config from CSS.
- Theme switcher (Day / Night / System-sync, v3.3) lives in `src/contexts/ThemeContext.tsx` + `useTheme.ts` (split provider/hook, like `DevModeContext`). Persists `mode` to `localStorage['whis-theme']`, applies `.dark` to `<html>`, syncs `<meta name="theme-color">`, and subscribes to `prefers-color-scheme` `change` events when in System-sync. The matching FOUC-prevention inline script in `frontend/index.html` applies the resolved class before React mounts.
- PWA is enabled via `vite-plugin-pwa` with `registerType: 'autoUpdate'`. **Service worker is disabled in dev** (`devOptions.enabled: false`) to prevent stale-asset bugs. Workbox `runtimeCaching` uses a function matcher (`url.pathname.startsWith('/api/')`).

### Data model quirks
- `Item.custom_fields` is a `JSON` column, so custom user-defined fields are denormalized per-item (not a separate `custom_fields` table as the ARCHITECTURE.md SQL snippet historically suggested — that part of the architecture doc is aspirational).
- UUIDs everywhere; the `UUID` TypeDecorator silently replaces any non-v4 UUID with a new v4 — be aware if you pass UUIDs from other sources.
- Images are stored on disk at `settings.UPLOAD_DIR` and referenced by `ItemImage.file_path`; deleting an item cascades to its images (`cascade="all, delete-orphan"`).

### CORS
`CORS_ORIGINS` env var (comma-separated) controls allowed origins. Default dev is HTTPS-only: `https://localhost:5173,https://192.168.1.122:5173`. The NAS compose file derives `CORS_ORIGINS` from `WHIS_DOMAIN` (`https://${WHIS_DOMAIN}`) by default since Caddy serves same-origin; `NAS_ORIGINS` overrides this for operators who front the stack with an additional upstream reverse proxy.

## Known deferred work
- Analytics response models aren't Pydantic yet — those endpoints return plain dicts, so analytics TS types are hand-written in `api/types.ts` (not generated). Migration → typed response_models is future cleanup.
- LLM usage accounting stamps a nominal (zero-token) usage entry for non-LLM provider calls — should thread real numbers back from the provider wrapper. Low priority since only the LLM provider actually costs money.
- Nightly contract test that hits a real LLM to catch provider API drift (gated by a CI secret).

## Conventions

- Python: Black (88 cols), isort, type hints, PEP 8. `logging` module only — no `print()` in server code.
- TS/React: functional components, ESLint flat config (`eslint.config.js`), 80 cols, relative imports preferred.
- Keep router endpoints thin; Pydantic schemas for all request/response shapes.
- When adding a model field: update `models.py`, `schemas.py`, create an Alembic migration, then update the corresponding router and frontend types.
- When touching operator-visible behavior (env vars, Docker, migrations, auth), update `CHANGELOG.md` and `backend/.env.example` / `frontend/.env.example` in the same commit.
