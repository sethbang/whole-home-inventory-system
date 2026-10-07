<div align="center">
  <img src="images/whis_logo_web.svg" alt="WHIS Logo" width="256" height="256">
</div>

# Whole-Home Inventory System (WHIS)

**Current version: 3.3.1** — see [CHANGELOG.md](CHANGELOG.md).

WHIS is a self-hosted platform for managing household inventories. It centralizes item information — descriptions, photos, locations, purchase details, valuations, warranties — into a local database accessible from multiple devices via a web interface. The v3.x line adds optional AI-assisted item identification (vision auto-fill) and resale-value pricing (eBay Browse + LLM), all while keeping your data local.

## Documentation

- 📖 [Architecture Overview](ARCHITECTURE.md)
- 🔧 [Development Guide](DEVELOPMENT.md)
- 🧪 [Testing Guide](TESTING.md)
- 🤝 [Contributing Guidelines](CONTRIBUTING.md)
- 📜 [API Documentation](API.md)
- 🔒 [Security Policy](SECURITY.md)
- 📦 [Deployment Guide](DEPLOYMENT.md)
- 🛒 [eBay Integration](docs/EBAY_INTEGRATION.md)
- 📋 [Changelog](CHANGELOG.md)

## Features

### Core (v1.x – v2.x)
- 📱 **Progressive Web App** — installable, offline-aware, mobile app-like experience
- 📸 **Photo management** — multiple images per item, camera capture, drag-to-reorder
- 🔍 **Full-text search** (v3.0) — fast item search via SQLite FTS5 / Postgres `tsvector`
- 🏷️ **Custom fields** — strict-typed top-level keys (`ebay`, `facebook`) plus free-form `user_defined`
- 🔒 **Privacy-first** — self-hosted, all data on your host, optional LLM-cloud kill-switch
- 📊 **Analytics & reports** — dashboard tiles, value breakdowns, charts
- 🔄 **Backup & restore** — in-app zip archives, async via ARQ when worker enabled
- 📷 **Barcode/QR scanning** — quick item lookup via `@zxing/browser`
- 🛒 **Marketplace assist** — eBay listing CSV (per-item + bulk) and Facebook Marketplace copy-paste + Meta Commerce catalog CSV

### v3.0 — Scale & ops
- 🐘 **Postgres support** — opt-in via `DATABASE_URL=postgresql+psycopg://...`; SQLite remains the zero-config default
- ⚙️ **ARQ background jobs** — Redis-backed queue for backup create/restore, thumbnail generation, vision, pricing. Synchronous fallback when `REDIS_URL` is unset
- 🖼️ **Image thumbnails** — generated server-side, served separately from full-res for fast galleries
- 🔎 **Items FTS** — sub-100ms search across name, brand, model, notes, location

### v3.1 — Intelligence (optional, off by default)
- 👁️ **Vision auto-fill** — point an image-capable LLM at a photo and pre-fill name/brand/model/tags. Strict JSON schema enforcement; per-day cost cap.
- 💰 **Pricing** — eBay Browse API for catalog comparables (P10/P50/P90), with LLM+web-search fallback for off-catalog items. Aggregated estimates cached for 14 days. Marketplace Account Deletion exempt — see [docs/EBAY_INTEGRATION.md](docs/EBAY_INTEGRATION.md).
- 🔐 **Privacy kill-switch** — `LLM_ALLOW_CLOUD=false` refuses to start unless `LLM_BASE_URL` resolves to a private host (Ollama/LocalAI on LAN).
- 💵 **Daily cost caps** — `VISION_DAILY_COST_CAP_USD` and `PRICING_DAILY_COST_CAP_USD` enforce per-(user, day) spend ceilings; over-cap returns HTTP 402.

## Screenshots

<div align="center">
  <img src="images/screenshots/WHIS - Whole-Home Inventory System.jpeg" alt="WHIS Dashboard" width="800">
  <p><em>Main Dashboard — overview of your inventory items</em></p>
  <img src="images/screenshots/WHIS - Whole-Home Inventory System · 5.08pm · 12-22.jpeg" alt="WHIS Item Details" width="800">
  <p><em>Item Details View — comprehensive information about each item</em></p>
  <img src="images/screenshots/WHIS - Whole-Home Inventory System · 5.08pm · 12-22 (1).jpeg" alt="WHIS Add Item" width="800">
  <p><em>Add Item Form — easy item entry with custom fields</em></p>
  <img src="images/screenshots/WHIS - Whole-Home Inventory System · 5.08pm · 12-22 (2).jpeg" alt="WHIS Reports" width="800">
  <p><em>Analytics Dashboard — detailed insights about your inventory</em></p>
</div>

## Tech stack

