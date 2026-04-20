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
mkdir -p /volume1/docker/whole-home-inventory-system/database
mkdir -p /volume1/docker/whole-home-inventory-system/uploads
mkdir -p /volume1/docker/whole-home-inventory-system/backups
```

The volume mount paths in `docker-compose.nas.yml` expect this layout.

### 3. Generate a `SECRET_KEY`

```bash
cat > .env <<EOF
SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(64))')
EOF
chmod 600 .env
```

Optional env vars you can set in the same `.env`:

- `NAS_ORIGINS` — override the default CORS origins (e.g. `https://whis.mydomain.example`) when fronting the stack with a reverse proxy on a different hostname
- `LOG_LEVEL` — defaults to `INFO`; set to `DEBUG` temporarily for troubleshooting
- `ACCESS_TOKEN_EXPIRE_MINUTES` — defaults to 30

The compose file refuses to start without `SECRET_KEY`; this is intentional (prevents shipping a placeholder secret in production).

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

- Backend health: `curl -k https://192.168.1.122:27182/api/health` → `{"status":"healthy","version":"2.0.0"}`
- Frontend: open `http://<nas-ip>:5173` in a browser. If you've added a reverse proxy, use the external hostname instead.

## HTTPS and external exposure

The frontend container's nginx listens on plain HTTP port 80 (mapped to host 5173). That's fine for LAN-only use. For external exposure you should:

1. Terminate TLS at Synology DSM's **Login Portal → Advanced → Reverse Proxy** (or Caddy/Traefik), pointing the external hostname at `http://<nas-ip>:5173`.
2. Set `NAS_ORIGINS=https://your-domain.example` in `.env` so the backend's CORS whitelist includes the external origin.
3. Consider adding rate limiting at the proxy layer — the application does not enforce it.

## Maintenance

### Viewing logs
```bash
docker compose -f docker-compose.nas.yml logs               # all services
docker compose -f docker-compose.nas.yml logs -f backend    # follow backend
docker compose -f docker-compose.nas.yml logs frontend      # frontend only
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

Use Synology's Hyper Backup (or `tar`/`rsync` to another volume) to snapshot these directories. The in-app backup feature produces a restorable zip that covers items + images but not users.

## Troubleshooting

### `SECRET_KEY must be set...` at container start
Your `.env` is missing or doesn't set `SECRET_KEY`. Re-run the `SECRET_KEY` generation step in One-time setup.

### `Can't locate revision identified by 'cafb3d2c47a1'`
Means the container hit Alembic directly instead of `scripts/bootstrap.py`. Check the Dockerfile CMD is intact (post-2.0.0 it runs `python scripts/bootstrap.py` before uvicorn). If you've built a custom image, ensure it inherits the updated CMD.

### Frontend can't reach the backend
1. `docker compose -f docker-compose.nas.yml ps` — both services should be `running`
2. `docker compose -f docker-compose.nas.yml logs backend` — look for uvicorn startup + migration output
3. If you've changed `NAS_ORIGINS`, ensure the value matches the exact origin the browser uses (scheme, host, port)

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
