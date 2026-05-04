# WHIS Testing Guide

This document describes the testing strategy, current test surface, and conventions for WHIS (Whole-Home Inventory System). Current as of v3.1.0.

## Current state

- **Backend:** 336 pytest tests (335 at v3.1.0 release + 1 deletion-exemption regression). Default run uses in-memory SQLite via `conftest.py`. Postgres 16 matrix is opt-in via `TEST_DATABASE_URL`.
- **Frontend:** 95 vitest tests across components, API client modules, contexts, and pages.
- **CI:** GitHub Actions at `.github/workflows/ci.yml`. 4-leg backend matrix (Python 3.11/3.12 × SQLite/Postgres). Frontend ESLint is **blocking** (0 errors). Three additional gates: `pip-audit --strict`, `npm audit --omit=dev --audit-level=high`, Trivy image scan (HIGH/CRITICAL fail), and a `contract-check` job that re-runs `npm run codegen:api` and fails if `frontend/src/api/openapi.d.ts` is out of sync.
- **Not yet present:** Playwright / E2E browser tests, Locust load tests, formal coverage gates. Coverage is reported in the job log but not failed-under.

## Table of Contents

1. [Testing Overview](#testing-overview)
2. [Test Environment Setup](#test-environment-setup)
3. [Backend Testing](#backend-testing)
4. [Frontend Testing](#frontend-testing)
5. [Compliance / Regression Tests](#compliance--regression-tests)
6. [End-to-End Testing](#end-to-end-testing)
7. [Performance Testing](#performance-testing)
8. [Security Testing](#security-testing)
9. [Continuous Integration](#continuous-integration)
10. [Best Practices](#best-practices)

## Testing Overview

### Testing pyramid

WHIS follows the testing pyramid:
- Many unit tests (fast, isolated)
- Fewer integration tests (slower, real DB / mocked HTTP)
- Few/no end-to-end tests (Playwright not yet wired up)

### Coverage targets (aspirational, not enforced)

- Backend: 80%+
- Frontend: 70%+
- Critical paths (auth, deletion-exemption, restore round-trip, settings fail-fast): 100%

## Test Environment Setup

### Backend

```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
```

Test deps (`pytest`, `pytest-cov`, `httpx`) are pinned in `requirements.txt` already. No separate `requirements-test.txt`.

Run the suite:

```bash
pytest                                              # ~50s, in-memory SQLite
pytest --cov=app tests/                             # with coverage
pytest tests/test_items.py::test_item_crud_round_trip   # single test
pytest -v                                           # verbose
pytest -k "pricing"                                 # filter by name
```

Run against Postgres (the CI matrix subset that doesn't depend on provider mocks):

```bash
TEST_DATABASE_URL=postgresql+psycopg://whis:whis@localhost:5432/whis pytest
```

### How the fixtures work

`backend/tests/conftest.py` sets `BYPASS_AUTH=false` and a deterministic `SECRET_KEY` at import time, wires the app to either an in-memory SQLite engine (default, `StaticPool`) or the database at `TEST_DATABASE_URL`, applies the schema (Alembic head for Postgres; create_all for in-memory speed), and exposes:

- `client` — FastAPI `TestClient` with `get_db` dependency override
- `db_session` — direct SQLAlchemy session for assertions
- `user` — a real DB user with a hashed password
- `auth_headers` — `Authorization: Bearer <real JWT>` header dict

Some specialty fixtures live alongside specific test files (e.g. `patch_task_session` in `test_job_tasks.py` for the ARQ task wrappers).

### Frontend

```bash
cd frontend
npm install
```

Run the suite:

```bash
npm test                                          # vitest run, ~6s
npm run test:watch                                # watch mode
npm test -- src/components/__tests__/Layout.test.tsx   # single file
```

Vitest config is `vitest.config.ts` (jsdom env, globals enabled, setup file at `src/setupTests.ts`, matches `src/**/__tests__/**/*.test.{ts,tsx,js,jsx}`).

## Backend Testing

### Unit / API tests

```python
# tests/test_items.py
def test_item_crud_round_trip(client, auth_headers):
    # Create
    r = client.post(
        "/api/items/",
        json={"name": "Test Item", "category": "Test"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    item_id = r.json()["id"]

    # Read
    r = client.get(f"/api/items/{item_id}", headers=auth_headers)
    assert r.json()["name"] == "Test Item"

    # Update
    r = client.put(
        f"/api/items/{item_id}",
        json={"name": "Renamed"},
        headers=auth_headers,
    )
    assert r.json()["name"] == "Renamed"

    # Delete
    r = client.delete(f"/api/items/{item_id}", headers=auth_headers)
    assert r.status_code == 204
```

### Service-layer tests

Routers delegate to services in `app/services/`. Service tests usually take `db_session` + `user` and exercise the service directly:

```python
# tests/test_item_service.py
from app.services.items import ItemService

def test_delete_item_removes_image_files(db_session, user, tmp_path):
    svc = ItemService(db_session, user)
    item = svc.create({"name": "x", "category": "y"})
    # ... attach an image file written to tmp_path
    svc.delete(item.id)
    # Assert the image file is gone from disk (F6 regression)
```

### LLM / pricing / vision tests

These are mock-heavy and SQLite-only. Provider tests use `httpx.MockTransport`:

```python
# tests/test_pricing_providers.py
def test_ebay_lookup_happy_path():
    transport = _mock_transport({
        "/identity/v1/oauth2/token": _oauth_ok(),
        "/buy/browse/v1/item_summary/search": httpx.Response(200, json={...}),
    })
    # ...assert P10/P50/P90 + sample_count
```

Vision/pricing service tests use a fake `OpenAICompatibleClient`:

```python
# tests/test_vision_service.py
def _fake_client(payload, ...):
    client = MagicMock()
    client.vision_completion = AsyncMock(return_value={"data": payload, ...})
    return client
```

## Frontend Testing

### Component tests

```tsx
// src/components/__tests__/ItemList.test.tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ItemList } from '../ItemList';

describe('ItemList', () => {
  it('renders items correctly', () => {
    const items = [{ id: '1', name: 'Test Item', category: 'Test' }];
    render(<ItemList items={items} onItemSelect={() => {}} />);
    expect(screen.getByText('Test Item')).toBeInTheDocument();
  });
});
```

### User interaction

```tsx
// src/components/__tests__/AddItem.test.tsx
import { describe, test, expect, vi } from 'vitest';
import { render, fireEvent } from '@testing-library/react';
import { AddItem } from '../AddItem';

test('form submission', async () => {
  const onSubmit = vi.fn();
  const { getByLabelText, getByText } = render(<AddItem onSubmit={onSubmit} />);
  fireEvent.change(getByLabelText('Name'), { target: { value: 'Test Item' } });
  fireEvent.click(getByText('Submit'));
  expect(onSubmit).toHaveBeenCalled();
});
```

### React Query / context-aware tests

Wrap with the same providers the app uses (`QueryClientProvider`, `AuthProvider`). The `setupTests.ts` file installs `@testing-library/jest-dom` matchers (still works under vitest via the `@testing-library/jest-dom/vitest` import).

```tsx
import { QueryClientProvider, QueryClient } from '@tanstack/react-query';

function renderWithProviders(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}
```

### API client tests

API client modules in `src/api/` are tested with `msw` or direct mocking of the axios instance. See `src/api/__tests__/items.test.ts` for the canonical pattern.

## Compliance / Regression Tests

A small set of tests is "load-bearing" — failures imply broken commitments to external systems or compliance regimes. Treat them as critical-path:

- **`test_pricing_providers.py::test_ebay_parser_drops_seller_pii_for_deletion_exemption`** — guards the eBay Marketplace Account Deletion exemption. If it fails, WHIS is no longer exempt and the deletion-notification callback must be implemented before shipping. See `docs/EBAY_INTEGRATION.md`.
- **`test_settings.py::test_*_refuses_to_load_with_*`** — fail-fast guards on `SECRET_KEY`, `BYPASS_AUTH=false` + missing key, `LLM_ALLOW_CLOUD=false` against a public host, `VISION_ENABLED=true` without `LLM_BASE_URL`, etc.
- **`test_backups.py::test_backup_create_and_restore_round_trip_with_images`** — guards the restore path that briefly shipped 670-byte image-less backups in pre-3.1.1 dev versions. Writes a real JPEG, backs up, restores, asserts byte-identical content.
- **Cascade test** — guards Postgres FK enforcement: `item_images.item_id ON DELETE CASCADE` is required because the bulk-delete path (`synchronize_session=False`) bypasses ORM cascade.

## End-to-End Testing

Not currently in-tree. Playwright is the planned vehicle. When E2E lands, expected layout:

```text
e2e/
├── playwright.config.ts
├── itemFlow.spec.ts
├── auth.spec.ts
└── pricing.spec.ts
```

Until then, the [UAT_v3.1.md](UAT_v3.1.md) checklist serves as the manual E2E coverage matrix.

## Performance Testing

Not formally automated. Spot-check approaches in use:

- **FTS smoke**: `tests/test_items_fts.py` exercises the v3.0 FTS path on both SQLite and Postgres dialects.
- **LLM cost ceilings**: budget guard tests assert HTTP 402 at cap.
- **Manual load profiling** via locust or k6 is operator territory.

## Security Testing

### Authentication

```python
# tests/test_auth.py
def test_invalid_token(client):
    r = client.get(
        "/api/items/",
        headers={"Authorization": "Bearer not-a-real-token"},
    )
    assert r.status_code == 401

def test_password_hashing():
    from app.security import hash_password, verify_password
    hashed = hash_password("test_password")
    assert verify_password("test_password", hashed)
```

### Settings fail-fast

`tests/test_settings.py` covers refusal to start with placeholder/missing `SECRET_KEY`, `LLM_ALLOW_CLOUD=false` against public LLM hosts, vision/pricing flagged on without LLM config, etc. Add a fail-fast test alongside any new setting that should refuse mis-configurations.

### Supply chain

CI gates: `pip-audit --strict` blocks known-vulnerable Python deps (3.12/SQLite leg). `npm audit --omit=dev --audit-level=high` blocks frontend deps. Trivy scans the backend + Caddy images for HIGH/CRITICAL CVEs. All three are blocking.

## Continuous Integration

`.github/workflows/ci.yml` runs on push/PR to `main`:

| Job | What it runs | Blocking? |
|---|---|---|
| `backend` | pytest matrix: Python 3.11 + 3.12 × SQLite + Postgres 16. Postgres-as-service per leg. Full suite on SQLite legs; LLM-mocking subset on Postgres legs. | Yes |
| `pip-audit` | `pip-audit --strict` (3.12/SQLite leg) | Yes |
| `frontend` | `npm run lint` (0 errors), `npm test`, `npm audit --omit=dev --audit-level=high` | Yes (lint + tests + audit) |
| `image-scan` | buildx + GHA cache, Trivy on backend + Caddy images, HIGH/CRITICAL fail (`--ignore-unfixed`) | Yes |
| `contract-check` | regenerates `frontend/src/api/openapi.d.ts` from a live backend; fails if committed file is out of sync | Yes |

Coverage is reported in the backend job log (`pytest --cov`) but not gated. A `--cov-fail-under` threshold can be added when coverage is broadly representative.

## Best Practices

1. **Test organization**
   - Group tests by router/module: `test_items.py`, `test_pricing_providers.py`, etc.
   - Use descriptive names — the test name should read as a sentence describing the behavior.
   - Follow AAA (Arrange, Act, Assert).
   - Keep tests independent — fixtures handle DB cleanup between tests.

2. **Test data**
   - Prefer the conftest fixtures (`user`, `auth_headers`) over hand-built objects.
   - Use realistic-shaped data — avoid `name="x"` when `name="MacBook Air 13"` is just as easy.
   - Don't share mutable state between tests.

3. **Assertions**
   - Be specific. `assert r.status_code == 200` beats `assert r.ok`.
   - Test one behavior per test. Multiple assertions on one behavior is fine; multiple behaviors per test is not.
   - Include explanatory `assert msg` strings on assertions whose intent isn't obvious.

4. **External services**
   - Never hit the real LLM / eBay / Facebook API in unit tests. Use `httpx.MockTransport` (httpx) or fake clients (MagicMock + AsyncMock).
   - The compliance tests are the only place where a "real" provider response shape is canonized — keep those mocks aligned with current provider behavior.

5. **Maintenance**
   - Delete tests that test removed features (don't keep them as `pytest.skip`).
   - When fixing a bug, write the failing test first.
   - When refactoring tests, do it as a separate commit.

## Running Tests — quick reference

```bash
# Backend
pytest                                                            # all
pytest --cov=app tests/                                           # coverage
pytest tests/test_items.py                                        # one file
pytest tests/test_items.py::test_item_crud_round_trip             # one test
pytest -k pricing                                                 # filter
TEST_DATABASE_URL=postgresql+psycopg://... pytest                 # Postgres

# Frontend
npm test                                                          # all
npm run test:watch                                                # watch
npm test -- src/components/__tests__/Layout.test.tsx              # one file
```
