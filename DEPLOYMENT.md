# Deploying WHIS on Synology NAS

This guide explains how to deploy WHIS on a Synology NAS (or any Docker host) using the committed `docker-compose.nas.yml` file.

## Prerequisites

1. Synology NAS with **Container Manager** (or the older Docker package) installed
2. Git on the NAS (Package Center) — or clone on your workstation and `scp` the project
3. Shell access via SSH or DSM's terminal
4. Your user added to the `docker` group:
   ```bash
   sudo synogroup --add docker $(whoami)
   ```
   Log out and back in for the group change to take effect.

## One-time setup

### 1. Clone the repository

```bash
cd /volume1/docker
git clone https://github.com/sethbang/whole-home-inventory-system.git
cd whole-home-inventory-system
```

### 2. Create persistent data directories

```bash
mkdir -p /volume1/docker/whole-home-inventory-system/{database,uploads,backups,certs,caddy-data,caddy-config,redis-data}
```

The volume mount paths in `docker-compose.nas.yml` expect this layout:

- `database`, `uploads`, `backups` — SQLite DB, user images, in-app backup zips
- `certs` — TLS material the backend uses for its internal HTTPS listener (see step 4)
- `caddy-data`, `caddy-config` — persist Caddy's ACME account keys, Let's Encrypt certs, and the internal CA across restarts
- `redis-data` — v3.0 ARQ job queue state. Survives container restarts so in-flight jobs don't get lost.

### 3. Generate a `SECRET_KEY`

```bash
cat > .env <<EOF
SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(64))')
EOF
chmod 600 .env
```

Optional env vars you can set in the same `.env`:

- `WHIS_DOMAIN` — hostname Caddy serves on. Defaults to `whis.local`. When the value resolves to a public IP Caddy auto-provisions a Let's Encrypt cert on first request; otherwise it serves via its internal CA (see step 5).
- `CADDY_ACME_EMAIL` — email address registered with Let's Encrypt. Defaults to `admin@whis.local`; set to a real inbox you control before pointing `WHIS_DOMAIN` at a public address.
- `NAS_ORIGINS` — override the default CORS origins when fronting the stack with an *additional* upstream reverse proxy. The default (`https://${WHIS_DOMAIN}`) already covers the common case.
- `LOG_LEVEL` — defaults to `INFO`; set to `DEBUG` temporarily for troubleshooting.
- `ACCESS_TOKEN_EXPIRE_MINUTES` — defaults to 30.
- `DATABASE_URL` — defaults to `sqlite:////app/database/whis.db`. Set to `postgresql+psycopg://whis:whis@postgres:5432/whis` if you want to run Postgres alongside (requires adding a `postgres` service to this compose file; see the main `docker-compose.yml` for the reference shape).
- `REDIS_URL` — defaults to `redis://redis:6379/0`. NAS deployments run Redis + the ARQ worker by default so 15-45s backup operations don't block uvicorn. Set to empty to force synchronous fallback.

v3.1 intelligence features (both default OFF):
- `VISION_ENABLED` / `PRICING_ENABLED` — flip to `true` to turn on vision auto-fill and item-value pricing. Both require `LLM_BASE_URL` + `LLM_API_KEY`; the app refuses to start if you flip them on without the LLM config.
- `LLM_BASE_URL` — any OpenAI-compatible API. Common targets: `https://openrouter.ai/api/v1` (canonical; supports structured outputs + response-healing + the `openrouter:web_search` server tool), `https://api.venice.ai/api/v1`, `http://ollama:11434/v1` (local).
- `LLM_API_KEY` — your provider API key.
- `LLM_ALLOW_CLOUD` — set to `false` for privacy mode. The app then refuses to start if `LLM_BASE_URL` doesn't resolve to localhost / a private IP / a known container hostname. Belt-and-suspenders against accidentally leaving OpenRouter configured when you meant to use Ollama.
- `VISION_DAILY_COST_CAP_USD` / `PRICING_DAILY_COST_CAP_USD` — per-(user, day) spend caps. Over-cap returns HTTP 402; a new day resets the rollup. Set to 0 to disable.
- `EBAY_APP_ID` + `EBAY_CERT_ID` — optional. When set, the eBay Browse API provider activates and runs before the LLM provider (per `PRICING_PROVIDERS=ebay,llm`). Without them pricing falls back to LLM + OR web_search only.

