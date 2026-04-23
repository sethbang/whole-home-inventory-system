# Changelog

All notable changes to WHIS will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Four fixes surfaced by the v3.1 pre-push validation pass. All four ship
together — the restore path fix is a data-loss guard that must land before
any Postgres deployment takes real traffic.

### Fixed

- **Postgres backup restore no longer crashes on users with images**
  (`services/backups.py::commit_restore`). The bulk
  `DELETE FROM items WHERE owner_id=...` (`synchronize_session=False`)
  bypasses SQLAlchemy's ORM cascade, and the `item_images.item_id`
  foreign key had no `ON DELETE CASCADE` — so Postgres correctly
  rejected the delete with `ForeignKeyViolation` the instant any user
  had one image. SQLite masked it because SQLite doesn't enforce FKs
  unless `PRAGMA foreign_keys=ON`. Fix is two-layer: (1) new Alembic
  migration `20260423_0008_item_images_cascade` that promotes the FK
  to `ON DELETE CASCADE` on both dialects, and (2) service-layer
  delete now removes `item_images` rows before `items` rows as
  belt-and-suspenders. The ORM's `ForeignKey("items.id")` declaration
  in `models.py` carries `ondelete="CASCADE"` for autogenerate
  fidelity.
- **Backup archives actually contain uploaded images again**
  (`services/backups.py::_write_backup_file`). The file-existence check
  was resolving `ItemImage.file_path` (a relative URL-style
  `uploads/<filename>`) directly from CWD instead of joining with
  `settings.upload_path`. The check always missed, so every backup
  silently shipped with zero images and restores had nothing to copy
  back. New backups contain the images; old 670-byte backups should be
  recreated.
- **New regression test** `test_backup_create_and_restore_round_trip_with_images`
  writes a real JPEG to disk, creates a backup, verifies the zip
  contains the bytes, wipes state, restores, and verifies both the DB
  rows and the file content round-trip. Fills the gap in
  `test_restore_commit_with_correct_confirm_proceeds` which used
  `images: []` and missed both bugs.
- **Backend compose service now waits for Postgres/Redis health**
  (`docker-compose.yml`, `docker-compose.nas.yml`). Booting the dev
  stack with `--profile postgres` or `--profile worker` used to race
  the DB/Redis startup — backend crashed on `connection refused` if
  its dependency was still initializing. Added `depends_on` with
  `condition: service_healthy`; the default compose file uses
  `required: false` (Compose v2.20+) so the dev stack still boots
  without those profiles.
- **Compose env blocks now propagate every operator-visible setting**
  to both `backend` and `worker` containers
  (`docker-compose.yml`, `docker-compose.nas.yml`). The v3.1 release
  documented `VISION_ENABLED=true` + LLM creds in `.env` as the way
  to turn on vision/pricing, but neither compose file listed those
  vars in its `environment:` block — so the vars were consumed only
  for YAML substitution and never reached the container. The v3.1
  intelligence layer was therefore **permanently off in any
  docker-compose deployment** regardless of what the operator put
  in `.env`. Same leak silenced `LLM_ALLOW_CLOUD`,
  `VISION_DAILY_COST_CAP_USD`, `PRICING_DAILY_COST_CAP_USD`,
  `EBAY_APP_ID`/`EBAY_CERT_ID`, plus `LOG_FORMAT`, `OTEL_*`,
  `MAX_UPLOAD_BYTES`, `MAX_IMAGE_DIMENSION`, and the Postgres
  `DB_POOL_*` knobs. Every one of these is now plumbed through.
  The worker block is kept in lockstep with the backend's so
  fail-fast guards and feature-flagged tasks behave identically
  on both sides.

### Security

- **python-dotenv bumped to >=1.2.2,<2** to resolve
  **CVE-2026-28684** (previously pinned at 1.0.1). CI's
  `pip-audit --strict` leg would otherwise block the push.

## [3.1.0] - 2026-04-23

Vision auto-fill + item-value pricing. Two feature-flagged
intelligence layers that ride on v3.0's ARQ queue and shared
type contract.

Both features default OFF and are fail-fast-gated — the default
`docker compose up` posture is unchanged.

### Added

- **Shared LLM layer** (`backend/app/llm/`). OpenAI-compatible
  client (works with OpenRouter / Venice.ai / LocalAI / Ollama)
  with three hard-wired features:
  - **OpenRouter structured outputs**
    (`response_format: json_schema`, `strict: true`). Model output
    is schema-valid by construction — no "permissive JSON extractor"
    heuristic. Pydantic is called on the response as
    defense-in-depth.
  - **Response Healing plugin** (`plugins: [{id: 'response-healing'}]`)
    enabled on every structured call as a zero-cost safety net for
    truncation / markdown wrappers / trailing commas.
  - **Server-side `openrouter:web_search` tool** for pricing.
    Replaces the previously-planned custom SearchProvider
    abstraction entirely — OR decides when to search, executes
    via Exa/Parallel/native, returns grounded results.
- **LLM-facing JSON Schemas** (`backend/app/schemas_llm.py`).
  Single Pydantic source for VisionSuggestion, VisionResult,
  PriceSource, PriceEstimate, PriceEstimateEnvelope.
  `model_json_schema()` hands the same contract to OR;
  `openapi-typescript` hands it to the frontend. No drift.
