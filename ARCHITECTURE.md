# WHIS Architecture

This document covers WHIS (Whole-Home Inventory System) v3.1.0 — system design, components, data model, security boundaries, deployment topology, and the architecture decisions that got us here.

For the conventions and engineering discipline, see [CLAUDE.md](CLAUDE.md). For per-API contracts, see [API.md](API.md). For deployment, see [DEPLOYMENT.md](DEPLOYMENT.md).

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Principles](#architecture-principles)
3. [System Components](#system-components)
4. [Data Architecture](#data-architecture)
5. [Security Architecture](#security-architecture)
6. [Integration Architecture](#integration-architecture)
7. [Deployment Architecture](#deployment-architecture)
8. [Performance Architecture](#performance-architecture)
9. [Architecture Decision Records](#architecture-decision-records)
10. [Future Considerations](#future-considerations)

## System Overview

### High-level architecture (v3.1)

```
┌──────────────────┐
│   Browser / PWA  │   React 19 + Vite + Tailwind v4 + TanStack Query
│  (https :5173)   │
└────────┬─────────┘
         │  HTTPS, JWT Bearer
         ▼
┌──────────────────┐                          ┌──────────────────┐
│   Caddy (NAS)    │  reverse-proxy           │  Reverse proxy   │
│   or Vite proxy  │──────────────────────────│  (operator's)    │
│   (dev)          │                          └──────────────────┘
└────────┬─────────┘
         │
         ▼
┌──────────────────────────────────────────────────────────────┐
│                  FastAPI app (uvicorn :27182)                │
│   routers / services / middleware / settings / structlog     │
│   slowapi rate limiting · OpenTelemetry (opt-in)             │
└──────────┬───────────────┬─────────────┬────────────┬────────┘
           │               │             │            │
           ▼               ▼             ▼            ▼
   ┌────────────┐   ┌─────────────┐  ┌────────┐  ┌────────────┐
   │  SQLite    │   │  Postgres   │  │ Redis  │  │  Disk      │
   │  default   │   │  opt-in     │  │ ARQ Q  │  │  uploads/  │
   └────────────┘   └─────────────┘  └────┬───┘  │  backups/  │
                                          │      └────────────┘
                                          ▼
                                  ┌──────────────┐
                                  │ ARQ worker   │  same image
                                  │ (whis-worker)│  as backend
                                  └──────┬───────┘
                                         │ async tasks
                                         ▼
                              ┌──────────────────────┐
                              │   LLM provider       │  outbound
                              │   (OpenRouter,       │  HTTPS to
                              │   Venice.ai, Ollama) │  user-chosen
                              │   eBay Browse API    │  base URL
                              └──────────────────────┘
```

A request enters via the browser, terminates TLS at Caddy or the Vite proxy, hits FastAPI, which either responds synchronously (the default posture) or enqueues an ARQ job to Redis for the worker container to pick up. Heavy operations — backup create/restore, image thumbnail generation, vision identification, pricing estimation — are the worker's domain. Outbound traffic to the LLM provider and the eBay Browse API only ever originates from the worker (when active) or from the backend's request thread (sync fallback).

### Key design decisions (summary — see ADRs below for context)

1. **SQLite default, Postgres opt-in.** Single-tenant household app — SQLite eliminates an operational dependency. Postgres is plumbed for households that want multi-device write concurrency or external backup integration.
2. **Alembic is the sole source of truth for schema.** `Base.metadata.create_all()` was removed in 2.0.0 to eliminate schema drift between dev and prod.
3. **HTTPS-only, even in dev.** Service-worker registration, camera capture, and barcode scan APIs require a secure context.
4. **ARQ over Celery.** Lightweight, async-native, no broker abstraction. Sync fallback when `REDIS_URL` is unset keeps the default `docker compose up` posture single-process.
5. **OpenAI-compatible LLM client.** Targets any provider matching the OpenAI Chat Completions shape — OpenRouter is the canonical endpoint (structured outputs + the `openrouter:web_search` server tool); Ollama / LocalAI / Venice.ai also work.
6. **Generated TypeScript types.** `frontend/src/api/openapi.d.ts` is regenerated from the live FastAPI schema; CI's `contract-check` job enforces drift detection.
7. **Caddy over nginx in NAS deployment.** Auto-TLS for both public hostnames (Let's Encrypt) and internal LANs (Caddy internal CA) — no operator manual cert work.

## Architecture Principles

### Design principles

1. **Thin routers, fat services.** Routers in `app/routers/` validate inputs and dispatch; business logic + ownership checks live in `app/services/`.
2. **Strict at boundaries, trusting inside.** Pydantic v2 models enforce shapes at the HTTP boundary. Inside the app, `model_dump()` is preferred over re-validation.
3. **Fail fast on configuration errors.** `app/settings.py` refuses to load if `BYPASS_AUTH=false` and `SECRET_KEY` is missing/placeholder, if vision/pricing are flagged on without LLM config, or if `LLM_ALLOW_CLOUD=false` against a public host.
4. **Composition over inheritance** for both backend services and frontend components.
5. **Schema-first contracts.** Any new endpoint adds a Pydantic response model; the frontend codegens against it.

### Technical principles

1. **Privacy first.** Self-hosted, all data on the operator's host, no telemetry. Optional LLM features are off by default and gated by `LLM_ALLOW_CLOUD` for paranoid operators.
2. **Graceful degradation.** No Redis? Sync fallback. No eBay creds? LLM fallback. No LLM provider? Pricing returns 503 cleanly. Each missing dependency degrades a feature, never the whole app.
3. **Observability without overhead.** Structured logging (structlog) is always on; OpenTelemetry tracing is opt-in via `OTEL_ENABLED`.

## System Components

### Backend (`backend/app/`) — current layout (v3.1.0)

```
backend/
├── alembic/versions/                    # 8+ migrations on top of baseline
│   ├── 20260420_0001_baseline.py        # idempotent baseline
│   ├── 20260420_0002_pricing_columns.py # v2.2 pre-wire (estimated_value_*)
│   ├── 20260421_0003_postgres_compat.py # v3.0 (UUID, JSON, server_default)
│   ├── 20260422_0004_items_fts.py       # v3.0 (FTS5 / tsvector)
│   ├── 20260422_0005_image_thumbnails.py # v3.0
│   ├── 20260422_0006_llm_usage.py       # v3.1
│   ├── 20260422_0007_price_cache_composite_pk.py # v3.1
│   └── 20260423_0008_item_images_cascade.py # v3.1+
├── app/
│   ├── main.py                          # App factory; mounts routers under /api;
│   │                                    # middleware (slash-tolerance, exception
│   │                                    # handler, request-ID); /uploads static mount
│   ├── settings.py                      # Settings singleton, fail-fast guards
│   ├── models.py                        # User, Item, ItemImage, Backup,
│   │                                    # PriceCache, LLMUsage; UUID TypeDecorator
│   ├── schemas.py                       # Pydantic v2 (ConfigDict)
│   ├── schemas_llm.py                   # VisionSuggestion, VisionResult,
│   │                                    # PriceSource, PriceEstimate,
│   │                                    # PriceEstimateEnvelope; PROMPT_VERSION
│   ├── database.py                      # Engine + SessionLocal; reads DATABASE_URL
│   ├── security.py                      # PyJWT auth (python-jose retired in 2.0)
│   ├── fts.py                           # FTS5 / tsvector helpers
│   ├── rate_limit.py                    # slowapi limiter instance
│   ├── telemetry.py                     # OpenTelemetry skeleton
│   ├── logging_config.py                # structlog + request-ID middleware
│   │
│   ├── routers/                         # Thin handlers
│   │   ├── auth.py        # /api/register, /api/token (5/min), /api/users/me
│   │   ├── items.py       # /api/items/*, /api/categories, /api/locations
│   │   ├── images.py      # /api/items/{id}/images, /api/images/{id}
│   │   ├── analytics.py   # /api/analytics/*
│   │   ├── backups.py     # /api/backups/*  (sync OR JobReference)
│   │   ├── ebay.py        # /api/ebay/* (CSV listing assist)
│   │   ├── facebook.py    # /api/facebook/* (copy-paste + Meta Commerce CSV)
│   │   ├── jobs.py        # /api/jobs/{id}  (v3.0 ARQ job status)
│   │   ├── vision.py      # /api/vision/identify  (v3.1)
│   │   └── pricing.py     # /api/pricing/{estimate,refresh,estimate}  (v3.1)
│   │
│   ├── services/                        # Domain logic + ownership checks
│   │   ├── items.py       # ItemService: CRUD, bulk_delete, image-file cleanup
│   │   ├── backups.py     # BackupService: create, restore (with confirm), list
│   │   └── images.py      # ImageService: validate, persist, delete (incl. thumb)
│   │
│   ├── jobs/                            # v3.0 ARQ scaffold
│   │   ├── client.py      # get_arq_pool() — returns None when REDIS_URL unset
│   │   ├── worker.py      # WorkerSettings export
│   │   └── tasks/
│   │       ├── backups.py # backup_create, backup_restore
│   │       ├── images.py  # thumbnail_generate
│   │       ├── vision.py  # vision_identify
│   │       └── pricing.py # pricing_refresh
│   │
│   ├── llm/                             # v3.1 shared LLM layer
│   │   ├── openai_compatible.py # AsyncOpenAI wrapper; structured outputs;
│   │   │                        # extra_body for OR plugins / web_search;
│   │   │                        # defensive _extract_content for null-choices
│   │   │                        # error envelopes
│   │   ├── prompts.py     # Versioned system prompts
│   │   └── budget.py      # Daily cost-cap guard (per-user, per-feature)
│   │
│   ├── vision/service.py                # VisionService.identify(_async)
│   │
│   ├── pricing/                         # v3.1 estimate orchestration
│   │   ├── service.py            # PricingService: provider routing, cache
│   │   ├── normalizer.py         # ItemIdentity (frozen dataclass with hash)
│   │   ├── cache.py              # PriceCache wrapper (composite PK)
│   │   ├── aggregate.py          # P10/P50/P90 (or min/median/max for N<5)
│   │   ├── provider_base.py      # PriceProvider ABC + exception hierarchy
│   │   ├── provider_ebay_browse.py  # OAuth client_credentials + Browse search
│   │   └── provider_llm.py       # Two-call flow: research + extraction
│   │
│   ├── ebay/              # CSV formatter, category mapping, schemas
│   └── facebook/          # Copy-paste formatter, Meta Commerce CSV, schemas
│
├── scripts/bootstrap.py                 # Dockerfile CMD entrypoint; reconciles
│                                        # legacy stamps + alembic upgrade head
├── tests/                               # 336 pytest tests; in-memory SQLite by
│                                        # default; honors TEST_DATABASE_URL for
│                                        # the Postgres matrix
├── .env.example
└── requirements.txt
```

#### Backend layer responsibilities

1. **Routing layer (`app/routers/`)** — handles HTTP concerns: dependency injection, validation, status codes, rate limiting. Keeps no state.
2. **Service layer (`app/services/`)** — owns business logic, ownership enforcement, and side effects (file deletes, cache invalidation). Each service is constructed with `(db, user)` and exposes verbs (`create`, `delete`, `bulk_delete`, etc.).
3. **Settings layer (`app/settings.py`)** — pydantic-settings singleton; **only** entry point for environment variables. Fail-fast at import time on misconfiguration.
4. **Data layer (`app/models.py` + `app/database.py`)** — SQLAlchemy 2.x models with custom `UUID` TypeDecorator (stores UUIDs as 36-char strings, coerces non-v4 to v4). Alembic owns schema; no `create_all()` at startup.
5. **LLM layer (`app/llm/`)** — sole HTTP client to OpenAI-compatible providers; defensive parsing for upstream-error-in-200 envelopes; `extra_body` for OR-specific kwargs.
6. **Job layer (`app/jobs/`)** — ARQ pool factory + task wrappers. Tasks return JSON-serializable envelopes (no `HTTPException` propagation — see F10b).
7. **Provider layer (`app/pricing/provider_*.py`)** — pluggable `PriceProvider` implementations. `PricingService` orchestrates priority + cache + per-item stamping.

### Frontend (`frontend/src/`) — current layout (v3.1.0)

```
frontend/
├── src/
│   ├── App.tsx                          # createBrowserRouter + RouterProvider
│   ├── main.tsx
│   ├── queryClient.ts                   # React Query 5 (retries=1, no focus refetch)
│   ├── index.css                        # Tailwind v4 @theme tokens
│   ├── setupTests.ts                    # Vitest setup
│   │
│   ├── api/
│   │   ├── client.ts                    # axios instance + ApiError
│   │   ├── items.ts, images.ts, analytics.ts, backups.ts,
│   │   ├── auth.ts, ebay.ts, facebook.ts, jobs.ts (v3.0)
│   │   ├── queryKeys.ts                 # Hierarchical query-key factory
│   │   ├── openapi.d.ts                 # Generated by `npm run codegen:api`
│   │   └── types.ts                     # Re-exports + analytics types
│   │
│   ├── contexts/                        # AuthContext + DevModeContext
│   │                                    # (split provider/hook for react-refresh)
│   ├── pages/                           # Dashboard, AddItem, ItemDetail, Reports,
│   │                                    # Backups, Login, Register
│   ├── router/loaders.ts                # Data-router loaders that warm RQ cache
│   │                                    # via ensureQueryData()
│   │
│   └── components/                      # Layout, BarcodeScanner (lazy + zxing),
│                                        # CameraCapture, CustomFields, EbayFields,
│                                        # FacebookFields, FacebookCopyPasteDialog,
│                                        # ImageGallery, DataMigration, ErrorBoundary
├── certs/                               # Generated by scripts/generate-certs.js
├── scripts/generate-certs.js            # mkcert-aware; OpenSSL fallback
├── vitest.config.ts
├── vite.config.ts
└── package.json
```

#### Frontend layer responsibilities

1. **Router/data layer.** `createBrowserRouter` data router with per-route loaders. Loaders warm the React Query cache so pages render without a loading flash.
2. **API layer.** Per-resource modules in `src/api/`. The shared axios client owns auth header injection, base URL, and the `ApiError` wrapper. `openapi.d.ts` provides end-to-end type safety.
3. **State layer.** React Query for server state; React Context for auth + dev-mode. No Redux. Form state via `react-hook-form` + zod.
4. **Components layer.** Functional components only. Heavy components (BarcodeScanner) lazy-loaded.
5. **Styling.** Tailwind v4 — config in CSS via `@theme` block, semantic tokens (`primary`, `primary-hover`, `primary-accent`, `primary-subtle`, `primary-subtle-hover`).

## Data Architecture

### Database schema (v3.1, abridged — see migrations for full DDL)

All UUID columns are stored as 36-char `VARCHAR` (SQLite) or native `UUID` (Postgres) by the custom `UUID` TypeDecorator. Postgres + SQLite are kept structurally identical; dialect-specific DDL (FTS, `tsvector`, `ON DELETE CASCADE`) is handled inside migrations via `op.get_bind().dialect.name` branching.

```sql
-- Core (1.x)
CREATE TABLE users (
    id               UUID PRIMARY KEY,
    email            VARCHAR UNIQUE,
    username         VARCHAR UNIQUE,
    hashed_password  VARCHAR,
    is_active        BOOLEAN,
    created_at       TIMESTAMP
);

CREATE TABLE items (
    id                       UUID PRIMARY KEY,
    name                     VARCHAR,
    category                 VARCHAR,
    location                 VARCHAR,
    brand                    VARCHAR,
    model_number             VARCHAR,
    serial_number            VARCHAR,
    barcode                  VARCHAR,
    purchase_date            TIMESTAMP,
    purchase_price           FLOAT,
    current_value            FLOAT,
    warranty_expiration      TIMESTAMP,
    notes                    VARCHAR,
    custom_fields            JSON,                -- strict-typed sub-object
    created_at               TIMESTAMP,
    updated_at               TIMESTAMP,
    owner_id                 UUID REFERENCES users(id),

    -- v2.2 pre-wire / v3.1 populated
    estimated_value_low      FLOAT,
    estimated_value_median   FLOAT,
    estimated_value_high     FLOAT,
    price_last_checked       TIMESTAMP,
    price_provider           VARCHAR(32)
);
CREATE INDEX ix_items_name     ON items(name);
CREATE INDEX ix_items_category ON items(category);
CREATE INDEX ix_items_location ON items(location);
CREATE INDEX ix_items_barcode  ON items(barcode);
-- v3.0 FTS: SQLite gets an FTS5 virtual table; Postgres gets a GIN
-- index on a generated tsvector column.

CREATE TABLE item_images (
    id                       UUID PRIMARY KEY,
    item_id                  UUID REFERENCES items(id) ON DELETE CASCADE, -- v3.1+
    filename                 VARCHAR,
    file_path                VARCHAR,
    -- v3.0 thumbnail pipeline
    thumbnail_path           VARCHAR,
    thumbnail_generated_at   TIMESTAMP,
    created_at               TIMESTAMP
);

CREATE TABLE backups (
    id             UUID PRIMARY KEY,
    owner_id       UUID REFERENCES users(id),
    filename       VARCHAR,
    file_path      VARCHAR,
    size_bytes     INTEGER,
    item_count     INTEGER,
    image_count    INTEGER,
    created_at     TIMESTAMP,
    status         VARCHAR,              -- 'completed' | 'failed' | 'in_progress'
    error_message  VARCHAR
);

-- v3.1 — pricing cache, composite PK so one hash can host one entry per provider
CREATE TABLE price_cache (
    identity_hash  VARCHAR(64),
    provider       VARCHAR(32),
    payload        JSON NOT NULL,
    created_at     TIMESTAMP NOT NULL,
    expires_at     TIMESTAMP NOT NULL,
    PRIMARY KEY (identity_hash, provider)
);
CREATE INDEX ix_price_cache_expires_at ON price_cache(expires_at);

-- v3.1 — daily LLM usage rollup, one row per (user, date, feature)
CREATE TABLE llm_usage (
    id              UUID PRIMARY KEY,
    user_id         UUID REFERENCES users(id),
    usage_date      DATE,
    feature         VARCHAR,           -- 'vision' | 'pricing'
    request_count   INTEGER,
    tokens_in       INTEGER,
    tokens_out      INTEGER,
    cost_usd        FLOAT,
    UNIQUE (user_id, usage_date, feature)
);
```

**Notes on the data model**:

- `Item.custom_fields` is a **JSON column on `items`** — strict-typed to `{ebay, facebook, user_defined}` at the Pydantic boundary, but persisted as a single blob. Earlier versions of this doc described a normalized `custom_fields` table; that was aspirational and never shipped.
- `item_images.item_id` carries `ON DELETE CASCADE` (v3.1 fix) so the bulk-delete path with `synchronize_session=False` doesn't crash on Postgres FK enforcement (SQLite masked this for a long time).
- `price_cache.payload` holds the JSON-serialized `PriceEstimate` envelope (the same shape the API returns). Listing `title` + `url` + `price` + `condition` only — no eBay seller PII (regression-tested; load-bearing for the eBay deletion exemption).
- `llm_usage` is upserted on every LLM call for the budget guard. Non-LLM provider calls (eBay) stamp a nominal zero-token row (deferred work: thread real provider numbers through).

### Data flow — typical request

```
Browser → Caddy/Vite → FastAPI router → middleware (auth, rate limit, request-ID)
       → service (ownership check, business logic) → SQLAlchemy session → DB
       → Pydantic response model → JSON → browser

For async-capable endpoints (backup create, vision, pricing):
       Router → ARQ pool (if REDIS_URL set) → returns JobReference
       → Worker picks up → executes task → result envelope to Redis
       → Frontend polls /api/jobs/{id} → receives result
```

## Security Architecture

See [SECURITY.md](SECURITY.md) for the full posture. Summary of what the application provides vs. what is the operator's responsibility:

### Application-provided

- HTTPS-only (no HTTP listener; refuses to start without certs in the shared volume)
- JWT auth via PyJWT (HS256 by default; switch via `ALGORITHM`)
- bcrypt password hashing via passlib
- Pillow magic-byte upload validation + size + dimension caps
- slowapi per-route rate limiting (auth, vision, pricing all rate-limited)
- Structured logging with stack-trace redaction unless `DEBUG=true`
- Privacy kill-switch (`LLM_ALLOW_CLOUD=false` enforces private-host LLM)
- Daily LLM cost caps (per-user, per-feature, returns 402 over-cap)
- eBay deletion-exemption regression test (CI-blocking)

### Operator-provided

- WAF / IP-level rate limiting / HSTS — Caddy supports `rate_limit` middleware
- VPN / SSO if exposing beyond LAN
- Backup-volume encryption at rest
- Secret rotation discipline (`SECRET_KEY`, `LLM_API_KEY`, `EBAY_*`)

## Integration Architecture

### LLM provider integration (v3.1)

The `app/llm/openai_compatible.py` client targets any OpenAI-compatible endpoint:

```
WHIS                                    Provider
────                                    ────────
PricingService.estimate                  /v1/chat/completions
  ↓ research call (web_search enabled)  ───────────────────►  text answer
  ↓ extraction call (response_format    ───────────────────►  strict JSON
    json_schema strict)
  ↓
PriceEstimateEnvelope
```

Two-call pattern for pricing exists because OpenRouter's `web_search` middleware can mangle nested objects when combined with `response_format` in a single call (F10a fix). Vision uses a single call with strict JSON schema.

Provider-specific kwargs (OpenRouter plugins, `openrouter:web_search` tool) are passed via `extra_body` so the OpenAI SDK doesn't reject them.

### eBay integration (v2.3 listing assist + v3.1 pricing)

Two completely separate surfaces, two distinct OAuth flows:

```
Listing assist (v2.3) — in-app only, no eBay API calls
────────────────────────────────────────────────────
Item → EbayFields validation → category mapping → CSV streamed to operator
       (operator uploads to Seller Hub manually)

Pricing (v3.1) — Browse API
───────────────────────────
PricingService.estimate
  ↓ EbayBrowseProvider.lookup
  ↓   client_credentials OAuth → bearer token (cached)
  ↓   /buy/browse/v1/item_summary/search
  ↓   _parse_item_summaries (drops seller PII — exemption guard)
  ↓ aggregate_prices → PriceEstimate
  ↓ PriceCache.set
  ↓ Item.estimated_value_* stamped
  ↓
PriceEstimateEnvelope returned to client
```

WHIS holds an exemption from eBay's Marketplace Account Deletion notification system on the basis that no eBay user data is persisted. See [docs/EBAY_INTEGRATION.md](docs/EBAY_INTEGRATION.md) for the full audit trail and the load-bearing regression test.

### Facebook Marketplace integration (v2.3)

Assist-only — Meta has no public listing API for individual sellers. WHIS produces:
- A copy-paste block (`/api/facebook/items/{id}/copy-paste`) — operator pastes into Marketplace's compose UI
- A Meta Commerce catalog CSV (`/api/facebook/export`) — operator imports into Meta Commerce Manager
- A zip of item images (`/api/facebook/items/{id}/images.zip`) — for image upload

### File storage

Uploads land in `settings.UPLOAD_DIR` with server-generated filenames (`{timestamp}_{uuid4}{ext}`). Thumbnails live alongside (`thumb_{stem}.webp`). Both are deleted from disk when the parent item or image is deleted (F6 regression).

Backup zips live in `settings.BACKUP_DIR`. Each archive contains the JSON manifest plus byte-identical copies of every image referenced by the user's items.

## Deployment Architecture

### Development

```
Local machine
  ├── backend (uvicorn :27182, HTTPS)
  ├── frontend (vite dev server :5173, HTTPS, proxies /api + /uploads)
  └── SQLite at backend/database/whis.db
```

### Docker — local testing

Compose profiles compose into 4 stacks:

| Stack | Composition | Use case |
|---|---|---|
| Default (`docker compose up`) | backend + frontend + SQLite, jobs sync | Casual local dev |
| `--profile worker` | + Redis + ARQ worker | Test async path, vision, pricing |
| `--profile postgres` | + Postgres 16 | Test the Postgres migrations |
| `--profile postgres --profile worker` | Full v3.0 stack | Pre-push end-to-end smoke |

### Production / NAS (`docker-compose.nas.yml`)

```
Internet/LAN
     │
     ▼
┌──────────┐  port 80/443
│  Caddy   │  auto-TLS (Let's Encrypt for public hostnames,
│          │            internal CA for *.local)
└────┬─────┘
     │  HTTP proxy
     ▼
┌──────────┐
│ backend  │  uvicorn :27182, HTTPS internal
│ (uvicorn)│
└────┬─────┘
     │
     ├──→ Redis (always on in NAS posture)
     ├──→ ARQ worker (always on in NAS posture)
     ├──→ SQLite or Postgres
     └──→ disk (database/, uploads/, backups/)
```

NAS deployments run Redis + worker by default — the 15–45s latency of synchronous backup operations isn't acceptable in interactive use.

## Performance Architecture

### Backend

- **Indexed queries.** `models.py` declares `index=True` on all routinely-filtered columns (`name`, `category`, `location`, `barcode`, `email`, `username`, `expires_at`).
- **FTS for search.** v3.0 replaced ad-hoc `LIKE '%q%'` queries with FTS5 (SQLite) / `tsvector` + GIN (Postgres). Sub-100ms search at typical inventory sizes.
- **Async-by-default for heavy ops.** ARQ worker takes vision (~3–10s), pricing (~3–6s), backup create/restore (~5–60s), thumbnail generation (~50–500ms each). Sync fallback exists for the default dev posture.
- **Cache where reasonable.** `PriceCache` defaults to 14-day TTL (`PRICING_CACHE_DAYS`); per-provider so eBay and LLM estimates can co-exist for the same item.
- **Connection pool tuned for Postgres.** `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_POOL_RECYCLE_SECONDS` exposed as env. SQLite ignores these.

### Frontend

- **React Query with hierarchical keys.** `api/queryKeys.ts` enables fine-grained invalidation.
- **Loader-driven page warmup.** Data router loaders use `ensureQueryData` so navigation feels instant.
- **Lazy-loaded heavy components.** `BarcodeScanner` (`@zxing/browser` is large) loads on demand.
- **Service worker via vite-plugin-pwa.** Workbox `runtimeCaching` matches `/api/` via a function predicate; assets via `autoUpdate`.
- **Thumbnails for galleries.** v3.0 thumbnails are served instead of full-res in lists.

## Architecture Decision Records

### ADR 1 — SQLite default, Postgres opt-in

- **Context:** Single-tenant household app. Operators range from "double-click an installer" to "operations engineers running k8s." Need a default that's zero-config.
- **Decision:** Ship SQLite by default; support Postgres via `DATABASE_URL=postgresql+psycopg://...` and a compose profile.
- **Consequences:** Migrations have to be dialect-aware (handled via `op.get_bind().dialect.name` branching). FK-enforcement gap on SQLite caused F1-era bugs (cascade fix in v3.1).

### ADR 2 — JWT authentication via PyJWT

- **Context:** Stateless multi-device API. Need standard auth that's portable across web + future native clients.
- **Decision:** JWT (HS256 default) via PyJWT (python-jose retired in 2.0.0 due to maintenance status).
- **Consequences:** Tokens hard-expire (`ACCESS_TOKEN_EXPIRE_MINUTES`, default 30). No refresh-token flow yet — operators tolerate periodic re-login.

### ADR 3 — Alembic as sole schema source of truth (2.0.0)

- **Context:** Pre-2.0.0 startup called both `Base.metadata.create_all()` and `alembic upgrade head`, leading to subtle schema drift.
- **Decision:** Remove `create_all()`. `bootstrap.py` reconciles legacy stamps and runs `alembic upgrade head`.
- **Consequences:** Adding a model field requires both `models.py` + a migration. CI catches the gap via the test matrix.

### ADR 4 — ARQ over Celery (3.0.0)

- **Context:** Need a job queue for backup create/restore (15–45s) and the upcoming v3.1 LLM/pricing flows. Celery is over-broker-abstracted for this scale.
- **Decision:** ARQ (Redis-backed, async-native, ~1k LOC). Sync fallback when `REDIS_URL` is unset.
- **Consequences:** No multi-broker support. Worker must run the same image as backend. Task return values must be JSON-serializable (F10b regression).

### ADR 5 — OpenAI-compatible LLM client (3.1.0)

- **Context:** Want to support OpenRouter (canonical), Venice.ai (privacy), Ollama (local), LocalAI without a separate adapter per provider.
- **Decision:** Single `AsyncOpenAI` client; provider-specific kwargs via `extra_body`.
- **Consequences:** Some provider features (OR `response-healing`, `openrouter:web_search`, schema constraints incompatible with Anthropic-via-Azure) need defensive handling in the wrapper.

### ADR 6 — Caddy over nginx for NAS (2.4.0)

- **Context:** Operator complaints about nginx cert management, especially behind dynamic-DNS and `*.local` LANs.
- **Decision:** Caddy with auto-TLS for both Let's Encrypt (public) and internal CA (LAN).
- **Consequences:** One fewer manual cert step. Operators on `*.local` install Caddy's root CA on each device.

### ADR 7 — Strict JSON schema for LLM structured outputs (3.1.0)

- **Context:** Free-text LLM responses are unparseable; markdown-fenced JSON is brittle.
- **Decision:** Use `response_format: {type: "json_schema", strict: true}` with the generated schema from `schemas_llm.py`.
- **Consequences:** Some provider+model combinations reject specific JSON Schema constraints (`minimum`, `pattern`, etc.). The client strips these before sending; strictness still applies on our side via `model_validate`.

## Future Considerations

### Currently aspirational

- **End-to-end testing.** Playwright is the planned vehicle.
- **Coverage gates in CI.** Currently reported but not failed-under.
- **Multi-tenancy / RBAC.** Single-role today; possible future evolution if WHIS ever moves beyond single-household scope.
- **Refresh-token flow.** Currently re-login required after `ACCESS_TOKEN_EXPIRE_MINUTES`.
- **eBay Sell APIs.** v3.1 only does Browse (read-only, no user-context); a full Sell-side integration would require reversing the Marketplace deletion exemption and standing up the callback listener.
- **Real-time updates.** No WebSocket layer today; React Query polling covers async-job lifecycle.
- **Native mobile.** PWA is the only mobile path today.

### Already shipped (don't add to "future" lists)

- ✅ AI integration (v3.1 vision + pricing)
- ✅ Marketplace integrations (v2.3 eBay CSV, v2.3 Facebook copy-paste/CSV, v3.1 eBay pricing)
- ✅ Postgres support (v3.0)
- ✅ Background jobs (v3.0 ARQ)
- ✅ Image thumbnails (v3.0)
- ✅ FTS search (v3.0)
- ✅ Tailwind v4 migration (v2.4)
- ✅ React Router v7 data router (v2.3)
- ✅ react-hook-form + zod (v2.3 — Formik+Yup retired)
- ✅ Vitest (v2.4 — Jest retired)
- ✅ OpenTelemetry skeleton (v2.2 — opt-in)
- ✅ Structured logging (v2.2 — structlog)
- ✅ Per-route rate limiting (v2.2 — slowapi)
