# WHIS API Documentation

REST API reference for **WHIS 3.3.1**. All routes are mounted under `/api` in `backend/app/main.py`. Routers themselves do not carry the `/api` prefix — `main.py` adds it.

## Base URL

- Development: `https://localhost:27182`
- Production / NAS: `https://<your-host>` (Caddy fronts the stack on 80/443 and proxies `/api/...` to the backend)

## Authentication

WHIS uses JWT bearer tokens signed with `SECRET_KEY` (HS256 by default). Tokens are obtained via the OAuth2 password flow (form-encoded, not JSON) and sent as `Authorization: Bearer <token>`.

### `POST /api/register` — create a user

Request (JSON):
```json
{
  "email": "alice@example.com",
  "username": "alice",
  "password": "correct-horse-battery-staple"
}
```

Response (200):
```json
{
  "id": "a7a41c99-...",
  "email": "alice@example.com",
  "username": "alice",
  "is_active": true,
  "created_at": "2026-04-20T12:00:00"
}
```

### `POST /api/token` — exchange credentials for a JWT

Request (form-encoded — matches the OAuth2 spec FastAPI uses):
```
Content-Type: application/x-www-form-urlencoded

grant_type=password&username=alice&password=correct-horse-battery-staple
```

Response (200):
```json
{
  "access_token": "eyJhbGci...",
  "token_type": "bearer"
}
```

When `BYPASS_AUTH=true` (dev only), the endpoint returns a hardcoded `"access_token": "dev_token"`; all authenticated endpoints then also honor the bypass.

**Rate-limited:** 5 requests/minute per IP via slowapi.

### `GET /api/users/me` — current user

Response (200): the `User` schema above. Returns 401 if the token is missing, expired, or invalid (unless `BYPASS_AUTH=true`).

## Items API

### The `Item` shape

```json
{
  "id": "uuid",
  "owner_id": "uuid",
  "name": "string",
  "category": "string",
  "location": "string",
  "brand": "string | null",
  "model_number": "string | null",
  "serial_number": "string | null",
  "barcode": "string | null",
  "purchase_date": "ISO datetime | null",
  "purchase_price": "number | null",
  "current_value": "number | null",
  "warranty_expiration": "ISO datetime | null",
  "notes": "string | null",
  "custom_fields": {
    "ebay": {/* EbayFields, see docs/EBAY_INTEGRATION.md */} | null,
    "facebook": {/* FbFields */} | null,
    "user_defined": {"any_user_key": "any"} | null
  },
  "images": [ ItemImage ],
  "created_at": "ISO datetime",
  "updated_at": "ISO datetime",

  /* v3.1 pricing fields — populated by PricingService.estimate.
     NULL until the first estimate is requested for the item. */
  "estimated_value_low": "number | null",
  "estimated_value_median": "number | null",
  "estimated_value_high": "number | null",
  "price_last_checked": "ISO datetime | null",
  "price_provider": "string | null"
}
```

`custom_fields` is a strict-typed JSON sub-object — unknown top-level keys are rejected at validation time. `user_defined` is the free-form bag for operator-defined fields.

### Endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/items/` | Create an item (note trailing slash — `redirect_slashes=False`) |
| `GET`  | `/api/items` | List items (paginated, filterable, FTS-searchable) |
| `GET`  | `/api/items/{item_id}` | Fetch one |
| `PUT`  | `/api/items/{item_id}` | Update |
| `DELETE` | `/api/items/{item_id}` | Delete (cascades to item images on disk) |
| `POST` | `/api/items/bulk-delete` | Body: `{"item_ids": ["uuid", ...]}`. Cleans image files for all. |
| `GET`  | `/api/items/barcode/{barcode}` | Lookup by barcode; 404 if absent |
| `GET`  | `/api/items/export/data` | Export items as CSV or JSON (`?format=csv|json`) |
| `POST` | `/api/items/import` | Upload a CSV or JSON file (`multipart/form-data`, field `file`) |
| `GET`  | `/api/categories` | Distinct categories currently in use |
| `GET`  | `/api/locations` | Distinct locations currently in use |
| `GET`  | `/api/locations/counts` | Per-location item counts for the caller (v3.3, drives the Browse page's room sidebar): `[{"location": "Kitchen", "count": 12}, ...]`. Null/empty locations excluded; sorted by name |

#### `GET /api/items` query parameters

- `query` — full-text search across name/category/location/brand/model/notes (v3.0: SQLite FTS5 / Postgres `tsvector`, case-insensitive). On Postgres also ranks results by relevance.
- `category`, `location` — exact-match filters
- `min_value`, `max_value` — numeric range on `current_value`
- `sort_by` — field name, e.g. `created_at`, `current_value`, `estimated_value_median`
- `sort_desc` — boolean
- `page` (default 1), `page_size` (default 10)

Response:
```json
{
  "items": [ Item, ... ],
  "total": 42,
  "page": 1,
  "page_size": 10
}
```

## Images API

### The `ItemImage` shape

```json
{
  "id": "uuid",
  "item_id": "uuid",
  "filename": "20260420_120000_<uuid>.png",
  "file_path": "uploads/20260420_120000_<uuid>.png",
  "thumbnail_path": "uploads/thumb_20260420_120000_<uuid>.webp | null",
  "thumbnail_generated_at": "ISO datetime | null",
  "created_at": "ISO datetime"
}
```

Images are served statically at `/uploads/<filename>`. Thumbnails are produced asynchronously by the v3.0 `thumbnail_generate` ARQ task — `thumbnail_path` is `null` until generation completes; the frontend falls back to `file_path` until then.

### Endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST`   | `/api/items/{item_id}/images` | Upload a single image (`multipart/form-data`, field `file`) |
| `GET`    | `/api/items/{item_id}/images` | List images for an item |
| `DELETE` | `/api/images/{image_id}` | Delete an image (by image id, not `/items/{item_id}/images/{image_id}`). Removes both the full-res file and its thumbnail from disk. |

Upload validation:
- Magic-byte verification via Pillow — spoofed `Content-Type` is rejected
- Max size: `settings.MAX_UPLOAD_BYTES` (default 10 MB) → 413 Payload Too Large
- Max dimensions: `settings.MAX_IMAGE_DIMENSION` px on the long side (default 8000) → 400
- Allowed formats: JPEG, PNG, WebP, HEIC/HEIF

## Analytics API

All endpoints require authentication. Scoped to the current user's items.

| Method | Path | Returns |
|---|---|---|
| `GET` | `/api/analytics/value-by-category` | Array of `{category, item_count, total_value}` |
| `GET` | `/api/analytics/value-by-location` | Array of `{location, item_count, total_value}` |
| `GET` | `/api/analytics/value-trends`      | `{total_purchase_value, total_current_value, value_change, value_change_percentage}` |
| `GET` | `/api/analytics/warranty-status`   | `{expiring_soon: [], expired: [], active: []}` — each entry `{id, name, expiration_date}` |
| `GET` | `/api/analytics/age-analysis`      | `{"0-1 year": {count, total_value, items: [...]}, "1-3 years": ..., "3-5 years": ..., "5+ years": ...}` |

These are still hand-typed on the frontend (not Pydantic-modeled on the backend) — types live in `frontend/src/api/types.ts` rather than the generated `openapi.d.ts`.

## Backups API

Backups are zip archives containing a JSON manifest plus copies of every image file referenced by the user's items.

| Method | Path | Returns | Notes |
|---|---|---|---|
| `POST`   | `/api/backups` | `JobReference` or `Backup` | Async via worker if `REDIS_URL` set, sync otherwise |
| `GET`    | `/api/backups` | `BackupList` | List backups for the current user |
| `POST`   | `/api/backups/upload` | `Backup` | Upload an existing backup zip (`multipart/form-data`, field `file`) |
| `POST`   | `/api/backups/{backup_id}/restore` | `JobReference` or restore-result | **Destructive** — deletes current items and restores from the backup. Also async-capable. Requires confirmation body. |
| `DELETE` | `/api/backups/{backup_id}` | `204` | Delete a backup record + file |
| `GET`    | `/api/backups/{backup_id}/download` | `application/zip` | Stream the backup zip (`Content-Disposition: attachment`) |

### The `Backup` shape

```json
{
  "id": "uuid",
  "owner_id": "uuid",
  "filename": "backup_<user-id>_<timestamp>.zip",
  "file_path": "/app/backend/backups/backup_....zip",
  "size_bytes": 12345,
  "item_count": 42,
  "image_count": 17,
  "created_at": "ISO datetime",
  "status": "completed | failed | in_progress",
  "error_message": "string | null"
}
```

### Async-capable response pattern

Endpoints that may run via the ARQ worker return a discriminated union:

```json
// Async path — when REDIS_URL is configured
{ "kind": "job", "job_id": "abc123" }

// Sync path — when REDIS_URL is unset, the resource is returned directly
{ "id": "...", "filename": "...", ... }
```

The frontend branches on the `kind` field. When `kind == "job"`, poll `GET /api/jobs/{job_id}` until `status` is terminal.

### Restore response (sync path)

```json
{
  "success": true,
  "message": "Backup restored successfully",
  "items_restored": 42,
  "images_restored": 17,
  "errors": ["string", ...] | null
}
```

## Jobs API (v3.0)

When `REDIS_URL` is configured and the ARQ worker is running, heavy operations (backup create/restore, vision identify, pricing estimate, thumbnail generate) enqueue to a job queue and return a `JobReference`. The frontend polls this endpoint to track progress.

### `GET /api/jobs/{job_id}`

Response (200) — `JobDetail`:
```json
{
  "job_id": "abc123",
  "status": "queued | running | complete | failed | not_found",
  "result": { /* task-specific shape, populated only on complete */ } | null,
  "error": "string | null"
}
```

ARQ status mapping:
- `deferred` + `queued` → `queued` (frontend doesn't need to distinguish)
- `in_progress` → `running`
- `complete` → `complete` or `failed` (depending on whether the task raised)
- absent from Redis → `not_found`

Task-specific `result` shapes:
- **Backup create**: full `Backup` object
- **Backup restore**: `{success, items_restored, images_restored, errors}`
- **Vision identify**: full `VisionResult` (see Vision API)
- **Pricing estimate**: full `PriceEstimateEnvelope` (see Pricing API)
- **Thumbnail generate**: `{thumbnail_path, generated_at}`

Returns 503 if `REDIS_URL` is unset (no job queue to inspect).

Returns 403 if the requested job belongs to a different user (enforced by inspecting the job's stored `user_id` kwarg).

## Vision API (v3.1)

Image-based item identification via an LLM. Off by default — enable with `VISION_ENABLED=true` + `LLM_BASE_URL` + `LLM_API_KEY`.

### `POST /api/vision/identify`

Request (`multipart/form-data`):
- `files` — 1..`VISION_MAX_IMAGES_PER_REQUEST` image uploads (default cap: 4)
- `hints` (optional) — JSON object with user-supplied hints (`{"brand": "Canon", "category": "Camera"}`)

Response (200) — `JobReference` (when worker active) or `VisionResult` (sync fallback):

```json
// VisionResult shape
{
  "suggestion": {
    "name": "Canon EOS R5",
    "brand": "Canon",
    "model_number": "EOS R5",
    "confidence": 0.92,
    "warnings": ["Serial obscured"],
    "suggested_tags": ["camera", "mirrorless", "Canon"],
    "ebay_item_specifics": { "Type": "Mirrorless", "Megapixels": "45 MP" },
    "fb_item_specifics": { "category": "Cameras & Photography" }
  },
  "provider": "openrouter",
  "model": "google/gemini-3-flash-preview",
  "prompt_version": "v3.1.1",
  "tokens_in": 1234,
  "tokens_out": 567,
  "cost_usd_estimate": 0.0015,
  "queried_at": "2026-05-03T01:23:45Z"
}
```

Errors:
- `400` — no images, too many images, invalid `hints` JSON, malformed image bytes
- `402` — daily LLM cost cap reached (`VISION_DAILY_COST_CAP_USD`)
- `413` — image exceeds `MAX_UPLOAD_BYTES`
- `503` — `VISION_ENABLED=false`

## Pricing API (v3.1)

Resale-value estimation routed through the providers in `PRICING_PROVIDERS` (default `ebay,llm`). Off by default — enable with `PRICING_ENABLED=true` + LLM config (and optionally `EBAY_APP_ID` / `EBAY_CERT_ID` for the priority eBay Browse provider).

### `POST /api/pricing/estimate`

Body:
```json
{
  "item_id": "uuid",          // exactly one of these
  "metadata": {                // ↑ or ↓
    "brand": "Apple",
    "model_number": "A2179",
    "name": "MacBook Air 13",
    "condition": "used",
    "year": 2020
  }
}
```

Returns `JobReference` (when worker active) or `PriceEstimateEnvelope` (sync). 422 if both / neither input is provided.

### `POST /api/pricing/refresh/{item_id}`

Force a re-fetch, ignoring the cache. Same return shape. **Rate-limited:** 5 requests/minute.

### `GET /api/pricing/estimate/{item_id}`

Cache-first lookup for an existing item. Same return shape.

### `PriceEstimateEnvelope` shape

```json
{
  "estimate": {
    "currency": "USD",
    "low": 24.49,
    "median": 124.00,
    "high": 226.40,
    "sample_count": 30,
    "confidence": 0.541,
    "sources": [
      {
        "title": "MacBook Air 13\" A2179 LCD Assembly",
        "url": "https://www.ebay.com/itm/...",
        "price": 119.0,
        "condition": "Used",
        "sold_date": null,
        "source_site": "ebay"
      }
      /* ... up to ~10 representative comparables */
    ]
  },
  "provider": "ebay",
  "prompt_version": "",
  "queried_at": "2026-05-03T01:23:45Z",
  "cache_hit": false,
  "cost_usd_estimate": 0.0
}
```

Provider semantics:
- `ebay` — `cost_usd_estimate=0`, `prompt_version=""` (no LLM cost)
- `llm` — `cost_usd_estimate>0`, `prompt_version` stamped (e.g. `"v3.1.1"`)

Errors:
- `400` — missing brand+model+name, invalid input
- `402` — daily LLM cost cap reached (`PRICING_DAILY_COST_CAP_USD`) — only fires on the `llm` provider; eBay-only requests are unaffected
- `429` — exceeded `/api/pricing/refresh/{item_id}` rate limit (5/min per IP)
- `503` — `PRICING_ENABLED=false`

## LLM config API (v3.2 — admin only)

Backs the in-app Settings page. Every route requires an admin user
(the first registered account is promoted to admin); others get `403`.

| Method | Path | Purpose |
|---|---|---|
| `GET`  | `/api/llm-config` | Effective LLM config (`LLMConfigRead`). Never returns the plaintext key — only `api_key_set` + `api_key_last4`. `sources` gives per-field provenance (`db` / `env` / `default`); `today_*_cost_usd` report the caller's spend today |
| `PUT`  | `/api/llm-config` | Partial update (`LLMConfigUpdate`) — every field optional; `null` leaves a field unchanged, empty string / `0` clears it back to the env value. `api_key`: omitted = keep, `""` = clear, non-empty = encrypt and store. `400` on invalid values. Returns the new `LLMConfigRead` |
| `GET`  | `/api/llm-config/models` | Models listed by the configured provider, annotated for the UI |
| `POST` | `/api/llm-config/test` | Quick check: URL + key reachable, configured models exist. Optional `LLMConfigUpdate` body tests unsaved values. Returns `{ok, base_url, model, detail, checks}` |
| `POST` | `/api/llm-config/test-vision` | Deep check: sends a tiny image through the vision path with a strict schema. Same optional body. Returns `{ok, model, detail, parsed_response, usage, cost_usd}` |

See [SECURITY.md](SECURITY.md) for how the stored key is encrypted and
what rotating `SECRET_KEY` does to it.

## eBay API (v2.3 — CSV listing assist)

| Method | Path | Purpose |
|---|---|---|
| `GET`  | `/api/ebay/categories` | Enumerate eBay categories; with `?item_id=...` returns a suggested category for the item |
| `POST` | `/api/ebay/items/{item_id}/ebay-fields` | Attach/update eBay-specific fields on an item (`custom_fields.ebay`) |
| `POST` | `/api/ebay/export` | Body: `{"item_ids": [...], "default_fields": {...}?}`. **Streams** a Seller Hub CSV directly (no intermediate file) |

The v3.1 eBay Browse API for pricing lives under `/api/pricing/...`, not `/api/ebay/...`. See [docs/EBAY_INTEGRATION.md](docs/EBAY_INTEGRATION.md) for the full split.

## Facebook Marketplace API (v2.3)

Assist-only — Meta has no public listing API for individual sellers. Output is operator-copied into Marketplace's compose UI, or imported into Meta Commerce as a catalog CSV.

| Method | Path | Purpose |
|---|---|---|
| `GET`  | `/api/facebook/categories` | Enumerate FB Marketplace categories; with `?item_id=...` returns a suggested category |
| `POST` | `/api/facebook/items/{item_id}/fb-fields` | Attach/update FB-specific fields on an item (`custom_fields.facebook`) |
| `POST` | `/api/facebook/items/{item_id}/copy-paste` | Returns `{title, price, description, category, condition}` formatted for the operator to paste into Marketplace |
| `GET`  | `/api/facebook/items/{item_id}/images.zip` | Stream a zip of the item's images for upload |
| `POST` | `/api/facebook/export` | Body: `{"item_ids": [...]}`. Streams a Meta Commerce catalog CSV (`id,title,description,availability,condition,price,link,image_link,brand`) |

## System endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/health` | `{"status": "healthy", "version": "3.3.1"}` — unauthenticated |
| `OPTIONS` | `/{any}` | CORS preflight handler |

## Error responses

### 400 Bad Request
```json
{"detail": "Error message", "status_code": 400}
```

### 401 Unauthorized
```json
{"detail": "Not authenticated", "status_code": 401}
```

### 402 Payment Required (v3.1)
```json
{
  "detail": "Daily LLM cost cap reached for vision (5.00 USD).",
  "status_code": 402
}
```

### 403 Forbidden (v3.0)
```json
{"detail": "Job belongs to a different user", "status_code": 403}
```

### 404 Not Found
```json
{"detail": "Item not found", "status_code": 404}
```

### 413 Payload Too Large
```json
{"detail": "File exceeds maximum size of 10485760 bytes", "status_code": 413}
```

### 422 Validation Error
FastAPI / Pydantic validation errors:
```json
{
  "detail": [
    { "loc": ["body", "name"], "msg": "field required", "type": "value_error.missing" }
  ]
}
```

### 429 Too Many Requests (v2.2 — slowapi)
```json
{"detail": "Rate limit exceeded: 5 per 1 minute", "status_code": 429}
```

Per-route limits via slowapi: `/api/token` (5/min), `/api/pricing/refresh/{item_id}` (5/min), and other auth/cost-sensitive routes.

### 500 Internal Server Error
```json
{"detail": "Internal server error", "status_code": 500}
```

By default the 500 response body is opaque. Set `DEBUG=true` in the backend's env (dev only) to include `type` and `stack_trace` fields.

### 503 Service Unavailable (v3.0/v3.1)
```json
{"detail": "Vision auto-fill is disabled on this deployment.", "status_code": 503}
```

Returned when a feature-flagged endpoint is hit while disabled (`VISION_ENABLED=false`, `PRICING_ENABLED=false`), or when a `/api/jobs/{id}` lookup fires without `REDIS_URL` configured.

## Things the application provides

- ✅ JWT auth (PyJWT, HS256 by default)
- ✅ Per-route rate limiting (slowapi, in-app)
- ✅ Magic-byte upload validation
- ✅ HTTPS enforcement (no HTTP listener)
- ✅ Structured logging (structlog, JSON in prod)
- ✅ OpenTelemetry tracing (opt-in via `OTEL_ENABLED=true`)
- ✅ ARQ background job queue (opt-in via `REDIS_URL`)
- ✅ Daily LLM cost caps (per-user, per-feature)
- ✅ Privacy kill-switch (`LLM_ALLOW_CLOUD=false`)

## Things the application does NOT provide

- **WAF / IP-level rate limiting / HSTS** — terminate at your reverse proxy (Caddy supports `rate_limit` middleware).
- **OAuth/OIDC/MFA** — only the password-grant JWT flow above.
- **Refresh tokens** — tokens hard-expire after `ACCESS_TOKEN_EXPIRE_MINUTES` (default 30). Re-login required.
- **`X-API-Version` response header** — query `/api/health` instead.
- **Multi-tenancy / RBAC** — single user-role model.

## Examples

### curl — login and list items

```bash
TOKEN=$(curl -sk -X POST https://localhost:27182/api/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password&username=alice&password=correct-horse-battery-staple" \
  | jq -r .access_token)

curl -sk https://localhost:27182/api/items \
  -H "Authorization: Bearer $TOKEN" | jq .
```

### curl — pricing estimate (anonymous metadata path)

```bash
curl -sk -X POST https://localhost:27182/api/pricing/estimate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"metadata":{"brand":"Apple","model_number":"A2179","name":"MacBook Air 13","condition":"used"}}' \
  | jq .
```

### Python

```python
import httpx

base = "https://localhost:27182"
with httpx.Client(verify=False) as c:
    token = c.post(
        f"{base}/api/token",
        data={"grant_type": "password", "username": "alice", "password": "..."},
    ).json()["access_token"]

    items = c.get(
        f"{base}/api/items",
        headers={"Authorization": f"Bearer {token}"},
    ).json()
    print(items["total"])
```

### TypeScript (axios — auto-typed via openapi.d.ts)

```typescript
import axios from 'axios';
import type { components } from './api/openapi';

type Item = components['schemas']['Item'];

const client = axios.create({ baseURL: 'https://localhost:27182' });

const params = new URLSearchParams();
params.append('grant_type', 'password');
params.append('username', 'alice');
params.append('password', '...');
const { data: token } = await client.post('/api/token', params, {
  headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
});
client.defaults.headers.common.Authorization = `Bearer ${token.access_token}`;

const { data } = await client.get<{ items: Item[]; total: number }>('/api/items');
```

The frontend itself uses `frontend/src/api/openapi.d.ts` (regenerated by `npm run codegen:api`) so all responses are end-to-end type-safe; CI's `contract-check` job blocks pushes that drift.

## Changelog (API-visible breaking changes)

See [CHANGELOG.md](CHANGELOG.md) for the full history. Breaking API-visible changes since 1.x:

- **2.0.0** — Login is `POST /api/token` (not `/api/auth/login`); register is `POST /api/register`. Image delete is `DELETE /api/images/{image_id}` (no item id in path). Backup creation is `POST /api/backups` (not `POST /api/backups/create`).
- **2.2.0** — Per-route rate limits introduced via slowapi; affected endpoints now return 429.
- **3.0.0** — Backup create/restore + thumbnail generation can return a `JobReference` instead of the full resource when the worker profile is active. Frontend should branch on `kind: "job"`. New `/api/jobs/{job_id}` endpoint.
- **3.1.0** — `Item` shape gains `estimated_value_*`, `price_last_checked`, `price_provider`. `ItemImage` gains `thumbnail_path` + `thumbnail_generated_at`. New routers: `/api/vision/...`, `/api/pricing/...`. New error codes: 402 (cost cap), 503 (feature disabled).
- **3.2.0** — `User` gains `is_admin`; the first registered user becomes admin. New admin-only `/api/llm-config/...` routers.
- **3.3.0** — New `GET /api/locations/counts`.
- **3.3.1** — `POST /api/register` is now rate-limited (5/min/IP) and can return 429.
