# WHIS Development Guide

This guide provides detailed information for developers working on WHIS (Whole-Home Inventory System), currently at v3.1.0.

## Table of Contents

1. [Development Environment Setup](#development-environment-setup)
2. [Project Structure](#project-structure)
3. [Development Workflow](#development-workflow)
4. [Code Style and Standards](#code-style-and-standards)
5. [Testing](#testing)
6. [Debugging](#debugging)
7. [Performance Optimization](#performance-optimization)
8. [Common Development Tasks](#common-development-tasks)

## Development Environment Setup

### Prerequisites

- Python 3.11 or 3.12 (CI matrix runs both)
- Node.js 20+ (CI uses 20)
- Git
- VS Code (recommended)
- Docker + Docker Compose for the full-stack workflow

### VS Code Extensions

- Python, Pylance
- ESLint, Prettier
- Tailwind CSS IntelliSense
- Docker
- SQLite Viewer

### Environment setup steps

```bash
# Clone
git clone https://github.com/sethbang/whole-home-inventory-system
cd whole-home-inventory-system

# Backend venv + deps
cd backend
python -m venv venv
source venv/bin/activate                       # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Frontend deps
cd ../frontend
npm install

# Dev TLS certs (app is HTTPS-only, even in dev)
node scripts/generate-certs.js
# Install certs/whis-dev-ca.crt per OS — see frontend/certs/CERTIFICATE-SETUP.md
```

### Backend env config

```bash
cd ../backend
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(64))"
# Paste the output into SECRET_KEY in .env.

# For real auth flow, leave BYPASS_AUTH=false (default).
# For one-off UI exploration, set BYPASS_AUTH=true — settings fail-fast
# is skipped in that mode.
```

### Database setup

```bash
# bootstrap.py reconciles legacy stamps from pre-2.0.0 databases and
# is idempotent — safe to re-run.
python scripts/bootstrap.py

# Optional dev seed (only needed when BYPASS_AUTH=false):
python create_dev_user.py
```

### Optional v3.1 LLM/eBay env

If you'll exercise the vision auto-fill or pricing features locally, add to `backend/.env`:

```bash
LLM_BASE_URL=https://openrouter.ai/api/v1   # or http://ollama:11434/v1
LLM_API_KEY=sk-...
LLM_MODEL=google/gemini-2.5-flash
# Optional model-per-feature overrides:
LLM_VISION_MODEL=google/gemini-3-flash-preview
LLM_PRICING_MODEL=anthropic/claude-sonnet-4.6
VISION_ENABLED=true
PRICING_ENABLED=true
VISION_DAILY_COST_CAP_USD=5.0
PRICING_DAILY_COST_CAP_USD=10.0
# eBay Browse API (optional but the priority pricing provider):
EBAY_APP_ID=YourCo-yourapp-PRD-...
EBAY_CERT_ID=PRD-...
```

The settings module fail-fasts: if `VISION_ENABLED=true` without `LLM_BASE_URL`, the app refuses to start. Same for `LLM_ALLOW_CLOUD=false` against a public LLM host.

### IDE configuration

VS Code `settings.json`:
```json
{
  "python.linting.enabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  },
  "typescript.preferences.importModuleSpecifier": "relative"
}
```

## Project Structure

### Backend (`backend/app/`)

```
backend/
├── alembic/versions/        # Migrations stack: 20260420_0001 (baseline)
│                            #   → v2.2 pricing prewire
│                            #   → v3.0 Postgres compat / FTS / thumbnails
│                            #   → v3.1 LLM usage / pricing cache composite PK
│                            #   → v3.1+ item_images cascade
├── app/
│   ├── main.py              # FastAPI factory, middleware, exception handlers,
│   │                        # /uploads static mount, router registration with
│   │                        # /api prefix (routers themselves carry no prefix)
│   ├── settings.py          # pydantic-settings singleton, fail-fast guards
│   │                        # (SECRET_KEY, LLM_*, LLM_ALLOW_CLOUD)
│   ├── models.py            # SQLAlchemy: User, Item, ItemImage, Backup,
│   │                        # PriceCache, LLMUsage; custom UUID TypeDecorator
│   ├── schemas.py           # Pydantic v2 (ConfigDict). Use model_dump()
│   ├── schemas_llm.py       # Strict json_schema for VisionSuggestion +
│   │                        # PriceEstimate; PROMPT_VERSION
│   ├── database.py          # Engine + SessionLocal; reads DATABASE_URL
│   ├── security.py          # PyJWT auth (python-jose was removed in 2.0.0)
│   ├── fts.py               # Items full-text search (SQLite FTS5 / PG tsvector)
│   ├── routers/             # Thin handlers — delegate to services/
│   │   ├── auth.py
│   │   ├── items.py
│   │   ├── images.py
│   │   ├── analytics.py
│   │   ├── backups.py
│   │   ├── ebay.py          # CSV listing assist
│   │   ├── facebook.py      # Copy-paste + Meta Commerce CSV
│   │   ├── jobs.py          # v3.0 ARQ job status
│   │   ├── vision.py        # v3.1 image identification
│   │   └── pricing.py       # v3.1 resale-value estimation
│   ├── services/            # Domain logic with ownership checks
│   │   ├── items.py
│   │   ├── backups.py
│   │   └── images.py
│   ├── jobs/                # v3.0 ARQ scaffold
│   │   ├── client.py        # Pool factory, sync fallback when REDIS_URL unset
│   │   ├── worker.py        # WorkerSettings export
│   │   └── tasks/           # backups, images, vision, pricing
│   ├── llm/                 # v3.1 shared LLM layer
│   │   ├── openai_compatible.py   # Sole HTTP client; supports OR web_search
│   │   ├── prompts.py             # Versioned system prompts
│   │   └── budget.py              # Daily cost-cap guard
│   ├── vision/              # v3.1 image -> structured suggestion
│   ├── pricing/             # v3.1 estimate orchestration
│   │   ├── service.py
│   │   ├── normalizer.py
│   │   ├── cache.py
│   │   ├── aggregate.py     # P10/P50/P90 (or min/median/max for N<5)
│   │   ├── provider_base.py
│   │   ├── provider_ebay_browse.py
│   │   └── provider_llm.py
│   ├── ebay/                # CSV formatter + category mapping
│   ├── facebook/            # Copy-paste + Meta Commerce CSV
│   └── middleware/          # Rate limiting, request-ID, structured logging
├── scripts/
│   └── bootstrap.py         # Runtime migration + legacy-stamp reconciliation
├── tests/                   # pytest suite, in-memory SQLite by default,
│                            # honors TEST_DATABASE_URL for the Postgres matrix
├── .env.example
└── requirements.txt
```

### Frontend (`frontend/src/`)

```
frontend/
├── src/
│   ├── App.tsx              # createBrowserRouter + RouterProvider
│   ├── queryClient.ts       # React Query 5 client (retries=1, no focus refetch)
│   ├── api/
│   │   ├── client.ts        # axios instance + ApiError class
│   │   ├── items.ts, images.ts, analytics.ts, backups.ts,
│   │   ├── auth.ts, ebay.ts, facebook.ts, jobs.ts (v3.0)
│   │   ├── queryKeys.ts     # Hierarchical query-key factory
│   │   ├── openapi.d.ts     # Generated by `npm run codegen:api`
│   │   └── types.ts         # Re-exports from openapi.d.ts + hand-written
│   │                        # types for endpoints not yet typed in the schema
│   ├── components/          # Layout, BarcodeScanner (lazy), CameraCapture,
│   │                        # CustomFields, EbayFields, FacebookFields,
│   │                        # FacebookCopyPasteDialog, ImageGallery,
│   │                        # ErrorBoundary
│   ├── contexts/            # AuthContext + DevModeContext (split provider/hook)
│   ├── pages/               # Dashboard, AddItem, ItemDetail, Reports, Backups,
│   │                        # Login, Register — each with a colocated
│   │                        # <Name>.schema.ts (zod)
│   ├── router/loaders.ts    # React Router data-router loaders that
│   │                        # ensureQueryData() warm the React Query cache
│   ├── index.css            # Tailwind v4 @theme block (semantic tokens)
│   └── setupTests.ts        # Vitest setup
├── scripts/generate-certs.js
├── vitest.config.ts
├── vite.config.ts
└── package.json
```

## Development Workflow

### Starting dev servers

```bash
# Backend (HTTPS on 27182)
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --port 27182 \
  --ssl-keyfile ../frontend/certs/key.pem \
  --ssl-certfile ../frontend/certs/cert.pem
```

```bash
# Frontend (HTTPS on 5173, regenerates certs on start, proxies /api + /uploads)
cd frontend
npm run dev
```

### Docker compose profiles

```bash
# Default — backend + frontend + SQLite, jobs run synchronously in-request.
docker compose up --build

# + Redis + ARQ worker — heavy ops (backup, vision, pricing) go async.
docker compose --profile worker up --build

# + Postgres 16.
docker compose --profile postgres up --build

# Full v3.0 stack: Postgres + Redis + worker.
docker compose --profile postgres --profile worker up --build

# NAS deployment (Caddy auto-TLS; Redis + worker always on).
docker compose -f docker-compose.nas.yml up -d
```

Both compose files require `SECRET_KEY` in the shell env or in a sibling `.env`. Generate one with `python -c "import secrets; print(secrets.token_urlsafe(64))"`.

### Database migrations

```bash
cd backend

# Create a new revision skeleton
alembic revision -m "description_of_changes"

# Apply migrations (preferred — handles legacy stamps + idempotent)
python scripts/bootstrap.py
# Or, on known-clean DBs:
alembic upgrade head

# Revert last migration
alembic downgrade -1
```

When a migration needs different DDL on Postgres vs SQLite, branch on `op.get_bind().dialect.name`. See `20260423_0008_item_images_cascade.py` for an example. `Base.metadata.create_all()` is no longer called at startup — Alembic is the sole source of truth for schema.

### TypeScript API types — codegen

The frontend type definitions for backend resources are **generated** from the live FastAPI OpenAPI schema:

```bash
cd frontend
npm run codegen:api    # writes frontend/src/api/openapi.d.ts
```

After any backend schema change (new field, renamed endpoint, etc.):

1. Run `npm run codegen:api` to regenerate.
2. Commit the regenerated `openapi.d.ts` alongside the backend change.

CI's `contract-check` job re-runs codegen and fails the build if the committed file is out of sync. Don't hand-edit `openapi.d.ts` — add hand-written types to `frontend/src/api/types.ts` only for resources the backend doesn't yet emit (notably analytics responses, which are still plain dicts).

## Code Style and Standards

### Python style guide

- PEP 8 with **Black** (88-col line length)
- Type hints everywhere
- `isort` for imports
- Docstrings on public functions/classes
- Use the `logging` module — no `print()` in server code
- Use **`model_dump()`**, not `dict()` (Pydantic v2)

```python
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import models, schemas


def create_item(
    db: Session,
    item: schemas.ItemCreate,
    user_id: str,
) -> models.Item:
    """Create a new inventory item owned by user_id."""
    db_item = models.Item(**item.model_dump(), owner_id=user_id)
    db.add(db_item)
    try:
        db.commit()
        db.refresh(db_item)
        return db_item
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
```

In practice, route handlers should be thin and delegate to a service in `app/services/` (e.g. `ItemService.create(...)`) which owns ownership checks and business logic.

### TypeScript / React style guide

- Functional components only
- TypeScript types/interfaces for all props
- Follow the ESLint flat config (`eslint.config.js`) — CI lint is **blocking**
- 80-col line length
- Prefer relative imports
- React Hooks rules (eslint-plugin-react-hooks enforces at lint time)

```tsx
import { useQuery } from '@tanstack/react-query';

import { itemsApi } from '../api/items';
import { queryKeys } from '../api/queryKeys';
import type { Item } from '../api/types';

interface ItemListProps {
  category?: string;
  onItemSelect: (item: Item) => void;
}

export function ItemList({ category, onItemSelect }: ItemListProps) {
  const { data: items = [] } = useQuery({
    queryKey: queryKeys.items.list({ category }),
    queryFn: () => itemsApi.list({ category }),
  });

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {items.map((item) => (
        <button
          key={item.id}
          onClick={() => onItemSelect(item)}
          className="p-4 border rounded hover:shadow-lg text-left"
        >
          <h3 className="text-lg font-semibold">{item.name}</h3>
          <p className="text-gray-600">{item.category}</p>
        </button>
      ))}
    </div>
  );
}
```

## Testing

### Backend testing

```bash
cd backend
source venv/bin/activate

pytest                                              # ~50s, in-memory SQLite
pytest --cov=app tests/                             # with coverage
pytest tests/test_items.py::test_item_crud_round_trip   # single test

# Run against Postgres (the CI matrix subset that doesn't depend on
# provider mocks):
TEST_DATABASE_URL=postgresql+psycopg://whis:whis@localhost:5432/whis pytest
```

Conftest provides `client`, `user`, `db_session`, `auth_headers`. Fixtures honor `TEST_DATABASE_URL`; they default to in-memory SQLite + `StaticPool`.

```python
# Example test (uses fixtures from conftest)
def test_item_crud_round_trip(client, auth_headers):
    # Create
    r = client.post("/api/items/",
                    json={"name": "Test Item", "category": "Test"},
                    headers=auth_headers)
    assert r.status_code == 200
    item_id = r.json()["id"]

    # Read
    r = client.get(f"/api/items/{item_id}", headers=auth_headers)
    assert r.json()["name"] == "Test Item"
```

### Frontend testing

```bash
cd frontend
npm test                                          # vitest run
npm run test:watch                                # watch mode
npm test -- src/components/__tests__/Layout.test.tsx   # single file
```

Test files live under `src/**/__tests__/**/*.test.{ts,tsx,js,jsx}`. Vitest config is `vitest.config.ts` (jsdom env, globals enabled, setup file at `src/setupTests.ts`).

```tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';

import { ItemList } from '../ItemList';

describe('ItemList', () => {
  it('renders items correctly', () => {
    const onItemSelect = vi.fn();
    const items = [{ id: '1', name: 'Test Item', category: 'Test' }];
    render(<ItemList items={items} onItemSelect={onItemSelect} />);
    expect(screen.getByText('Test Item')).toBeInTheDocument();
  });
});
```

### CI matrix

GitHub Actions (`.github/workflows/ci.yml`) runs:

- **`backend`** — pytest on Python 3.11 + 3.12 × SQLite + Postgres 16 (4 legs). Postgres runs as a service container per leg.
- **`pip-audit`** — `--strict` on the Python deps; gated to the 3.12/SQLite leg.
- **`frontend`** — ESLint (**blocking**, 0 errors), Vitest, `npm audit --omit=dev --audit-level=high`.
- **`image-scan`** — builds backend + Caddy images with buildx + GHA cache, scans both with Trivy. HIGH/CRITICAL fail (ignore-unfixed).
- **`contract-check`** — regenerates `frontend/src/api/openapi.d.ts` from a live backend and fails if the committed file is out of sync.

### End-to-end testing

Not currently in-tree. Playwright is the planned vehicle when E2E lands.

## Debugging

### Backend debugging

VS Code launch configuration:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": ["app.main:app", "--reload", "--port", "27182"],
      "jinja": true,
      "justMyCode": true
    }
  ]
}
```

Logging is via `structlog` with a JSON renderer in production (`LOG_FORMAT=json`) and console in dev (`LOG_FORMAT=console` or `DEBUG=true`). For temporary diagnostic prints, use the `logging` module — `logger.debug(...)` is preferred over `print()`.

### Async-job debugging

When the worker profile is up:

```bash
docker compose --profile worker logs -f whis-worker
# Tail jobs as they execute. Each task wraps return values in an envelope
# (see backend/app/jobs/tasks/) so failures serialize cleanly back to the
# /api/jobs/{id} endpoint.
```

### Frontend debugging

- React Developer Tools (Chrome/Firefox extension) — Components + Profiler tabs
- React Query Devtools (auto-mounted in dev only)
- Vite's overlay surfaces compile errors directly in the browser

## Performance Optimization

### Backend
- Index appropriately; consult `models.py` for current `index=True` columns.
- The v3.0 FTS path replaces ad-hoc `LIKE` queries — use `app.fts` for any new search surface.
- Long-running operations (backup create/restore, vision, pricing) belong on the ARQ worker — see `app/jobs/tasks/`.
- LLM cost is the largest variable cost; respect `VISION_DAILY_COST_CAP_USD` and `PRICING_DAILY_COST_CAP_USD`.

### Frontend
- React Query caches by hierarchical key — see `api/queryKeys.ts`.
- Lazy-load heavy components (`BarcodeScanner` already does this).
- `vite-plugin-pwa` handles SW caching; runtime caching is a function matcher in `vite.config.ts`.
- The bundled images path uses thumbnails (v3.0) — prefer `<ItemImage thumbnail>` over full-res in lists.

## Common Development Tasks

### Adding a new model field

1. Update `app/models.py` and `app/schemas.py`.
2. `alembic revision -m "add_<field>"` and write the migration.
3. Update the relevant router/service in `app/`.
4. Run `cd frontend && npm run codegen:api` to refresh `openapi.d.ts`.
5. Update frontend types/components that need the new field.
6. Add tests on both sides.

### Adding a new router

1. Create `app/routers/<resource>.py` with `router = APIRouter(tags=["..."])`. Don't add a `/api` prefix — `main.py` adds it.
2. Register the router in `main.py` via `app.include_router(<resource>.router, prefix="/api")`.
3. Add per-route rate-limit decorators if the route is auth/cost-sensitive (see `routers/auth.py` for the slowapi pattern).
4. Add tests.
5. Regenerate `openapi.d.ts` via `npm run codegen:api`.

### Updating dependencies

```bash
# Backend
cd backend && source venv/bin/activate
pip list --outdated
pip install --upgrade <package>
pip freeze | grep '^<package>=' >> requirements.txt   # or update the pin manually

# Frontend
cd frontend
npm outdated
npm update                     # or `npm install <package>@latest`
```

CI's `pip-audit --strict` and `npm audit --audit-level=high` will block known-vulnerable versions.

### Building for production

```bash
# Backend image build is identical to dev — Dockerfile handles it.
# Frontend production build:
cd frontend
npm run build                  # tsc --noEmit + vite build → dist/

# Full prod stack:
docker compose -f docker-compose.nas.yml up -d --build
```

## Additional resources

- [FastAPI](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.x](https://docs.sqlalchemy.org/)
- [Alembic](https://alembic.sqlalchemy.org/)
- [Pydantic v2](https://docs.pydantic.dev/latest/)
- [React](https://react.dev/)
- [React Router v7 data router](https://reactrouter.com/)
- [TanStack Query v5](https://tanstack.com/query/latest)
- [Tailwind CSS v4](https://tailwindcss.com/)
- [Vitest](https://vitest.dev/)
- [ARQ](https://arq-docs.helpmanual.io/)
- [OpenRouter](https://openrouter.ai/)