### Backend
- **Python** 3.11 / 3.12 (CI matrix)
- **FastAPI** (>=0.115)
- **SQLAlchemy 2.x**, **Pydantic v2**, **pydantic-settings**
- **SQLite** by default; **Postgres 16** opt-in via `DATABASE_URL`
- **Alembic** — sole source of truth for schema (the `Base.metadata.create_all()` path was removed in 2.0.0)
- **PyJWT** + **passlib/bcrypt** for auth
- **ARQ** + **Redis** (v3.0) — optional background job queue
- **OpenAI Python SDK** (v3.1) — talks to any OpenAI-compatible LLM (OpenRouter, Venice.ai, Ollama, LocalAI)
- **structlog**, **slowapi** (per-route rate limiting), **OpenTelemetry** (opt-in)

### Frontend
- **React 19**, **TypeScript 5**, **Vite 6**
- **Tailwind CSS v4** (`@tailwindcss/vite`, config in CSS via `@theme` block — no `tailwind.config.js`/`postcss.config.js`)
- **React Router v7** (data router with loaders)
- **TanStack Query 5**
- **react-hook-form** + **zod** (Formik + Yup were removed in v2.3)
- **Vitest** (Jest was removed in v2.4)
- **vite-plugin-pwa** for service worker / installability
- **`@zxing/browser`** for barcode scanning

### Infrastructure
- **Docker Compose** with profiles (`worker` for Redis+ARQ, `postgres` for the Postgres service)
- **Caddy** for the NAS deployment (auto-TLS, replaces the v2.3-and-prior nginx setup)

## Prerequisites

- Python 3.11 or higher
- Node.js 20 or higher
- npm
- Git
- Optional: Docker + Docker Compose for the containerized stack

## Installation (local dev)

```bash
git clone https://github.com/sethbang/whole-home-inventory-system.git
cd whole-home-inventory-system
```

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate                       # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(64))"
# paste the output into SECRET_KEY in .env

# Apply migrations. Use bootstrap.py — it reconciles legacy stamps
# from pre-2.0.0 databases automatically.
python scripts/bootstrap.py
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env   # optional — only needed if backend runs outside compose
```

### Certificates (required — app is HTTPS-only, even in dev)

WHIS speaks HTTPS everywhere — it relies on browser features (service worker, camera, clipboard) that don't work over plain HTTP outside `localhost`. There are three deployment shapes; pick whichever matches what you're doing:

| Shape | Cert source | Browser trust setup |
|---|---|---|
| **A. Dev / single host** (this section) | Local CA from `generate-certs.js`. Uses `mkcert` when present (recommended), falls back to OpenSSL otherwise. | mkcert auto-installs into the system trust store. Without mkcert: one-time CA install per device. |
| **B. Household LAN with no public domain** | Same local CA, distributed to each device. Or Caddy's internal PKI when running `docker-compose.nas.yml`. | One-time CA install per device. See [DEPLOYMENT.md](DEPLOYMENT.md). |
| **C. NAS / public-domain deployment** | **Real Let's Encrypt cert via Caddy + ACME.** | None — every device just works. **Recommended** for any household with a domain. See [DEPLOYMENT.md](DEPLOYMENT.md). |

The recommended path for shape **A** is the wrapper script — it auto-detects your LAN IP, regenerates certs only when the SAN set actually changes, writes a generated env file consumed by compose, and (on macOS) publishes `whis.local` via Bonjour so any device on your LAN can use the same URL:

```bash
# Strongly recommended: install mkcert first. Without it the script
# falls back to OpenSSL and the host browser will need a manual trust
# step, plus Firefox won't trust the cert at all (it has its own store).
brew install mkcert nss      # macOS — Linux: see https://github.com/FiloSottile/mkcert#installation

./bin/whis certs             # generate certs only
# — or —
./bin/whis up                # generate certs + bring the dev stack up
```

This produces:
- `frontend/certs/cert.pem` + `key.pem` — server cert (SANs cover `localhost`, `whis.local`, the auto-detected LAN IP, and your Mac's `<computer-name>.local`)
- `frontend/certs/whis-dev-ca.crt` — root CA you install on each *additional* device
- `frontend/certs/CERTIFICATE-SETUP.md` — per-OS install instructions for the additional-device step
- `.env.generated` at the repo root — auto-generated; consumed by compose, ignored by git

When mkcert is on PATH, the script runs `mkcert -install` for you — the host running the script trusts the CA automatically (system store + Firefox/NSS). For other devices on your network, copy `whis-dev-ca.crt` over and follow the steps in `CERTIFICATE-SETUP.md`. From any of those devices, browse to `https://whis.local:5173` (mDNS) — or use the LAN-IP fallback URL the wrapper prints if `whis.local` doesn't resolve on that device.

If mkcert is not available the script falls back to OpenSSL. The host then needs the same per-device install as everyone else (the setup doc carries the exact command for each OS).

Power users can still call `cd frontend && node scripts/generate-certs.js` directly — it works the same way; the wrapper just adds the LAN-IP detection and mDNS publishing on top.

