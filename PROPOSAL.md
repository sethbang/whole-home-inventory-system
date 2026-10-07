# Proposal: WHIS B+ → A

A remediation plan derived from a full-codebase assessment (backend quality,
frontend quality, security/ops, and documentation-vs-reality verification).
It is sequenced so the high-trust, low-effort work lands first and the riskier
structural work is gated.

## What "A" means (the rubric)

The B+ is not a code-quality verdict — the code is already A-. The grade is
dragged down by **drift**: docs that don't match reality, an understated
migration, and a few real bugs. "A" is defined concretely:

| Dimension | B+ today | A target |
|---|---|---|
| **Doc accuracy** | Test counts, version, CHANGELOG all stale | Every claim verifiable; CI guards against re-drift |
| **Correctness** | 5 known latent bugs | Zero known bugs; each fix has a regression test |
| **Consistency** | ~30 legacy `db.query()` sites; ~975 deprecation warnings; 18 ruff errors | Single SQLAlchemy idiom; warnings ~0; ruff clean & enforced |
| **Frontend structure** | 5 components >500 lines, mixed concerns | Orchestration extracted to hooks; pages readable |
| **Test coverage** | Dashboard & Settings untested | Critical pages covered; async chains tested |
| **Security** | Good, one gap (`/register` unlimited) | Gap closed; trade-offs documented, not silent |

Principle: **an A-grade project's documentation can be trusted without reading
the code.** That is the gap we are closing.

## Phase 1 — Truth & hygiene (½ day, do first)

1. **Bump version to reality.** The code carries v3.3 theme work — stamp the
   real version in `main.py`, the `/health` endpoint, and `package.json`.
   Reconcile `CLAUDE.md`'s "Current version" line.
2. **Fix the CHANGELOG.** Resolve the duplicate `[3.1.0]` header; cut the
   `[Unreleased]` theme work to its real numbered release.
3. **Refresh `CLAUDE.md` counts** — 408 backend / 128 frontend tests.
4. **Kill the dual-DB footgun.** Align `backend/.env`'s `DATABASE_URL` with the
   container (`whis.db`), or delete the stale `app.db`, and document the single
   source of truth.
5. **Clear the 18 ruff errors** and **make CI enforce `ruff check`**.

Guardrail: add a CI step that fails if the version stamp diverges across
`main.py` / `package.json` / `CLAUDE.md`.

## Phase 2 — Fix the real bugs (1 day)

Each gets a regression test first (TDD).

1. **AddItem vision→pricing race** — tag each pricing request with a generation
   counter; ignore stale responses.
2. **Stale list cache** — invalidate `queryKeys.items.lists()` alongside
   `detail` after item mutations.
3. **Job-poll dead-end** — replace `retry: false` with bounded exponential
   backoff.
4. **`aiFields` not reset** — clear the Set on form reset.
5. **`/api/register` rate limit** — add `@limiter.limit(...)` to match `/token`.

## Phase 3 — Consistency: finish the migration (1–2 days)

1. **Complete `db.query()` → `select()`** across `security.py`,
   `routers/auth.py`, `routers/pricing.py`, `services/llm_config.py`, and all
   `jobs/tasks/*.py`.
2. **Eliminate the ~975 deprecation warnings** — `datetime.utcnow()` →
   `datetime.now(UTC)`.
3. Update `CLAUDE.md`'s "Known deferred work" to drop completed items.

## Phase 4 — Frontend structure & coverage (2–3 days)

1. **Extract orchestration into hooks** — `useVisionPricingChain` (AddItem),
   marketplace subcomponents (ItemDetail), a filter reducer (Dashboard). No page
   component over ~400 lines.
2. **Test the untested** — `Dashboard.tsx` and `Settings.tsx`; extend
   ItemDetail/AddItem tests to cover the async chains.
3. **Accessibility pass** — `role="dialog"` + focus trap on modals, label
   association on checkboxes, `aria-pressed` on toggles.
4. **Finish `errorElement` wiring** for every route.

## Phase 5 — Hardening polish (½ day)

1. **Budget-guard atomicity** — make the check-and-record path atomic so
   concurrent requests cannot both pass the daily cap.
2. **Document the security trade-offs** in `SECURITY.md` (`BYPASS_AUTH`,
   SECRET_KEY-derived encryption, configurable LLM `base_url`).

## Sequencing & effort

| Phase | Effort | Risk |
|---|---|---|
| 1 — Truth & hygiene | ½ day | None |
| 2 — Bug fixes | 1 day | Low |
| 3 — Migration | 1–2 days | Medium |
| 4 — Frontend structure | 2–3 days | Medium |
| 5 — Hardening | ½ day | Low |

Total: ~5–7 days. Phases 1–2 (1.5 days) erase the drift and the known bugs,
which is most of the half-grade.

## Definition of done — A is reached when

- [ ] Every doc claim (version, test counts, CHANGELOG) is verifiably accurate, and CI guards it
- [ ] `ruff check` clean and CI-enforced; deprecation warnings ≈ 0
- [ ] Zero `db.query()` calls remain; one SQLAlchemy idiom
- [ ] All 5 bugs fixed, each with a regression test
- [ ] No frontend page component over ~400 lines; Dashboard & Settings tested
- [ ] Every route has an `errorElement`; modals are accessible
- [ ] Security trade-offs documented in `SECURITY.md`
- [ ] Full suite green: backend + frontend + lint