The compose file refuses to start without `SECRET_KEY`; this is intentional (prevents shipping a placeholder secret in production).

### 4. Stage the backend TLS certs

The backend speaks HTTPS even inside the compose network, so it needs a
key + cert pair at `/app/certs`. On a workstation with
[mkcert](https://github.com/FiloSottile/mkcert) installed:

```bash
cd frontend
node scripts/generate-certs.js
scp -r certs/ <nas>:/volume1/docker/whole-home-inventory-system/certs/
```

This produces `key.pem` + `cert.pem` (SANs cover the household's LAN IPs)
plus a `whis-dev-ca.crt` you can install on devices for direct backend
access. If mkcert isn't available the script falls back to an OpenSSL CA
flow — same output, slightly more to install per-device.

### 5. Trust Caddy's certs

- **`WHIS_DOMAIN` points at a public DNS name** — nothing to do. Caddy
  obtains a Let's Encrypt cert on first request and renews automatically.
  Browsers trust it out of the box.
- **`WHIS_DOMAIN=whis.local` (the default) or any non-public host** — Caddy
  uses its own internal CA. After first boot extract the root cert and
  install it on each household device:

  ```bash
  docker compose -f docker-compose.nas.yml exec caddy \
      cat /data/caddy/pki/authorities/local/root.crt \
      > whis-caddy-root.crt
  ```

  Install instructions per OS live in `frontend/certs/CERTIFICATE-SETUP.md`
  (the generate-certs flow produces it); the same steps apply to
  `whis-caddy-root.crt`.

## Deployment

### Command line

```bash
cd /volume1/docker/whole-home-inventory-system
docker compose -f docker-compose.nas.yml up -d --build
docker compose -f docker-compose.nas.yml logs backend | head -30
```

On first boot after upgrading from pre-2.0.0 databases, you should see `scripts/bootstrap.py` clear the legacy `cafb3d2c47a1` Alembic stamp and run the new baseline migration. Your existing data is preserved.

### Container Manager UI

The modern path:

1. Open Container Manager → **Project** → **Create**
2. Point it at `/volume1/docker/whole-home-inventory-system`
3. Select `docker-compose.nas.yml`
4. Supply the same `SECRET_KEY` via the environment section
5. Run

## Verification

After the stack is up:

- Both services healthy: `docker compose -f docker-compose.nas.yml ps` reports `healthy` for `backend` and `caddy` within ~30s.
- Backend direct health: `docker compose -f docker-compose.nas.yml exec backend curl -kfsS https://localhost:27182/api/health` → `{"status":"healthy","version":"3.1.0"}`.
- Frontend through Caddy: open `https://${WHIS_DOMAIN}/` in a browser. The SPA should load and `/api/...` requests should succeed same-origin.

## HTTPS and external exposure

Caddy terminates TLS on ports 80/443 directly — no DSM reverse proxy
required for the common case. For external exposure:

1. Point your public DNS (`A`/`AAAA`) at the NAS, set `WHIS_DOMAIN` to that
   hostname, and set `CADDY_ACME_EMAIL` to an inbox you control. Let's
   Encrypt will issue a cert on first request.
2. Forward TCP 80 and 443 from the router to the NAS. TCP 80 is required
   for the HTTP-01 ACME challenge even if you only serve over 443.
3. Leave `NAS_ORIGINS` unset — it defaults to `https://${WHIS_DOMAIN}`,
   which matches what the browser sends.
4. Consider adding rate limiting either in Caddy (e.g. a `rate_limit`
   middleware) or at the router — the application does not enforce it.

## Maintenance

### Viewing logs
```bash
docker compose -f docker-compose.nas.yml logs               # all services
docker compose -f docker-compose.nas.yml logs -f backend    # follow backend
docker compose -f docker-compose.nas.yml logs caddy         # Caddy access + ACME logs
```

### Updating the application
```bash
cd /volume1/docker/whole-home-inventory-system
git pull origin main
docker compose -f docker-compose.nas.yml up -d --build
```

The `bootstrap.py` startup step is idempotent — it's safe to restart containers arbitrarily often.

### Managing containers
```bash
# Stop (preserves volumes and data)
docker compose -f docker-compose.nas.yml down

# Stop AND delete volumes (destroys the DB, uploads, backups — only use if you
# know what you're doing, and only after you've verified a backup zip)
docker compose -f docker-compose.nas.yml down --volumes
```

### Backup data

Persistent data lives in:

- `/volume1/docker/whole-home-inventory-system/database` — SQLite database
- `/volume1/docker/whole-home-inventory-system/uploads` — uploaded images
- `/volume1/docker/whole-home-inventory-system/backups` — zip archives created via the in-app Backups page
- `/volume1/docker/whole-home-inventory-system/certs` — backend TLS material (regenerable, not strictly backup-critical)
- `/volume1/docker/whole-home-inventory-system/caddy-data` — Caddy ACME account + Let's Encrypt certs + internal CA. Restoring is optional but saves a reissue on rebuild.

Use Synology's Hyper Backup (or `tar`/`rsync` to another volume) to snapshot these directories. The in-app backup feature produces a restorable zip that covers items + images but not users.

## Troubleshooting

### `SECRET_KEY must be set...` at container start
Your `.env` is missing or doesn't set `SECRET_KEY`. Re-run the `SECRET_KEY` generation step in One-time setup.

### `Can't locate revision identified by 'cafb3d2c47a1'`
Means the container hit Alembic directly instead of `scripts/bootstrap.py`. Check the Dockerfile CMD is intact (post-2.0.0 it runs `python scripts/bootstrap.py` before uvicorn). If you've built a custom image, ensure it inherits the updated CMD.

### Frontend can't reach the backend
1. `docker compose -f docker-compose.nas.yml ps` — both services should be `healthy`
2. `docker compose -f docker-compose.nas.yml logs backend` — look for uvicorn startup + migration output
3. `docker compose -f docker-compose.nas.yml logs caddy` — look for a `reverse_proxy` error referencing `backend:27182`. A common cause is the backend still booting — Caddy will retry once it passes its healthcheck.
4. If you've changed `NAS_ORIGINS`, ensure the value matches the exact origin the browser uses (scheme, host, port)

### `bootstrap.py` fails with "expected TLS certs at /app/certs/..."
The shared certs volume is empty. Regenerate on a workstation with mkcert installed (`cd frontend && node scripts/generate-certs.js`) and copy the `certs/` directory into `/volume1/docker/whole-home-inventory-system/certs/`.

### Let's Encrypt issuance fails
1. Confirm TCP 80 is forwarded to the NAS — ACME HTTP-01 requires it even if you only serve HTTPS.
2. Confirm `WHIS_DOMAIN` resolves to the NAS's public IP (`dig $WHIS_DOMAIN`).
3. Check `docker compose -f docker-compose.nas.yml logs caddy` for the exact ACME error. Hitting LE's rate limits usually means you need to wait or fall back to the staging directory.

### Docker permission errors
```bash
sudo synogroup --add docker $(whoami)
# log out and back in
```

### Volume permissions
```bash
sudo chown -R $(whoami):docker /volume1/docker/whole-home-inventory-system/
sudo chmod -R 755 /volume1/docker/whole-home-inventory-system/
```
