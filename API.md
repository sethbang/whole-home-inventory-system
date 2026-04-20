# WHIS API Documentation

REST API reference for WHIS 2.0.0. All routes are mounted under `/api` in `backend/app/main.py`.

## Base URL

- Development: `https://localhost:27182`
- Production / NAS: `https://<your-host>:27182` (or the reverse-proxy fronting it)

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

Request (form-encoded, not JSON — matches the OAuth2 spec FastAPI uses):
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

### `GET /api/users/me` — current user

Response (200): the `User` schema above.

Returns 401 if the token is missing, expired, or invalid (unless `BYPASS_AUTH=true`).

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
  "custom_fields": { "any_user_defined_key": "any" },
  "images": [ ItemImage ],
  "created_at": "ISO datetime",
  "updated_at": "ISO datetime"
}
```

### Endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/items/` | Create an item (note trailing slash — the app sets `redirect_slashes=False`) |
| `GET`  | `/api/items` | List items (paginated) |
| `GET`  | `/api/items/{item_id}` | Fetch one |
| `PUT`  | `/api/items/{item_id}` | Update |
| `DELETE` | `/api/items/{item_id}` | Delete (cascades to item images) |
| `POST` | `/api/items/bulk-delete` | Body: `{"item_ids": ["uuid", ...]}` |
| `GET`  | `/api/items/barcode/{barcode}` | Lookup by barcode; 404 if absent |
| `GET`  | `/api/items/export/data` | Export items as CSV or JSON (`?format=csv|json`) |
| `POST` | `/api/items/import` | Upload a CSV or JSON file (`multipart/form-data`, field name `file`) |
| `GET`  | `/api/categories` | Distinct categories currently in use |
| `GET`  | `/api/locations` | Distinct locations currently in use |

#### `GET /api/items` query parameters

- `query` — full-text match across name/category/location/brand (case-insensitive)
- `category`, `location` — exact-match filters
- `min_value`, `max_value` — numeric range on `current_value`
- `sort_by` — field name, e.g. `created_at`, `current_value`
- `sort_desc` — boolean
- `page` (default 1), `page_size` (default 20)

Response:
```json
{
  "items": [ Item, ... ],
  "total": 42,
  "page": 1,
  "page_size": 20
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
  "created_at": "ISO datetime"
}
```

Images are served statically at `/uploads/<filename>`.

### Endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST`   | `/api/items/{item_id}/images` | Upload a single image for an item (`multipart/form-data`, field name `file`) |
| `GET`    | `/api/items/{item_id}/images` | List images for an item |
| `DELETE` | `/api/images/{image_id}` | Delete an image (by image id, not `/items/{item_id}/images/{image_id}`) |

Upload validation (enforced server-side in 2.0.0):
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

## Backups API

Backups are zip archives containing a JSON manifest plus copies of every image file.

| Method | Path | Purpose |
|---|---|---|
| `POST`   | `/api/backups` | Create a new backup synchronously |
| `GET`    | `/api/backups` | List backups for the current user |
| `POST`   | `/api/backups/upload` | Upload an existing backup zip (`multipart/form-data`, field `file`) |
| `POST`   | `/api/backups/{backup_id}/restore` | **Destructive** — deletes current items and restores from the backup |
| `DELETE` | `/api/backups/{backup_id}` | Delete a backup record + file |
| `GET`    | `/api/backups/{backup_id}/download` | Stream the backup zip (`Content-Disposition: attachment`) |

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

### Restore response

```json
{
  "success": true,
  "message": "Backup restored successfully",
  "items_restored": 42,
  "images_restored": 17,
  "errors": ["string", ...] | null
}
```

## eBay API (Phase 1 — CSV export only)

| Method | Path | Purpose |
|---|---|---|
| `GET`  | `/api/ebay/categories` | Enumerate available eBay categories; with `?item_id=...` also returns a suggested category based on the item's data |
| `POST` | `/api/ebay/items/{item_id}/ebay-fields` | Attach/update eBay-specific fields on an item |
| `POST` | `/api/ebay/export` | Body: `{"item_ids": [...], "default_fields": {...}?}`. Returns a link to a generated Seller Hub CSV |

## System endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/health` | `{"status": "healthy", "version": "2.0.0"}` — unauthenticated |
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

### 500 Internal Server Error
```json
{"detail": "Internal server error", "status_code": 500}
```

By default the 500 response body is opaque. Set `DEBUG=true` in the backend's env (dev only) to include `type` and `stack_trace` fields.

## Things the application does NOT provide

- **Rate limiting.** Terminate at your reverse proxy.
- **OAuth/OIDC/MFA.** Only the password-grant JWT flow above.
- **Refresh tokens.** Tokens hard-expire after `ACCESS_TOKEN_EXPIRE_MINUTES` (default 30).
- **`X-API-Version` response header.** Query `/api/health` instead.

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

### Python

```python
import httpx

base = "https://localhost:27182"
with httpx.Client(verify=False) as c:
    token = c.post(
        f"{base}/api/token",
        data={"grant_type": "password", "username": "alice", "password": "..."},
    ).json()["access_token"]
    items = c.get(f"{base}/api/items", headers={"Authorization": f"Bearer {token}"}).json()
    print(items["total"])
```

### TypeScript (axios)

```typescript
import axios from 'axios';

const client = axios.create({ baseURL: 'https://localhost:27182', withCredentials: true });

const params = new URLSearchParams();
params.append('grant_type', 'password');
params.append('username', 'alice');
params.append('password', '...');
const { data: token } = await client.post('/api/token', params, {
  headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
});
client.defaults.headers.common.Authorization = `Bearer ${token.access_token}`;

const { data: items } = await client.get('/api/items');
```

## Changelog

See `CHANGELOG.md` for the full version history. Breaking API-visible changes since 1.x:

- Login endpoint is `POST /api/token` (not `/api/auth/login`) and uses the OAuth2 form-encoded flow.
- Register endpoint is `POST /api/register` (not `/api/auth/register`).
- Image delete is `DELETE /api/images/{image_id}` (by image id, no item id in the path).
- Backup creation is `POST /api/backups` (not `POST /api/backups/create`).
- Analytics endpoints returned to their named forms (`value-by-category`, etc.) — there is no `/api/analytics/summary`.