- **Daily LLM budget cap** (`backend/app/llm/budget.py` +
  `20260422_0006_llm_usage.py` migration). Per-(user, day,
  feature) rollup of tokens + cost. Caps from
  `VISION_DAILY_COST_CAP_USD` / `PRICING_DAILY_COST_CAP_USD`
  return HTTP 402 when exceeded. Cost estimation via a small rate
  table (gemini-2.5-flash, claude-sonnet-4.6, gpt-4o) with a
  conservative $2/$10 fallback for unknown models.
- **Vision auto-fill** (`backend/app/vision/`,
  `/api/vision/identify`, `VisionSuggestionPanel` +
  `VisionIdentifyButton`). Photograph one or more shots of an
  item, receive structured metadata (name, brand, model,
  condition, year, dimensions, suggested_tags, ebay/fb item
  specifics) with per-field confidence. Field-by-field
  checkboxes let the user accept selectively. Sync + ARQ async
  paths both supported; image upload rejects bad magic bytes
  up-front so bad uploads don't enqueue a doomed job. Image
  content NEVER logged — only sha256 hashes when
  `VISION_LOG_IMAGE_HASHES_ONLY=true` (the default).
- **Item-value pricing** (`backend/app/pricing/`,
  `/api/pricing/{estimate,refresh/{id},estimate/{id}}`,
  `PriceEstimateCard`). Two providers:
  - **eBay Browse API** — OAuth client-credentials flow, in-memory
    token cache, `/buy/browse/v1/item_summary/search`. Results
    aggregated via P10/P50/P90 when sample≥5, min/median/max below
    that. Drops zero-priced Best Offer placeholders.
  - **LLM with OR web_search** — Pricing prompt + schema +
    `use_web_search=True`. Model researches, cites, returns strict
    JSON. Web search usage logged for cost tracking.
  Providers tried in `PRICING_PROVIDERS` priority order. Cache
  layer keyed `(identity_hash, provider)` with 14-day TTL +
  60-day stale fallback (decayed confidence) when providers are
  rate-limited. When an `item_id` is given, the item's
  `estimated_value_low/median/high + price_last_checked +
  price_provider` columns (v2.2 pre-wire) are stamped.
- **Vision → Pricing chain** on `AddItem`. After the user applies
  a vision suggestion with brand + model_number, the form fires
  a metadata-based pricing estimate and renders a PriceEstimateCard
  with "Apply median as current value" wired to the form input.
- **"AI filled" chip banner** that tracks vision-sourced fields
  and clears on user edit via a RHF `watch` subscription.
- **Rate limiting** on `POST /api/pricing/refresh/{id}` at
  5/minute/user (slowapi) so accidental loops can't DOS eBay or
  burn through the LLM quota.
- **LLM_ALLOW_CLOUD privacy kill-switch**. When false, the app
  refuses to start if LLM_BASE_URL resolves to anything other
  than localhost / 127.0.0.0/8 / 10/8 / 172.16/12 / 192.168/16 /
  the known container hostnames (ollama, host.docker.internal).
  Belt-and-suspenders guard for operators running local-only
  setups.

### Changed

- `backend/app/routers/backups.py`, `backup_restore` service
  layer untouched from v3.0 (no behavior change — listed here so
  the changelog is readable as a whole).
- `backend/app/jobs/worker.py`: task registry grows to include
  `vision_identify` and `pricing_refresh`.
- `backend/app/models.py`: `PriceCache` PK promoted to composite
  `(identity_hash, provider)` via migration
  `20260422_0007_price_cache_composite_pk`. v2.2 provisioned the
  table with single-column PK; v3.1 is the first release to
  populate it, so the swap is safe to do without data migration.
  SQLite path uses `batch_alter_table(recreate="always")`;
  Postgres does a DROP/ADD CONSTRAINT.
- `backend/app/models.py`: new `LLMUsage` table for the budget
  rollup.
- `backend/requirements.txt`: `openai>=1.57,<2` added (other
  v3.1 deps — httpx + tenacity — were pre-wired in v3.0).

### Test counts

- Backend: **315 tests** passing on SQLite (up from 297 in v3.0).
  New coverage: LLM client (8), LLM schemas (9), settings gates
  (18), budget guard (8), vision service (7), vision router (7),
  pricing normalizer (13), pricing cache (7), pricing aggregator
  (9), pricing providers (11), pricing service (10), pricing
  router (8).
- Frontend: **95 tests** — no new tests this release; the new
  components are covered by end-to-end smoke via the dev server
  (vision + pricing flows exercised manually).

### Settings added

Shared LLM layer:
- `LLM_BASE_URL` (default empty)
- `LLM_API_KEY` (default empty)
- `LLM_MODEL` (default `google/gemini-2.5-flash`)
- `LLM_PRICING_MODEL` (defaults to LLM_MODEL if blank)
- `LLM_TIMEOUT_SECONDS` (default 90)
- `LLM_ALLOW_CLOUD` (default true)
- `LLM_RESPONSE_HEALING` (default true)

