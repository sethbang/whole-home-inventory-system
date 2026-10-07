# Changelog

All notable changes to WHIS will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- **Dependency refresh** (supersedes Dependabot PRs #2–#14).
  - Frontend: Vite 6 → 8, `@vitejs/plugin-react` 4 → 6,
    `vite-plugin-pwa` 0.21 → 2.0, Vitest + coverage 3 → 5, `globals`
    15 → 17, `eslint-plugin-react-refresh` 0.4 → 0.5, plus minor/patch
    bumps across React 19.3, TanStack Query, react-hook-form, zod,
    zxing, and Tailwind. The lockfile was regenerated; `npm audit`
    (dev included) now reports 0 vulnerabilities.
  - Backend: `openai` SDK 1.x → 3.x (no code changes — WHIS doesn't use
    the Responses API or pass a custom httpx client), uvicorn 0.54,
    SQLAlchemy 2.1, alembic 1.20, and raised floors for httpx,
    pydantic-settings, and slowapi.
  - CI: `actions/checkout` v7, `actions/setup-node` v7,
    `docker/setup-buildx-action` v4.
- **Node.js 24** in CI and both frontend Docker images (was 20, which is
  end-of-life). Vitest 5 requires Node ≥ 22.12, so that is now the
  minimum for local development.
- `vite.config.ts` uses `import.meta.dirname` instead of `__dirname`,
  for Vite's upcoming native config loader.

### Fixed

- **Two timing-dependent frontend tests.** The Dashboard bulk-delete
  test asserted the dialog had closed before the delete promise
  resolved (it failed CI on `main` once), and the Browse room-filter
  test assumed the location-counts query resolved alongside the items
  query, which no longer holds with TanStack Query 5.104. Both now wait
  for the UI state they check.

## [3.3.1] - 2026-10-06

### Security

- **Patched four high-severity frontend dependency advisories**
  (`npm audit fix`): `axios` 1.15.1 → 1.20.0 (prototype-pollution
  gadgets), `react-router` / `react-router-dom` → 7.18.4
  (turbo-stream deserialization, `__manifest` DoS), and `form-data` →
  4.0.6 (CRLF injection in multipart field names). The production
  dependency audit (`npm audit --omit=dev`) is clean again.
- **Patched Python dependency advisories** flagged by `pip-audit`:
  `starlette` floor raised to 1.3.1 (PYSEC-2026-161/-248/-249/-2280/
  -2281) and `cryptography` to 50.x (PYSEC-2026-3552/-3553/-3554,
  GHSA-537c-gmf6-5ccf). Starlette 1.0 only removed APIs WHIS doesn't
  use; no code changes were needed.
- **Backend image: upgraded setuptools to 84+** in both the app venv
  and the base image's system Python. The setuptools seeded by Python
  3.11 vendors `jaraco.context` 5.3.0 (CVE-2026-23949) and `wheel`
  0.45.1 (CVE-2026-24049), which failed the CI Trivy scan.

### Changed

- **Completed the SQLAlchemy 2.x `select()` migration.** Every remaining
  legacy `db.query()` call site (auth, security, analytics, pricing,
  eBay, the ARQ job tasks, the backup / LLM-config services, and the dev
  scripts) now uses `select()` / `db.execute(...)`, and `Base` now
  comes from `sqlalchemy.orm.declarative_base` rather than the legacy
  `sqlalchemy.ext.declarative`. The codebase is now ready for
  SQLAlchemy 3.x, where the `Query` API is removed.
- **Replaced the deprecated `datetime.utcnow()`** with a new
  `app/utctime.py` helper (`utcnow()` — a naive UTC datetime,
  behaviour-identical to the old call). The backend test run dropped
  from ~976 deprecation warnings to 2.
- **Frontend structural refactor.** Extracted the vision→pricing
  orchestration into a `useVisionPricingChain` hook, the eBay/Facebook
  panels into a `MarketplacePanels` component, the shared item form
  into an `ItemFormFields` component used by both Add Item and Item
  Detail, the Dashboard filter state into a reducer, and split the
  837-line Settings page into focused tab components, plus a reusable
  accessible `ConfirmDialog`. Page sizes dropped sharply — Settings
  837→306, ItemDetail 654→436, AddItem 612→386, Dashboard 566→446
  lines — and new unit/component tests bring the frontend suite to 159.
- **Accessibility pass.** Confirmation dialogs now use `role="dialog"`
  + `aria-modal` with focus trapping and Escape-to-close; list
  checkboxes and the view-mode toggle got accessible names /
  `aria-pressed`; every route now declares its own `errorElement` so a
  loader/render failure stays localized to the page area instead of
  blanking the navigation shell.

### Fixed

- **Vision→pricing race in Add Item.** A slow pricing response kicked
  off by an earlier vision suggestion could overwrite a newer one. The
  `useVisionPricingChain` hook now guards every result with a
  generation counter, so only the most recent request can set the
  estimate.
- **Concurrent LLM usage accounting could lose spend.** `record_usage`
  did a read-modify-write in Python, so two calls landing together for
  the same (user, day, feature) could overwrite each other's totals. It
  now uses an atomic in-DB increment. The daily-cap *check* remains
  best-effort by nature — a call's cost is unknowable until it
  completes — which is now documented in `SECURITY.md` alongside the
  `SECRET_KEY`-derived LLM-key encryption trade-offs.
- **`POST /api/register` is now rate-limited** (5/min/IP), matching the
  existing throttle on `/api/token`. Registration was previously
  unthrottled, leaving it open to account-enumeration probing and
  user-table flooding.
- **Editing, deleting, or changing images on an item now refreshes the
  Dashboard and Browse lists.** `ItemDetail` mutations previously
  invalidated only the item-detail query, so list cards could show a
  stale name/value/thumbnail — or a deleted item could linger as a
  ghost card — until the next manual refetch. The mutations now
  invalidate the whole `items` query namespace.

### CI

- **Backend lint gate.** `ruff check` now runs in CI alongside the
  existing ESLint gate.
- **Version-stamp guard.** A new `version-check` job fails the build if
  `frontend/package.json`, the FastAPI app version, the `/api/health`
  payload, `CLAUDE.md`, and `README.md` disagree. On `main` these had
  all stayed at 3.1.0 while the 3.2 and 3.3 work shipped; they were
  brought up to 3.3.0 in this release cycle.

### Documentation

- **Corrected stale and false statements.** `README.md`, `API.md`,
  `TESTING.md`, and `DEPLOYMENT.md` now report 3.3.1 and current test
  counts (409 backend / 159 frontend). `API.md` now documents the v3.2
  admin-only `/api/llm-config` routes and `GET /api/locations/counts`.
  `SECURITY.md` no longer claims the app has no rate limiting or a
  single user role. `ARCHITECTURE.md` and `DEVELOPMENT.md` are now
  labelled as last reviewed against v3.1.0.

## [3.3.0] - 2026-05-04

### Added — Browse page

- **`/browse` page** with a room sidebar showing per-location item
  counts; selecting a room filters the inventory. Includes a reusable
  `ItemCard` (card and list layouts), debounced search, category /
  value filters, and a view-mode toggle. Linked from the main
  navigation.
- **`GET /api/locations/counts`** returns per-location item counts for
  the authenticated user (null / empty locations excluded, sorted by
  name), backed by `ItemService.location_counts()` and a new
  `LocationCount` schema.

### Fixed

- **Backup downloads no longer fail with 401.** The Backups page opened
  download URLs with `window.open`, which drops the JWT
  `Authorization` header. Downloads now go through the authenticated
  API client and save via a blob, using the filename from
  `Content-Disposition`.

### Added — Day / Night / System-sync theming

- **Three-mode theme switcher** in the user-menu dropdown (and mobile
  disclosure panel) of `frontend/src/components/Layout.tsx`. The control
  is a segmented radiogroup with **Day**, **Night**, and **System-sync**
  options, each with a Heroicons glyph (sun, moon, computer-desktop).
  Selection persists in `localStorage` under the key `whis-theme`;
  default is `system`.
- **`ThemeProvider` / `useTheme`** at
  `frontend/src/contexts/ThemeContext.tsx` and `useTheme.ts`, following
  the existing split provider/hook pattern (`DevModeContext`). Owns the
  `mode → resolvedMode` resolution, applies the `.dark` class to
  `<html>`, mirrors the active surface color into the
  `<meta name="theme-color">` tag, and subscribes to
  `prefers-color-scheme` `change` events when in System-sync mode so the
  app follows the OS toggle without a reload. Wrapped over
  `DevModeProvider` + `AuthProvider` in `router/layouts.tsx` so Login /
  Register inherit the theme.
- **FOUC-prevention inline script** in `frontend/index.html` resolves
  the same logic synchronously before React mounts, so a hard-reload in
  Night mode never flashes white. Also adds
  `<meta name="color-scheme" content="light dark">` so native form
  controls and scrollbars adopt the right palette pre-paint.
- **Neutral-token palette** in `frontend/src/index.css` (`--color-fg`,
  `--color-muted`, `--color-subtle`, `--color-inverse`,
  `--color-surface`, `--color-surface-raised`, `--color-surface-muted`,
  `--color-line`, `--color-line-strong`, `--color-overlay`) plus a
  status palette (`--color-danger`, `--color-success`, `--color-warning`
  with matching `-subtle` variants). All tokens swap values inside
  `:root.dark { ... }`, and `--color-primary-subtle` /
  `--color-primary-subtle-hover` are tuned to desaturated dark blues so
  the existing primary tints don't glow on a dark background.
- **9 new vitest cases** at
  `frontend/src/contexts/__tests__/ThemeContext.test.tsx` covering
  default-mode, persistence round-trip, malformed-storage fallback,
  system-mode pickup at mount, system-mode reaction to
  `matchMedia('change')` events, override-stickiness when the user
  picks Day or Night explicitly, and listener cleanup on unmount.

### Changed — Day / Night / System-sync theming

- **Tailwind v4 dark variant** wired up via
  `@custom-variant dark (&:where(.dark, .dark *));` in `index.css` and a
  `.dark` class toggle on `<html>`. Components do **not** use `dark:*`
  prefixes — the new neutral tokens swap values automatically.
- **~700 hardcoded color callsites** across 22 component / page files
  migrated from raw `bg-gray-*` / `text-gray-*` / `border-gray-*` /
  `bg-white` / `bg-black` / `bg-red-*` / `text-red-*` / `bg-green-*` /
  `text-green-*` / `bg-yellow-*` / `bg-blue-*` / `text-blue-*` /
  `bg-indigo-*` / etc. to the new semantic tokens
  (`bg-surface-raised`, `text-fg`, `text-muted`, `text-subtle`,
  `border-line`, `border-line-strong`, `bg-danger-subtle`,
  `text-warning`, `bg-primary` for ad-hoc blue/indigo buttons, etc.).
  `text-white` is preserved on primary/danger/success surfaces because
  contrast is fixed there.
- **`@tailwindcss/forms` plugin override.** The plugin's base reset
  hard-codes `background-color: #fff` on every text-style input,
  textarea, and select, which would have made them white-on-white in
  Night mode. `index.css` now ships an explicit override using the
  same `[type='text']` / `[multiple]` / `textarea` / `select` selector
  set the plugin uses (matching specificity 0,1,0 — a bare `input`
  selector loses to the plugin), driving the controls off
  `--color-surface-raised` / `--color-fg`. Disabled state uses
  `--color-surface-muted` / `--color-subtle`. Status colors retuned
  for night mode so `bg-danger text-white` / `bg-success text-white`
  buttons keep AA contrast.
- **`color-scheme` follows the resolved theme.** `html { color-scheme:
  light }` / `html.dark { color-scheme: dark }` so native widgets
  (scrollbars, date pickers, autofill highlights) match the user's
  picked theme regardless of OS preference.

### Added — dev-DB seeding via Venice.ai nano-banana-2

- **`backend/scripts/seed_items.py`.** One-shot dev-only seeder that drops
  a curated set of 60 diverse `Item` rows spanning Appliances /
  Electronics / Furniture / Kitchen / Tools / Clothing / Sports /
  Outdoor across realistic household locations (Living Room, Master
  Bedroom, Home Office, Kitchen, Garage, Basement, Shed, Front Porch,
  Mudroom, etc.) with 1–3 product photos each generated on the fly via
  Venice.ai's `nano-banana-2` image model. Per-name idempotency: each
  seeded item carries `custom_fields.user_defined.seeded="v1"`, and the
  script skips items already present by name so the list stays additive
  — appending more entries and re-running picks up just the new ones.
  Resolves the seed user via `SEED_USER=<username>`, falling back to a
  `developer` user, then to a single-user fallback when only one user
  exists. Mirrors the on-disk + DB conventions in
  `backend/app/services/images.py` (filename, thumbnail path, relative
  `uploads/...` form) and generates 512×512 WebP thumbnails inline so
  the gallery renders immediately, even when the ARQ worker isn't
  active.
- **`backend/scripts/test_venice_image.py`.** Smoke test for the same
  endpoint — generates one image, writes it under `backend/uploads/`,
  prints timing + bytes. Run before the full seeder to confirm
  credentials and image quality.
- **`VENICE_API_KEY` env override** in `backend/.env.example`. The seed
  scripts pick `VENICE_API_KEY` first, then fall back to
  `LLM_API_KEY` + `LLM_BASE_URL` when the latter is pointed at Venice.

### Added — zero-IP-config setup wrapper + mDNS

- **`bin/whis` host-side wrapper** at the repo root (with a thin
  `Makefile` alias). Subcommands `up`, `down`, `certs`, `logs`, `nas`.
  Auto-detects the host's LAN IP from the OS's primary interface
  (macOS: `route -n get default` + `ipconfig getifaddr`; Linux:
  `ip route get 1.1.1.1`), filters out Docker bridge / link-local
  ranges, and writes `WHIS_LAN_IP` into a generated env file
  consumed by both `docker-compose.yml` and `docker-compose.nas.yml`.
  Falls back to manual override via the `WHIS_LAN_IP` env var.
- **mDNS publishing.** On macOS the wrapper publishes `whis.local` via
  `dns-sd -P` as a backgrounded host process (necessary because Docker
  Desktop's hidden Linux VM blocks multicast from a sidecar). On Linux
  hosts an avahi-based sidecar (`mdns/`) runs as part of compose —
  profile-gated `--profile mdns` in dev (off by default), always-on in
  the NAS variant. Households can now use a uniform
  `https://whis.local:5173` URL instead of memorising per-install IPs.
- **Auto-detected `<computer-name>.local` SAN on macOS** via `scutil
  --get LocalHostName`, so devices that resolve via macOS Bonjour
  (rather than the wrapper's `whis.local` publisher) still validate.

### Changed — zero-IP-config setup wrapper + mDNS

- **Cert SAN list is now dynamic.**
  `frontend/scripts/generate-certs.js` reads `WHIS_LAN_IP` and
  `WHIS_EXTRA_SANS` from the environment instead of carrying a
  hardcoded `192.168.1.15` and Docker bridge gateways. The OpenSSL
  `[alt_names]` block is rebuilt at runtime from the same SAN list so
  the mkcert and OpenSSL paths stay in lock-step.
- **Cert drift check.** The script now writes a SHA-256 SAN signature
  to `frontend/certs/.san-signature` after each run; subsequent runs
  exit early if the signature still matches and the existing cert is
  fresher than 350 days. Running `./bin/whis up` repeatedly is now
  effectively free.
- **In-container cert generation is now a no-op.** Previously the
  frontend container's `npm run dev` re-ran the script, which saw the
  container's bridge IPs (e.g. `192.168.156.3`) instead of the host's
  LAN IP and produced unreachable SANs. The script's existing
  `/.dockerenv` detector now exits 0 with a friendly note pointing at
  `bin/whis certs` on the host. Vite continues to start because the
  certs already exist on the bind-mounted volume.
- **`CORS_ORIGINS` interpolated, not hardcoded.**
  `docker-compose.yml` now reads
  `https://${WHIS_LAN_IP:-localhost}:5173,https://localhost:5173,https://whis.local:5173,https://frontend:5173`.
  The `:-localhost` fallback keeps a vanilla `docker compose up` working
  if the wrapper isn't used. The NAS compose's `CORS_ORIGINS` was
  already parameterised and is unchanged.

### Notes — zero-IP-config setup wrapper + mDNS

- Existing devices that already trusted `whis-dev-ca.crt` keep
  validating: only the *server* cert changes when the LAN IP drifts;
  the CA stays put. Deleting `frontend/certs/ca.crt` + `ca.key` is the
  only thing that invalidates per-device trust.
- The mDNS sidecar requires `network_mode: host` so multicast can
  reach the LAN. On Synology DSM hosts that already publish via avahi,
  set `WHIS_MDNS_HOSTNAME=whis-app` (or stop the host's avahi) to
  avoid name collisions on `whis.local`.
- Compose v2.16+ is required for the multi-`--env-file` flag the
  wrapper uses. The wrapper version-checks and bails clearly on older
  versions.

## [3.2.0] - 2026-05-04

### Added — v3.2 LLM operator dashboard

- **In-app `/settings` page (admin-only)** that lets a household admin
  configure the LLM provider end-to-end without touching `.env` or
  restarting Docker. Surfaces base URL, API key, default/vision/pricing
  models, daily cost caps, vision/pricing feature flags, response-healing
  toggle, and today's per-feature spend on one screen.
- **First-registered user is promoted to admin.** New
  `User.is_admin` boolean column (Alembic
  `20260503_0009_llm_config_and_admin`); subsequent registrations default
  to `is_admin=False`. The dev-bypass user is admin so the new page is
  reachable from a fresh dev stack. A new `require_admin` FastAPI
  dependency guards the operator surface.
- **`LLMConfig` singleton table** + new
  `app/services/llm_config.py` service that resolves the effective
  config as "DB row overrides env, env is fallback". Existing env-only
  deployments keep working unchanged; the form pre-fills with the
  currently-active env values so operators can see what's live.
- **API key encrypted at rest** with Fernet, key derived from
  `settings.SECRET_KEY` via HKDF-SHA256
  (`app/security_crypto.py`). Plaintext is never returned to the
  browser — the GET response carries only `api_key_set` + the last four
  characters.
- **Five new endpoints on `/api/llm-config*`:** `GET` (current effective
  config, redacted), `PUT` (partial update), `GET /models` (proxies the
  configured provider's `/v1/models` and annotates each entry with a
  tri-state vision / strict-JSON capability heuristic), `POST /test`
  (lists models, confirms configured names exist — no token spend), and
  `POST /test-vision` (sends a tiny embedded JPEG through
  `vision_completion` against a strict schema; stamps an `LLMUsage` row
  tagged `feature="config_test"`). `/test*` accept an optional
  `LLMConfigUpdate` body so the UI can validate prospective values
  before saving.
- **Capability heuristic (`app/llm/capabilities.py`)** walks each
  `/v1/models` entry recursively for keys like `supportsVision`,
  `multimodal`, `input_modalities`, `architecture.modality`,
  `supportsResponseSchema`, etc. Returns `True` / `False` /
  `None` (= "provider didn't expose a flag — use Test to verify"). No
  hard-coded model name allowlists — the heuristic adapts as providers
  add new models.
- **Hot reload throughout.** `OpenAICompatibleClient` and
  `DailyBudgetGuard` now read through the config service rather than
  `settings.*`, so a UI-driven model swap, key rotation, or cap change
  takes effect on the next vision/pricing request — no Docker restart
  required. The vision and pricing routers also gate on the live
  `vision_enabled` / `pricing_enabled` values rather than the static env
  flag.
- **Privacy guard preserved.** When `LLM_ALLOW_CLOUD=false` is set in
  env, the save endpoint refuses any non-RFC1918 base URL. The privacy
  kill-switch stays env-only on purpose — a runtime UI shouldn't be
  able to disable itself.
- **85 new tests** across `test_security_crypto`,
  `test_llm_config_service`, `test_capabilities`, and
  `test_llm_config_router`. Total backend test count: 400 (was 315 on
  v3.1).

### Fixed — v3.2 LLM operator dashboard

- **Response-healing toggle now actually disables the OpenRouter
  `plugins` injection**, and the plugin is **provider-gated** to
  OpenRouter (`app/llm/openai_compatible.py`). Two bugs sat on top of
  each other: the structured-completion path read
  `settings.LLM_RESPONSE_HEALING` directly (the env value), so the new
  UI toggle was a no-op even after a save; and the `plugins` key was
  emitted unconditionally on every provider, which Venice / OpenAI /
  Ollama reject with `400 Unrecognized key(s) in object: 'plugins'`.
  Fix threads the effective `response_healing` flag through the client
  constructor (with the same DB→env fallback the other fields use) and
  gates the injection on `self.provider == "openrouter"` regardless of
  the toggle. New regression test
  `test_structured_completion_skips_plugins_for_non_openrouter`
  covers the Venice case.
- **Vision self-test image upgraded from a 4×4 px probe to a 256×256
  JPEG** (`backend/assets/test_pixel.jpg`). Venice's image validator
  rejects sub-resolution inputs with
  `Supplied image did not pass validation checks.`; the new asset is
  a small (~4 KB) red square + blue circle on an off-white background
  — large enough to pass any provider's sanity check, simple enough
  for the model to describe back through the strict schema.
- **`POST /api/llm-config/test-vision` no longer 500s on a second run
  the same day** (`app/routers/llm_config.py::test_vision`). The
  endpoint blindly inserted a new `LLMUsage` row tagged
  `feature="config_test"`, but `llm_usage` has
  `UNIQUE(user_id, usage_date, feature)` — so re-running the Vision
  test against any provider that successfully returned a response
  would crash with `IntegrityError: UNIQUE constraint failed`. Fix
  switches to the same select-then-upsert pattern
  `DailyBudgetGuard.record_usage` already uses: tokens / cost /
  request_count accumulate into the existing row. New regression
  test `test_deep_test_second_run_same_day_accumulates_into_existing_row`
  exercises two consecutive calls and asserts the row was updated
  rather than duplicated.

### Notes — v3.2 operator dashboard

- Backups created on a host with `SECRET_KEY=A` and restored onto a host
  with `SECRET_KEY=B` will fail to decrypt the stored API key and fall
  back to env. Re-save the key in the UI to re-encrypt under the new
  SECRET_KEY.
- The pricing provider continues to log a nominal usage entry on
  non-LLM provider paths (eBay Browse). Threading real numbers from the
  provider wrapper is still the deferred-work item it was in v3.1.

## [3.1.1] - 2026-04-23 — pre-v3.2 baseline

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
  `DB_POOL_*` knobs. Fix uses `env_file: [.env]` on both the backend
  and worker services so the full `.env` flows into each container
  without hand-listing each var; the `environment:` block is reserved
  for compose-specific overrides (mount paths, CORS dev-LAN defaults,
  required secrets). Pydantic settings falls back to its own defaults
  for any var absent from `.env`. Worker is kept in lockstep with
  backend so fail-fast guards and feature-flagged tasks behave
  identically on both sides.

- **Vision and pricing await their async LLM calls instead of
  wrapping them in `asyncio.run`** (`app/vision/service.py`,
  `app/pricing/service.py`, routers, ARQ tasks). The previous code
  wrapped the async OpenAI client calls in `asyncio.run()` inside
  sync service methods, then called those from async FastAPI
  handlers / async ARQ tasks — both of which are already inside a
  running event loop. `asyncio.run()` raises "cannot be called from
  a running event loop", so `POST /api/vision/identify` and
  `POST /api/pricing/estimate` both crashed 500 the instant they
  actually tried to reach a provider. Now each service exposes
  `identify_async` / `estimate_async` as the canonical coroutine
  (awaited directly by the async callers), with sync `identify` /
  `estimate` kept as `asyncio.run`-backed shims for tests and
  future non-async call sites. Two new regression tests
  (`test_identify_async_awaitable_inside_running_loop`,
  `test_estimate_async_awaitable_inside_running_loop`) drive the
  async methods from inside a live loop to keep the bug from
  coming back. Bug was masked in production because of F7 (the
  feature flag never reached the container), and masked in CI
  because the existing tests mock the client with `AsyncMock`
  values that don't actually exercise `asyncio.run`.
- **OpenRouter-specific request knobs moved under `extra_body`**
  (`app/llm/openai_compatible.py`). The OpenAI SDK raises
  `TypeError: AsyncCompletions.create() got an unexpected keyword
  argument 'plugins'` when handed any kwarg it doesn't recognize;
  `plugins` (for Response Healing) and `tools: [{type:
  openrouter:web_search}]` are both OR-only extensions and must be
  nested under `extra_body` so the SDK forwards them opaquely
  instead of rejecting them. The `test_llm_openai_compat` tests now
  assert the new placement explicitly so a revert doesn't sneak
  through.

- **Item delete now cleans up image files on disk**
  (`services/items.py::delete`, `services/items.py::bulk_delete`).
  ORM cascade and the new `ON DELETE CASCADE` FK both correctly
  removed `item_images` rows, but the disk-cleanup path that
  `ImageService.delete` does for individual image deletes was never
  invoked from item delete or bulk delete — every deleted item left
  its uploaded files orphaned in `uploads/`, growing without bound.
  Extracted the disk-cleanup logic into a shared
  `remove_image_files_from_disk` helper in `services/images.py` and
  wired both `ItemService.delete` and `ItemService.bulk_delete` to
  call it for every image they remove. Bulk delete fetches
  filenames via an ownership-scoped JOIN before the bulk SQL DELETE,
  so a caller passing a mixed-ownership ID list only cleans disk for
  files belonging to items they actually owned. Three new regression
  tests cover the happy path on both delete shapes plus the
  missing-disk-file edge case.

- **ARQ tasks no longer poison the result blob with HTTPException**
  (`app/jobs/tasks/{vision,pricing,backups}.py`,
  `app/routers/jobs.py`). `GET /api/jobs/{job_id}` raised
  `DeserializationError: unable to deserialize job result` whenever
  a task surfaced an `HTTPException` because Starlette's
  `HTTPException.__init__` is kwargs-only and doesn't survive ARQ's
  pickle round-trip (`HTTPException.__init__() missing 1 required
  positional argument: 'status_code'`). Each task now catches
  `HTTPException` at its boundary and returns a serializable
  `{"ok": false, "error": <detail>, "status_code": <code>}` envelope
  instead of re-raising; the jobs router detects that shape and
  surfaces it as a `failed` `JobDetail` with the status code
  prefixed onto the error string so the polling client gets the
  same surface as a real exception result. As defense in depth the
  router also wraps `result_info()` in a `try/except
  DeserializationError` so any future un-picklable exception type
  surfaces as a failed job rather than crashing the polling
  endpoint with a 500. Eight new regression tests cover the
  per-task envelope translation plus the two new router branches.

- **LLM pricing provider now uses a two-call flow** to sidestep an
  OpenRouter middleware bug (`app/pricing/provider_llm.py`,
  `app/llm/openai_compatible.py`, `app/llm/prompts.py`,
  `app/pricing/service.py`). When `openrouter:web_search` was
  combined with `response_format: json_schema strict` in a single
  request, OR mangled every nested object in the response into a
  stringified `{completionState, entries, type}` envelope —
  confirmed across Anthropic, OpenAI, AND Google models, so it's
  an OR middleware issue rather than a model-specific quirk. The
  fix splits pricing into two calls: (1) `chat_completion` with
  `web_search` ON and no schema returns grounded analysis as
  natural text; (2) `structured_completion` with the strict
  `PRICE_ESTIMATE_SCHEMA` (no web_search) extracts that text into
  a validated `PriceEstimate`. End-to-end cost on Sonnet 4.6 lands
  at ~$0.20-0.25 per pricing lookup (cheaper than the broken
  single-call shape was when it occasionally succeeded). Two new
  prompts (`PRICING_RESEARCH_PROMPT`, `PRICING_EXTRACTION_PROMPT`)
  carry the per-call instructions; `PROMPT_VERSION` bumps to
  `v3.1.1`. The provider stashes merged token / cost / web_search
  counters across both calls on `last_usage` so the daily budget
  guard sees real numbers (closes the v3.1.0 TODO that stamped
  zero-token usage entries for LLM provider calls). The
  `structured_completion` path also strips
  `minimum`/`maximum`/`pattern`/etc. constraints from the JSON
  schema before sending — Anthropic via Azure rejects these with
  `For 'number' type, property 'minimum' is not supported`;
  Pydantic's own validation still enforces them at
  `model_validate` time so nothing is lost.

- **LLM client now surfaces upstream-error envelopes instead of
  TypeError-crashing** (`app/llm/openai_compatible.py`). OpenRouter
  occasionally returns 200 OK with a payload shaped
  `{"error": {"message", "code"}, "choices": null, "usage": null}`
  when an upstream provider hits a transient failure (observed
  with Anthropic-via-Azure 524 timeouts; the same shape comes
  from other transient upstream failures). The OpenAI SDK
  deserializes this as a `ChatCompletion` with `choices=None`,
  so accessing `choices[0]` raised `TypeError: 'NoneType' object
  is not subscriptable` — uncaught by the previous parser's
  `(AttributeError, IndexError)` clause and bubbled up as a 500
  to the caller. Extracted `_extract_content` as a shared helper
  for both `structured_completion` and `chat_completion`; it
  detects `response.error` first and surfaces the upstream
  message + code as `LLMProviderError`, defaults the
  empty-choices case to a clean error, and adds `TypeError` to
  the parsing-error catch as defense in depth. Two new
  regression tests cover the error envelope and the bare
  null-choices paths.

- **Vision model is now configurable independently of `LLM_MODEL`**
  via the new `LLM_VISION_MODEL` setting (`app/settings.py`,
  `app/vision/service.py`, `backend/.env.example`). Mirrors the
  existing `LLM_PRICING_MODEL`. Closes a regression discovered
  while running the v3.1 validation pass against the production
  `.env`: with `LLM_MODEL=anthropic/claude-sonnet-4.6` set for
  pricing reasoning, every vision call timed out (HTTP 524 from
  OpenRouter) because Sonnet 4.6's image+structured-output path
  via Azure can't compose the two within OR's gateway timeout.
  Sonnet without an image works; Sonnet without a strict schema
  works; Sonnet with both reliably 524s. The fix doesn't try to
  work around the upstream issue — it lets the operator point
  vision at a model that handles the combination cleanly
  (`google/gemini-3-flash-preview` confirmed working
  end-to-end at $0.0015/call) while pricing keeps Sonnet 4.6.
  Default sample `.env` ships with `LLM_VISION_MODEL` blank so
  `LLM_MODEL` continues to drive both features for fresh
  installs that haven't picked a separate pricing model. Added
  `google/gemini-3-flash-preview` to the cost-rate table
  (`$0.50/$3.00 per 1M`, derived from observed OR billing).

### Security

- **python-dotenv bumped to >=1.2.2,<2** to resolve
  **CVE-2026-28684** (previously pinned at 1.0.1). CI's
  `pip-audit --strict` leg would otherwise block the push.

### Compliance

- **eBay Marketplace Account Deletion exemption — regression-tested**
  (`backend/app/pricing/provider_ebay_browse.py::_parse_item_summaries`,
  `backend/tests/test_pricing_providers.py::test_ebay_parser_drops_seller_pii_for_deletion_exemption`).
  WHIS holds an exemption from eBay's deletion-notification system on
  the basis that we persist no eBay user data. The exemption is
  load-bearing — the new test feeds the parser a Browse response laden
  with seller PII (`username`, `userId`, `eiasToken`,
  `feedbackPercentage`, seller email, buyer block) and asserts none of
  it survives into the `PriceSource` list (which is what lands in
  `PriceCache.payload` and gets serialized to clients). A code-comment
  block on `_parse_item_summaries` documents the exemption commitment.
  See `docs/EBAY_INTEGRATION.md` for the full audit trail.

### Test counts (at 3.1.1)

- Backend: **335 tests** (up from 315 at v3.1.0 release):
  fixes for F6/F10a/F10b/F11/F12 + deletion-exemption regression,
  all green on SQLite + Postgres 16.
- Frontend: **95 vitest** tests, 0 ESLint errors.

### Documentation

Full doc audit + refresh sweep — every Markdown doc in the repo
verified against the actual codebase and brought current with
v3.0 (Postgres / ARQ / FTS / thumbnails / openapi codegen) and
v3.1 (vision auto-fill / pricing / shared LLM layer / privacy
kill-switch / cost caps).

- **README.md** — replace v2.0.0 tech stack (Tailwind 3.4,
  Formik+Yup, SQLite-only) with current reality (Tailwind v4,
  RHF+zod, Postgres opt-in, ARQ profile, OpenAI SDK, Caddy);
  split features into Core / v3.0 / v3.1; drop broken
  `docs/USER_GUIDE.md` link; add docker compose profile
  variants.
- **ARCHITECTURE.md** — high-level diagram now shows ARQ worker,
  Redis, Postgres, LLM provider, eBay; backend layout includes
  services/, jobs/, llm/, vision/, pricing/, ebay/, facebook/,
  schemas_llm.py, fts.py, rate_limit.py, telemetry.py,
  logging_config.py, all routers and the 8 migrations on top of
  baseline; DB schema includes price_cache (composite PK),
  llm_usage, item_images thumbnail/cascade columns, and items
  pricing columns; ADRs added for ARQ-not-Celery, OpenAI-
  compatible client, Caddy-not-nginx, strict JSON schema for
  LLM outputs; Future Considerations split into "aspirational"
  vs "already shipped" so v3.x features stop appearing on
  roadmap-style lists.
- **API.md** — bump version banner + /api/health to 3.1.0; add
  4 missing routers: jobs (v3.0), vision/pricing (v3.1), and
  facebook (v2.3); document JobReference / Union[JobReference,
  Resource] async pattern; add 402 (LLM cost cap), 429 (slowapi)
  and 503 (feature disabled) error codes; add v3.1 fields to
  Item shape (estimated_value_*, price_last_checked,
  price_provider) and ItemImage (thumbnail_path); document FTS
  search query parameter; flip "no rate limiting" claim to the
  current slowapi reality.
- **TESTING.md** — backend test count 10 -> 335, frontend
  19 jest -> 95 vitest; replace all jest examples with vitest;
  document the 4-leg backend matrix (Python 3.11/3.12 x
  SQLite/Postgres) and the four blocking CI gates beyond the
  test matrix (pip-audit, npm audit, Trivy, contract-check);
  mark ESLint as blocking; new "Compliance / Regression Tests"
  section calling out load-bearing tests (eBay deletion
  exemption, settings fail-fast, restore round-trip, cascade).
- **DEVELOPMENT.md** — Project Structure mirrors CLAUDE.md;
  jest examples replaced with vitest; add codegen workflow
  (`npm run codegen:api`); document compose profiles (worker,
  postgres, full v3.0); v3.1 LLM/eBay env config block; "Adding
  a new router" recipe; `dict()` -> `model_dump()` (Pydantic v2);
  async-job debugging section.
- **CONTRIBUTING.md** — `--port 27182` on the dev uvicorn
  command; jest -> vitest; full CI matrix shape; ESLint
  blocking; supply-chain gates section.
- **DEPLOYMENT.md** — health-check version stamp 2.0.0 -> 3.1.0.
- **SECURITY.md** — nginx -> Caddy (since v2.4); document
  slowapi per-route rate limiting (no longer "not provided");
  new v3.1 LLM/eBay secrets-management section
  (LLM_API_KEY, LLM_ALLOW_CLOUD privacy kill-switch, image/
  query egress paths, daily cost caps); 3.x added to Supported
  Versions table; cross-ref the deletion-exemption regression
  test.
- **Whole_Home_Inventory_System_WHIS_DesignDoc.md** — bump to
  3.1.0; add Phase 6 (v3.0 scale & ops) and Phase 7 (v3.1
  intelligence) entries with full feature lists; trim Future
  section to genuinely-not-yet-implemented items (RHF/data-
  router/Tailwind v4 had been listed despite shipping in v2.3+).
- **docs/EBAY_INTEGRATION.md** — full rewrite; split into the
  two real surfaces (CSV listing assist vs Browse pricing);
  document Marketplace Account Deletion exemption as load-
  bearing with regression-test reference; sandbox/production
  keying gotcha; refreshed roadmap with shipped/future split.
- **UAT_v3.1.md** — new manual UAT checklist for v3.1 covering
  vision, pricing, eBay export, Facebook, backups, PWA, error
  handling.
- **CLAUDE.md, backend/.env.example, frontend/.env.example,
  CHANGELOG.md, VALIDATION_PLAN.md** — verified current; no
  changes needed.
- **ToDo.md** — left alone (5-line personal scratchpad).


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