### Run the dev servers

```bash
# Backend (HTTPS on 27182)
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --port 27182 \
  --ssl-keyfile ../frontend/certs/key.pem \
  --ssl-certfile ../frontend/certs/cert.pem

# Frontend (HTTPS on 5173, proxies /api + /uploads). Cert generation
# now lives in `bin/whis certs` — `npm run dev` just starts vite and
# expects the certs from a prior `bin/whis certs` run to be on disk.
cd frontend
npm run dev
```

App is at https://localhost:5173 (LAN: https://whis.local:5173, or the LAN-IP URL `bin/whis` prints).

## Docker (recommended for testing the full stack)

The default `docker-compose.yml` is **deployment shape A** — your laptop running the whole stack locally for evaluation. It bind-mounts `frontend/certs/` into the frontend container so the certs from `bin/whis certs` are reused (the in-container path is now a no-op — the host wrapper is the sole sanctioned cert-gen entry point, since `os.networkInterfaces()` inside a container can't see your real LAN IP).

```bash
# At the repo root — generate a SECRET_KEY once.
cat > .env <<EOF
SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(64))')
EOF
grep -q '^\.env$' .gitignore || echo '.env' >> .gitignore

# One-command happy path. Auto-detects your LAN IP, regenerates certs
# (skipped on subsequent runs unless the SAN set drifts), publishes
# `whis.local` via mDNS (Bonjour on Mac, avahi sidecar on Linux), and
# brings up backend + frontend + SQLite.
./bin/whis up

# Other profiles still pass through cleanly — bin/whis just shells out
# to docker compose, so any flag you'd pass there works:
./bin/whis up --profile worker            # + Redis + ARQ worker
./bin/whis up --profile postgres          # + Postgres 16
./bin/whis up --profile postgres --profile worker   # full v3.0 stack

# `make up` is an alias if you prefer make:
make up
```

Browse to `https://whis.local:5173` from any device on your LAN. If `whis.local` doesn't resolve on a particular device, fall back to the LAN-IP URL the wrapper prints on startup. Both URLs are covered by the same cert SAN.

If you'd rather skip the wrapper, plain `docker compose up` still works — `CORS_ORIGINS` falls back to `https://localhost:5173`, but you'll lose the LAN-IP entry and mDNS publishing. The wrapper is purely additive.

The backend container's startup script (`scripts/bootstrap.py`) runs `alembic upgrade head` on every boot and reconciles legacy migration stamps from pre-2.0.0 databases.

### Production / NAS deployment (shapes B and C)

For anything you want a household to actually use day-to-day — a NAS, a homelab box, a small server — see [DEPLOYMENT.md](DEPLOYMENT.md). The NAS compose file (`docker-compose.nas.yml`) puts Caddy on 80/443 and supports two TLS modes:

- **Shape C — public domain (recommended):** set `WHIS_DOMAIN=whis.example.com` + `CADDY_ACME_EMAIL=…` and point DNS at your public IP. Caddy auto-issues a real Let's Encrypt cert; **no client-side trust setup, ever.**
- **Shape B — LAN-only:** when `WHIS_DOMAIN` doesn't resolve publicly (e.g. the `whis.local` default), Caddy falls back to its internal CA. The root cert lives at `/data/caddy/pki/authorities/local/root.crt` inside the container; install it once per device — same UX as the per-device step in shape A, but the CA lives on the server.

## Quick start

1. **First-time setup**
   - Open https://localhost:5173 → Register an account → log in.
2. **Adding items**
   - Click **Add Item**. Optionally upload/take a photo and click **Auto-fill from image** (requires vision feature flagged on).
   - Fill remaining fields, save.
3. **Pricing an item** (optional, requires `PRICING_ENABLED=true`)
   - Open the item → **Get price estimate**. Falls through providers per `PRICING_PROVIDERS` (default `ebay,llm`).
4. **Marketplace export**
   - Open an item → **Marketplace** tab → eBay (CSV) or Facebook (copy-paste + Meta Commerce CSV). Bulk variants live on the Dashboard.
5. **Backups**
   - Backups page → **Create backup**. Download / restore from the same page.

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for development workflow, style guidelines, testing requirements, and PR process.

## Support

- 🐛 [Issue Tracker](https://github.com/sethbang/whole-home-inventory-system/issues)
- 💬 [Discussions](https://github.com/sethbang/whole-home-inventory-system/discussions)

## License

MIT — see [LICENSE](LICENSE).

## Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) — backend framework
- [React](https://react.dev/) — UI library
- [Tailwind CSS](https://tailwindcss.com/) — styling
- [Vite](https://vite.dev/) — frontend build tool
- [ARQ](https://arq-docs.helpmanual.io/) — background job queue
- [OpenRouter](https://openrouter.ai/) — primary LLM gateway used in v3.1