Vision:
- `VISION_ENABLED` (default false)
- `VISION_MAX_IMAGES_PER_REQUEST` (default 4)
- `VISION_DAILY_COST_CAP_USD` (default 5.0)
- `VISION_LOG_IMAGE_HASHES_ONLY` (default true)

Pricing:
- `PRICING_ENABLED` (default false)
- `PRICING_PROVIDERS` (CSV, default `ebay,llm`)
- `PRICING_CACHE_DAYS` (default 14)
- `PRICING_MAX_SAMPLES` (default 30)
- `PRICING_MULTIPROVIDER` (default false)
- `PRICING_DAILY_COST_CAP_USD` (default 5.0)
- `PRICING_WEB_SEARCH_MAX_RESULTS` (default 5)
- `PRICING_WEB_SEARCH_MAX_TOTAL` (default 20)
- `PRICING_WEB_SEARCH_DOMAINS` (CSV, default `ebay.com,mercari.com,bonanza.com`)

eBay Browse API:
- `EBAY_APP_ID`, `EBAY_CERT_ID` (both empty by default)
- `EBAY_MARKETPLACE_ID` (default `EBAY_US`)
- `EBAY_ENVIRONMENT` (default `production`; `sandbox` also valid)

### Migration notes

- `alembic upgrade head` applies migrations 0006 + 0007. Both are
  cross-dialect; both are safe on populated DBs (0006 adds a new
  table, 0007 reshuffles the PK of a table that's empty in v3.0
  production deployments).
- Enabling vision/pricing requires setting `LLM_BASE_URL` +
  `LLM_API_KEY` + flipping the feature flag. Without these the
  startup fail-fast guard refuses to boot — by design.

## [3.0.0] - 2026-04-22

Platform leap. No new product surface — v3.0 builds the substrate that
v3.1's Vision + Pricing features will ride on: an optional Postgres
path alongside the SQLite default, full-text search replacing the
5-column ILIKE fan-out, an ARQ job queue that moves 15-45s blocking
operations off the request thread, a thumbnail pipeline, and a shared
OpenAPI → TypeScript type contract so schema changes can't silently
break the frontend.

### Added

- **Postgres as an opt-in database** (`DATABASE_URL=postgresql+psycopg://...`).
  SQLite stays the default — operators graduate by setting
  `DATABASE_URL` and running `docker compose --profile postgres up`.
  The backend image ships `psycopg[binary]>=3.2,<4` for both
  dialects (~5MB overhead).
- **Postgres compat migration** (`20260422_0003_postgres_compat.py`).
  On Postgres, promotes `items.custom_fields` + `price_cache.payload`
  to JSONB and adds a GIN index on `items.custom_fields`. No-op on
  SQLite.
- **Full-text search** — `20260422_0004_items_fts.py` +
  `app/fts.py`. SQLite gets an FTS5 virtual table `items_fts` fed by
  three triggers; Postgres gets a `search_tsv` tsvector column with
  a GIN index and a BEFORE-INSERT-OR-UPDATE trigger.
  `ItemService.list()` dispatches on dialect at query time. User
  input sanitized via `_sanitize_fts5` (FTS5 phrase quoting) on the
  SQLite path; `plainto_tsquery('english', ...)` on Postgres.
- **ARQ job queue** (`app/jobs/` package) —
  [arq](https://github.com/python-arq/arq)-backed async worker,
  profile-gated so the default dev stack stays unchanged:
  - `docker compose up` — SQLite + synchronous, as before.
  - `docker compose --profile worker up` — Redis + ARQ worker boot
    alongside; heavy endpoints enqueue instead of blocking.
  - `docker compose --profile postgres --profile worker up` — full
    v3.0 stack.
  NAS (`docker-compose.nas.yml`) runs Redis + worker unconditionally.
- **`GET /api/jobs/{job_id}`** router with ownership guard (cross-
  user reads return 404, not 403, to avoid leaking existence).
  Lifecycle states: `queued / running / complete / failed /
  not_found`. Returns 503 when no pool is configured.
- **Backup create + restore as ARQ tasks**. `POST /api/backups` and
  `POST /api/backups/{id}/restore` (commit) return
  `Union[JobReference, Backup|RestoreResponse]` — the frontend
  branches on a `kind: "job"` discriminator and polls
  `GET /api/jobs/{id}` until the status is terminal. Falls back to
  synchronous execution when the pool isn't active.
- **Thumbnail pipeline** (`20260422_0005_image_thumbnails.py`).
  `ItemImage` gains `thumbnail_path` + `thumbnail_generated_at`.
  Upload handler enqueues a `thumbnail_generate` ARQ task
  (fire-and-forget); the worker generates a 512×512 WebP at
  quality 82, respects EXIF rotation, saves as `thumb_<stem>.webp`.
  Frontend `ImageGallery` prefers the thumbnail when populated.
  Without the worker profile the same helper runs inline.
- **OpenAPI → TypeScript codegen**. `backend/scripts/dump_openapi.py`
  emits the schema; `frontend/scripts/generate-api-types.mjs` pipes
  it through `openapi-typescript` to produce
  `frontend/src/api/openapi.d.ts` (committed).
  `frontend/src/api/types.ts` re-exports the schemas as ergonomic
  shorthands. `hand-written frontend/src/types/` was deleted — 16
  call sites migrated to `../api/types`.
- **CI contract-check job** — regenerates `openapi.d.ts` on every PR
  and fails the build if the committed file is out of sync with
  `schemas.py`.
- **CI Postgres matrix leg** — backend job now runs
  `python-version: [3.11, 3.12] × database: [sqlite, postgres]` =
  four green legs. Postgres 16-alpine runs as a GitHub Actions
  service.

### Changed

- `backend/app/main.py` — FastAPI `lifespan` context manager creates
  the ARQ pool at startup, stashes on `app.state.arq`, closes on
  shutdown. Same hook point v3.1's Vision + Pricing features will
  use.
- `backend/app/services/backups.py` — factored restore preflight
  (ownership + confirm_item_count match) into
  `validate_restore_request` so the router can reject bad requests
  synchronously instead of burying failures inside a worker job.
- `backend/app/services/images.py` — added `generate_thumbnail` +
  delete-cleanup for the companion thumbnail file.
- `backend/app/database.py` — engine construction is dialect-aware;
  Postgres gets `pool_pre_ping + pool_size + max_overflow +
  pool_recycle` tuning. Guards the common `postgresql://` (psycopg2,
  not installed) vs `postgresql+psycopg://` mistake with an
  actionable error.
- `backend/alembic/versions/20260420_0001_baseline.py` — swapped
  the `sqlite.JSON()` import/usage for `sa.JSON()` so baseline
  applies cleanly on Postgres.
- `backend/tests/conftest.py` — `TEST_DATABASE_URL` env var drives
  the test engine. Default stays in-memory SQLite with StaticPool;
  set to a `postgresql+psycopg://` URL to exercise the PG leg
  locally.
- Frontend `Backups.tsx` — create + restore flows detect
  `JobReference` responses, show a progress banner, and poll via
  the new `useJobPoll` hook.
- `frontend/src/api/queryKeys.ts` — new `jobs` branch.

### Removed

- `frontend/src/types/` directory. All TS types that mirror a
  backend Pydantic schema now come from the generated
  `frontend/src/api/openapi.d.ts`.

### Test counts

- Backend: **200 tests** passing on both SQLite and Postgres 16
  (up from 161 in v2.4). New coverage: FTS (11), DB compat (4),
  jobs endpoint (10), async backups (7), thumbnails (7).
- Frontend: **95 tests** passing (up from 90). 5 new tests cover
  the `isJobReference` type guard.

### Settings added

- `DB_POOL_SIZE` (default 5), `DB_MAX_OVERFLOW` (10),
  `DB_POOL_RECYCLE_SECONDS` (1800) — honored on Postgres, ignored
  on SQLite.
- `REDIS_URL` (default empty). When unset, service-layer enqueuers
  fall back to synchronous execution.

### Migration notes

- `alembic upgrade head` applies 0003-0005 in sequence. Safe to run
  on an existing SQLite DB with data (all migrations are idempotent
  and use `batch_alter_table` where needed). Safe to run on a fresh
  Postgres DB.
- Operators wanting the async job queue must generate a new
  `SECRET_KEY` (unchanged) and add `REDIS_URL=redis://redis:6379/0`
  to their `.env`, then restart with `--profile worker`.

## [2.4.0] - 2026-04-21

Ops + style release. No new product surface — this release hardens the
deployment story (non-root containers, healthchecks, Caddy with
auto-TLS), modernizes the toolchain (Tailwind v4 semantic tokens,
Vitest, mkcert-aware certs), and flips CI's security gates on
(pip-audit, npm audit, Trivy, blocking lint). All four ambiguous
choices from the v2.3 retrospective were committed to the ambitious
option: semantic Tailwind tokens, Caddy + LE, full Jest → Vitest, and
a typing pass that brought ESLint to 0 errors.

### Added

- **Caddy reverse proxy for NAS deployments** (`Caddyfile` at repo
  root). Replaces the nginx image. Auto-provisions Let's Encrypt
  certs when `WHIS_DOMAIN` resolves publicly; falls back to Caddy's
  internal CA on the `whis.local` default. Emits HSTS, CSP, nosniff,
  X-Frame-Options, and Referrer-Policy headers on every response.
  Same-origin `/api/*` + `/uploads/*` reverse proxy to the backend on
  the internal docker network.
- **HEALTHCHECK on every service** (both compose files). `depends_on`
  with `condition: service_healthy` gates the frontend on a ready
  backend.
- **mkcert-aware dev cert generator** (`frontend/scripts/generate-certs.js`).
  Detects mkcert on `PATH` and uses it for system-trusted certs; falls
  back to the legacy OpenSSL CA flow when mkcert isn't available.
  Container check (`/.dockerenv`) skips `mkcert -install` inside
  containers where there's no host trust store.
- **Backend cert-existence guard** in `bootstrap.py` — fails fast with
  an actionable message when the shared certs volume is empty,
  instead of cascading into a cryptic uvicorn SSL handshake error.
- **Tailwind v4 semantic design tokens** in `frontend/src/index.css`
  via `@theme`. Palette consolidated to `primary`, `primary-hover`,
  `primary-accent`, `primary-subtle`, `primary-subtle-hover` — 106
  class occurrences across 15 files migrated.
- **Vitest** replaces Jest + ts-jest across all 16 frontend test
  files. Runtime dropped from ~6.5s to ~3.3s; ESM-native, so
  `import.meta.env.DEV` works directly (the v2.1 `NODE_ENV`
  workaround in `src/lib/logger.ts` is gone).
- **CI security gates**:
  - `pip-audit --strict` on `backend/requirements.txt` (Python 3.12
    matrix leg).
  - `npm audit --omit=dev --audit-level=high` on runtime frontend
    deps.
  - `aquasecurity/trivy-action` scans the built backend + Caddy
    images; fails on CRITICAL/HIGH, `ignore-unfixed` so unpatched
    upstream CVEs don't permanently block.
- **.github scaffolding**: `CODEOWNERS`, `pull_request_template.md`,
  `ISSUE_TEMPLATE/{bug_report,feature_request}.md`.

### Changed

- **Dockerfiles hardened**: backend image is multi-stage (deps in a
  venv stage, runtime stage is python:3.11-slim with a non-root
  `whis` user at uid 1000). Frontend dev image runs as `USER node`.
  Both drop the baked-in cert generation — certs come from a shared
  volume now.
- **`docker-compose.nas.yml`**: frontend service replaced with a
  `caddy` service on 80/443 (+443/udp for HTTP/3). Persists
  `/data` + `/config` to preserve ACME state across rebuilds.
  `CORS_ORIGINS` now derives from `WHIS_DOMAIN` by default.
- **CI lint gate flipped**: the 31 ESLint findings from v2.3 were
  resolved in a typing pass (proper types on `BarcodeScanner`,
  `CameraCapture`, `DataMigration`, `CustomFields`, `EbayFields`;
  `AuthContext` / `DevModeContext` split into provider + hook files;
  `useCallback` wrapping on camera lifecycle helpers).
  `continue-on-error: true` is gone from the CI lint step.
- **Bumped backend deps to patch 8 pip-audit findings**:
  `python-multipart 0.0.12 → >=0.0.26`,
  `pyjwt 2.9.0 → >=2.12.0`,
  widened `pillow` to `<13` so `>=12.2.0` resolves,
  explicit `starlette>=0.49.1` pin.
- **Bumped transitive npm pins via `npm audit fix`** to patch 5
  runtime CVEs (axios / form-data / react-router).

### Removed

- `frontend/nginx.conf` — Caddy replaces it.
- `backend/scripts/generate-certs.py` — the unified
  `frontend/scripts/generate-certs.js` script is now the single
  source of dev certs.
- `frontend/postcss.config.js` and `frontend/tailwind.config.js` —
  Tailwind v4 reads its config from the `@theme` block in CSS; no JS
  config file required.
- Jest / ts-jest / jest-environment-jsdom / @types/jest /
  identity-obj-proxy from `package.json` devDependencies.

## [2.3.0] - 2026-04-21

Frontend refit + Facebook Marketplace integration. Pays down the
deferred work CLAUDE.md has been tracking (Formik → RHF + Zod,
RRv7 data router, API client split, typed error narrowing) and adds
the second marketplace integration (assist-only, since Meta doesn't
expose a public listing API for individual sellers).

### Added

- **Facebook Marketplace integration (assist workflow)**:
  - New `backend/app/facebook/` subpackage with
    `schemas.py` (FbFields / FbCondition / FbAvailability /
    FbCopyPasteBlock / FbCatalogExportRequest), `category_mapping.py`
    (curated WHIS → FB taxonomy map with Miscellaneous fallback),
    and `formatter.py` (pure build_copy_paste_block +
    build_catalog_csv_row helpers).
  - New `backend/app/routers/facebook.py` with five endpoints:
    `GET /api/facebook/categories`,
    `POST /api/facebook/items/{id}/fb-fields`,
    `POST /api/facebook/items/{id}/copy-paste`,
    `GET /api/facebook/items/{id}/images.zip`,
    `POST /api/facebook/export`.
  - Frontend surface: `src/types/facebook.ts`, `src/api/facebook.ts`,
    `src/components/FacebookFields.tsx`,
    `src/components/FacebookCopyPasteDialog.tsx`.
  - ItemDetail gains a "Marketplace Integrations" Headless UI Tab
    group with eBay (default) and Facebook panels. Facebook panel
    surfaces FacebookFields + a "Generate copy-paste block" button.
  - Dashboard's bulk action bar (visible when items are selected)
    gains "Export eBay CSV (N)" and "Export FB Catalog (N)" buttons
    that stream the respective CSVs as browser downloads.
- **Strict `CustomFieldsSchema`**: HTTP boundary (`ItemCreate` /
  `ItemUpdate`) now rejects unknown top-level keys on
  `custom_fields` with a 422. Known slots (`ebay`, `facebook`)
  get per-schema type checking; an explicit `user_defined` catchall
  preserves hand-edited shapes. The import endpoint uses a lenient
  `CustomFieldsSchema.coerce_from_raw()` helper that folds legacy
  top-level keys into `user_defined` so CSV imports stay portable.
- **React Router v7 data router** (`createBrowserRouter`): every
  route declares a `loader` that prefetches its React Query data via
  `queryClient.ensureQueryData(...)` before the component mounts —
  no loading flash on navigation. Every route has a
  `RouteErrorBoundary` for localized failure UI. Every page is
  lazy-loaded via `lazy: () => import(...)` for per-route code
  splitting.
- **Error boundaries**: `src/components/ErrorBoundary.tsx` exports a
  `RouteErrorBoundary` (consumes `useRouteError`) and a
  `SectionErrorBoundary` (wraps risky subtrees with
  react-error-boundary; has a custom-fallback escape hatch and a
  `resetKey` prop).
- **Typed API errors**: `src/api/errors.ts` with `ApiError`,
  `isApiError`, `apiErrorMessage` helpers. The axios response
  interceptor in `src/api/http.ts` normalizes every network failure
  into an `ApiError` before rejecting, replacing the
  `catch (error: any)` pattern across the codebase.
- **Per-resource API modules**: `src/api/client.ts` split into
  `http.ts` (axios instance + interceptors),
  `auth.ts` / `items.ts` / `images.ts` / `backups.ts` /
  `analytics.ts` / `ebay.ts` / `facebook.ts` (per-resource
  helpers), and `errors.ts` / `download.ts` (shared infrastructure).
  `client.ts` is now a thin barrel for backward compatibility.
- **Centralized query keys**: `src/api/queryKeys.ts` — hierarchical
  factory (`queryKeys.items.detail(id)`, `queryKeys.analytics.all`,
  etc.). Every `useQuery` / `invalidateQueries` call migrated off
  inline string tuples so invalidations hit the right prefix.
- **Backup two-phase restore UI**: `src/pages/Backups.tsx` rewired
  for the v2.1 two-phase server contract. Clicking Restore now opens
  a modal that loads the preview, shows the expected counts, and
  requires the user to type the current item count to confirm
  before committing.

### Changed

- **Formik → react-hook-form + zod** across all five forms (Login,
  Register, AddItem, ItemDetail, Backups restore confirm). Form
  errors now flow via `formState.errors` (typed), server errors
  surface through a shared `role="alert"` banner driven by
  `apiErrorMessage()`. Zod schemas colocated at
  `<page>.schema.ts` next to each form.
- **`routers/ebay.py` POST /export**: returns `StreamingResponse`
  with a CSV body instead of the former `EbayExportResponse`
  JSON + TODO-to-store-file. Mirrors the new FB export endpoint so
  both integrations share the same client-side download path. The
  frontend helper uses a new shared `api/download.ts`
  (`downloadPost` / `downloadGet`) that handles
  `Content-Disposition` parsing + Blob URL download trigger.
- **`main.py`**: CORS `expose_headers` augmented with
  `Content-Disposition` so browsers can read the filename returned
  by the streaming CSV endpoints.
- **`AuthProvider` / `Layout`** now live under a `RootLayout` /
  `ProtectedLayout` composition inside the RRv7 route tree — both
  consume `<Outlet />` so `useNavigate()` works inside
  `AuthProvider` (required by RRv7's context rules).
- **eBay router** and **items router** migrated off
  `get_current_active_user_or_none` + manual `if not current_user:
  401` checks; every endpoint now uses strict
  `get_current_active_user`.

### Removed

- `formik` and `yup` npm packages. Every form now uses
  react-hook-form + @hookform/resolvers + zod. The `yup`-style
  `Yup.ref`-based cross-field validation (password confirmation)
  is replaced with a `z.refine()` on the Zod schema.
- Dead `handleDownload` function in `ImageGallery.tsx` that logged
  to console and was never wired to a UI affordance.
- Several unused locals across `BarcodeScanner.tsx` and
  `CameraCapture.tsx` surfaced by ESLint.

### Dependencies

Added:
- `react-hook-form ^7` + `@hookform/resolvers ^4`
- `zod ^4`
- `react-error-boundary ^6`

Removed:
- `formik`
- `yup`

### Test coverage

- Backend: 135 → 161 (+26 for the Facebook router + formatter).
- Frontend: 28 → 90 (+62). New files: `api/__tests__/errors.test.ts`,
  `api/__tests__/queryKeys.test.ts`, `api/__tests__/facebook.test.ts`,
  `router/__tests__/loaders.test.ts`,
  `components/__tests__/ErrorBoundary.test.tsx`,
  `components/__tests__/FacebookFields.test.tsx`,
  `components/__tests__/FacebookCopyPasteDialog.test.tsx`,
  `pages/__tests__/Login.test.tsx`,
  `pages/__tests__/Register.test.tsx`,
  `pages/__tests__/AddItem.test.tsx`,
  `pages/__tests__/Backups.test.tsx`.

### Bundle impact

- Main bundle: 586 KB / 178 KB gzip → 436 KB / 143 KB gzip
  (~25% reduction from per-route code splitting).
- Each page is now its own chunk: Dashboard 22 KB,
  ItemDetail 29 KB, AddItem 13 KB, Reports 11 KB, Backups 5 KB,
  Login 3 KB, Register 5 KB. Users only download what they visit.

### Operator notes

- No new env vars, no new migrations, no API-shape changes at the
  pre-existing endpoints (FB endpoints are all-new). Existing
  deployments upgrade seamlessly.
- The eBay POST `/api/ebay/export` response body is now a streaming
  CSV instead of JSON. Only the frontend calls this today (via the
  `ebay` API client, which was updated in lockstep), so there's no
  external migration — but if you built your own tooling against
  the legacy `{ success, file_url: null, ... }` shape, point it at
  the streamed CSV instead.
- CI lint gate remains advisory (`continue-on-error: true`). 31
  remaining ESLint findings are concentrated `any`-related typing
  debt in the camera + barcode scanner components; a dedicated
  typing pass is slated for v2.4.

## [2.2.0] - 2026-04-20

Backend structural release. Pays down the deferred work CLAUDE.md has been
tracking (service-layer extraction, SQLAlchemy 2.x `select()` migration) and
adds the operational plumbing that v3.1's Vision + Pricing features will lean
on (structured logs, request-ID propagation, OTEL skeleton, rate limits).
No HTTP behavior changes; this is refactor + observability + the schema
pre-wire for v3.1.

### Added

- **Service layer** — `app/services/{items,backups,images}.py`. Every
  router is now a thin HTTP shim that delegates to a service class whose
  methods enforce ownership against the authenticated user. Service
  methods are unit-tested directly with a real `db_session` (no
  TestClient), which is how 65 of the 69 new tests land.
  - `routers/images.py`: 168 → 60 lines.
  - `routers/backups.py`: 405 → 154 lines.
  - `routers/items.py`: 429 → 221 lines.
- **Structured logging** (`structlog` 25.x). `logging.basicConfig` is
  replaced with a shared renderer that both structlog-native and stdlib
  `logging.getLogger` calls use. New `LOG_FORMAT` env var picks between
  `console` (human-readable pretty-print) and `json` (line-delimited);
  unset auto-selects based on `DEBUG`.
- **Request-ID middleware** (`app/middleware/request_id.py`). Every
  request gets an `X-Request-ID` (generated if absent, propagated if
  supplied) bound to `structlog.contextvars` so every log line during
  the request carries `request_id=<id>`. Echoed back in the response
  header for client-side correlation.
- **OpenTelemetry skeleton** (`app/telemetry.py`). Gated behind
  `OTEL_ENABLED=true` so unconfigured deployments pay nothing. When on:
  tracer provider, OTLP gRPC exporter, and FastAPI + SQLAlchemy
  instrumentors. Endpoint override via `OTEL_EXPORTER_OTLP_ENDPOINT`.
- **Rate limiting** (`slowapi`, in-memory). User-aware key function
  (JWT → `user:<username>`, fallback → `ip:<addr>`). Limits:
  - `POST /api/token` — 5/minute (IP)
  - `POST /api/backups` — 5/hour (per user/IP)
  - `POST /api/backups/{id}/restore` — 3/hour (per user/IP)
  - `GET /api/items/export/data` — 10/hour (per user/IP)
  The 429 response body is generic — no policy leak.
- **Alembic migration `20260420_0002_pricing_prewire`**. Adds five nullable
  columns on `items` (`estimated_value_low/median/high`,
  `price_last_checked`, `price_provider`) and a new `price_cache` table
  (identity_hash PK, provider, JSON payload, expires_at index). Done in
  v2.2 so v3.1's pricing feature PR isn't also a schema-migration PR.
- **Test coverage: 33 → 121 backend tests (+88).** New files:
  `test_image_service.py` (17), `test_backup_service.py` (20),
  `test_item_service.py` (25), `test_logging.py` (12), `test_telemetry.py`
  (4), `test_rate_limits.py` (7), `test_migrations.py` (3).

### Changed

- **SQLAlchemy 2.x `select()` migration across the service layer**. Every
  query path routed through the new services uses
  `db.execute(select(...).where(...))` + `scalar_one_or_none()` /
  `.scalars()` instead of the legacy `db.query(...).filter(...)` chain.
  Future-compat for SQLAlchemy 3.x, which removes `.query()`.
- All item endpoints migrated from `get_current_active_user_or_none` +
  `if not current_user: 401` to strict `get_current_active_user`. The
  optional-auth pattern was only ever needed for the barcode endpoint,
  which v2.1 already fixed.
- Routers now raise a generic 500 on unexpected exceptions and log the
  full traceback server-side (pattern established in v2.1 for backups;
  extended to items/import in v2.2).
- `tests/conftest.py`: `db_session` fixture now wipes all tables on
  teardown — matches the cleanup contract the `client` fixture already
  provided. Fixes cross-test contamination for tests that only use
  `db_session`.
- CORS `expose_headers` now includes `X-Request-ID` so browsers can read
  the header after a preflighted request.
- Pre-existing broken `tsc --noEmit` / `npm run build` fixed in v2.1;
  v2.2 adds no frontend changes.

### Dependencies

Added to `backend/requirements.txt`:
- `slowapi>=0.1.9,<1`
- `structlog>=24.4,<26`
- `opentelemetry-api/-sdk/-exporter-otlp/-instrumentation-fastapi/-instrumentation-sqlalchemy`
  (1.28 / 0.49b+)
- `httpx>=0.27,<1` and `tenacity>=9,<10` — pre-wired for v3.1 so those
  feature PRs stay focused on logic rather than plumbing.

### Operator notes

- **New env vars**: `LOG_FORMAT`, `OTEL_ENABLED`, `OTEL_SERVICE_NAME`,
  `OTEL_EXPORTER_OTLP_ENDPOINT`. All optional, all documented in
  `backend/.env.example`. Existing deployments need no action.
- **Run the new migration**: `alembic upgrade head` (or let
  `scripts/bootstrap.py` do it on container start). Adds columns/table
  but populates nothing; the pricing feature in v3.1 will fill them in.
- Rate limit counters are in-memory and reset on worker restart. That's
  fine for single-worker household deployments; v3.0 will swap in Redis
  when the job queue lands.
- No breaking changes at the HTTP boundary.

## [2.1.0] - 2026-04-20

Security and correctness patch driven by the 2026-04-20 post-2.0 audit. Focuses
on the sharp bugs that shouldn't ship past 2.0 and lays the groundwork
(pre-commit, dependabot, `.dockerignore`) for the larger v2.2+ refactors.

### Security & correctness

- `GET /api/items/barcode/{barcode}` now requires an authenticated user. It
  previously accepted anonymous callers (via `get_current_active_user_or_none`)
  and only filtered by owner when a user was present, which allowed unauth'd
  barcode probing.
- `POST /api/backups/upload` now validates uploaded zips on magic bytes via
  `zipfile.is_zipfile()`, runs `testzip()` for CRC integrity, and enforces a
  decompression-bomb cap (total uncompressed size ≤ `MAX_UPLOAD_BYTES × 20`,
  returned as 413). Previously a renamed `.zip` of any content would pass.
- **Breaking API change for safety:** `POST /api/backups/{id}/restore` is now
  two-phase. Without query params it returns a non-destructive preview
  (`dry_run=true`) describing the item counts. To commit a restore the caller
  must pass `?dry_run=false` *and* a body `{"confirm_item_count": N}` that
  matches the current server-side count; a mismatch is rejected with 409.
  This guards against accidental clicks and stale-UI races that previously
  would wipe the entire item list.
- Backup create now eager-loads `Item.images` via `selectinload`, eliminating
  an O(items + images) N+1 pattern. Large inventories saw 100s of extra
  queries per backup; now it's two.
- Backup router no longer leaks `str(exc)` into HTTP response bodies. All
  unexpected errors are logged server-side and return a generic 500 with
  detail `"Restore failed; check server logs"` / equivalent.
- `models.UUID` TypeDecorator no longer silently replaces non-v4 UUIDs with a
  fresh v4 on every read and write. It now logs a warning and preserves the
  caller's value. Malformed strings raise `ValueError` (previously were
  silently replaced). Integrations passing v1/v5 UUIDs round-trip correctly.
- Frontend `src/lib/logger.ts` replaces direct `console.log` / `console.error`
  in `src/api/client.ts`. The login handler previously emitted credentials-
  adjacent output to the browser console in production builds.
- Frontend dev-mode auth bypass (`AuthContext`) now refuses to trust the
  `isDevMode` localStorage flag unless the app is being accessed from a
  loopback or RFC-1918 private hostname, even in a dev build. A dev build
  tunneled to the public internet cannot impersonate the admin account.

### Added

- `backend/tests/test_barcode.py`, `test_backups.py`, `test_uuid_decorator.py`
  add 23 new tests covering every behavior above (including an N+1 regression
  test via a SQLAlchemy event listener and a positive decompression-bomb
  rejection test). Backend suite: 10 → 33 tests.
- `frontend/src/lib/__tests__/logger.test.ts` and `devBypass.test.ts` add 10
  new tests (3 logger + 7 hostname guard). Frontend suite: 19 → 28 tests.
- `.github/dependabot.yml` — weekly grouped minor/patch PRs for pip, npm, and
  github-actions; security updates bypass the grouping.
- `.pre-commit-config.yaml` + `backend/ruff.toml` — ruff (backend) and eslint
  (frontend) gates at author time. Catches *new* issues without flagging the
  pre-existing debt.
- `backend/.dockerignore` and `frontend/.dockerignore` — exclude venvs,
  node_modules, caches, secrets, certs, and tests from the Docker build
  context.

### Changed

- `schemas.RestoreResponse` extended with `dry_run: bool`,
  `current_item_count`, `backup_item_count`, `backup_image_count`, all
  optional. A new `schemas.RestoreRequest` body carries `confirm_item_count`.

### Fixed

- Pre-existing `tsc --noEmit` failure (TS6305 on `vite.config.ts` via the
  composite project reference). Narrowed root `tsconfig.json` `include` to
  `["src"]` so `vite.config.ts` is handled exclusively by `tsconfig.node.json`
  (the canonical Vite-React-TS template pattern). `npm run build` now passes.

### Operator notes

- Frontend `Backups.tsx` restore button will need to be updated to the
  two-phase dry-run/confirm flow. Existing calls from the UI without a body
  will now return a preview and do nothing destructive — the restore action
  effectively becomes a no-op until the UI is updated. That change lands in
  v2.3's frontend refit. If you need to restore a backup before then, call
  the API directly: preview first, then
  `POST /api/backups/{id}/restore?dry_run=false` with JSON body
  `{"confirm_item_count": N}`.

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