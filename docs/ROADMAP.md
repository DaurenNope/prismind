## PrisMind Roadmap

### Scope & Goals

- Ship a minimal, reliable social intelligence pipeline with a professional repo layout.
- Ensure predictable collection, analysis, storage, and basic UI, with CI and tests.

### Phase 1 — Stabilize & Professionalize (Week 1)

- [X] Repository cleanup (root minimized; redundant/ organized)
- [X] Canonical services layer (`services/` imports)
- [X] CI + pre-commit hooks
- [X] Makefile tasks
- [X] Test harness bootstrapping (pytest fixtures, sample data)

Deliverables:

- Clean root, `services/` as canonical layer, CI passing baseline
  Acceptance criteria:

- [X] CI runs on PRs and main; lints and tests pass
- [X] Root contains only entrypoints and core dirs

### Phase 2 — Scheduling & Collection (Week 1–2)

- [X] APScheduler runner
- [ ] Twitter collector stable (rate limits respected)
- [ ] Reddit collector stable (rate limits respected)
- [X] Scrape state persisted to `var/`
- [X] Webhook notifier on job completion

Deliverables:

- Reliable periodic collection; idempotent runs
  Acceptance criteria:

- [ ] Scheduled run every N minutes without crashes for 24h
- [ ] Webhook receives JSON summary with totals and timestamps

### Phase 3 — Analysis Pipeline (Week 2)

- [ ] Intelligent content analyzer deterministic mode
- [ ] Value scoring env toggle (`USE_VALUE_SCORER`)
- [ ] Optional media analysis step (best-effort)

Deliverables:

- Stable analysis outputs, configurable scoring
  Acceptance criteria:

- [ ] Same input → same summary in deterministic mode
- [ ] Scoring can be disabled without breaking UI

### Phase 4 — Database & Integrations (Week 2–3)

- [X] `services.database` canonical usage
- [ ] Optional Supabase sync behind `SAVE_TO_SUPABASE`
- [ ] Lightweight migration helpers (idempotent)

Deliverables:

- Full local SQLite coverage; optional cloud sync
  Acceptance criteria:

- [ ] Local DB CRUD fully covered by tests
- [ ] Supabase sync smoke test passes with mock client

### Phase 5 — Dashboard UX (Week 3)

- [ ] Streamlit UI cleanup: tabs, filters, exports
- [ ] Basic insights panels with fast rendering

Deliverables:

- Usable UI for browsing and exporting
  Acceptance criteria:

- [ ] P95 UI render < 500ms on 1k rows locally
- [ ] Exports (CSV/JSON) working from UI

### Phase 6 — Packaging & Deploy (Week 3–4)

- [ ] Clear README install and usage
- [ ] Example `.env.example`
- [ ] One-click deployment notes (kept under `redundant/`)

Deliverables:

- Reproducible setup; dev UX is “make run”
  Acceptance criteria:

- [ ] Fresh clone → `make run` works without manual steps

---

### Testing Plan

- Unit
  - [X] services.database: schema init, CRUD, migrations
  - [X] services.notifier_webhook: disabled/enabled, success/failure paths
  - [X] scrape_state_manager: state read/write, cleanup
- Integration
  - [X] Collector orchestration with mocked extractors (Twitter/Reddit)
  - [X] APScheduler job triggers collectors and writes DB
  - [X] Webhook notifier posts after job
- E2E (smoke)
  - [X] Run a full collection against fixtures
  - [X] Assert DB rows, UI loads, export works

Test data fixtures:

- `tests/fixtures/twitter_saved.json`
- `tests/fixtures/reddit_saved.json`

Coverage targets:

- P0 paths ≥ 90% (database, collectors, scheduler)
- Overall ≥ 80%

---

### Architecture Checklist

- [ ] Canonical imports from `services/` only
- [ ] Feature flags via env with sane defaults
- [X] All write paths use `var/` for state/data
- [X] Non-runtime assets under `redundant/`

### Observability & Quality

- [ ] Structured logs for scheduler and collectors
- [ ] Error counters for failed runs
- [ ] Retry/backoff on transient failures

### Risks & Mitigations

- [ ] Rate limits → configurable pacing, backoff
- [ ] Site HTML changes → extractor unit tests + resilient parsing
- [ ] API keys/secrets → `.env`, no secrets in repo

### Roles & Ownership

- [X] Code ownership: `.github/CODEOWNERS`
- [ ] Review gates: CI green + at least one approval

### Timeline (High-level)

- Week 1: Phase 1
- Week 1–2: Phase 2
- Week 2: Phase 3
- Week 2–3: Phase 4
- Week 3: Phase 5
- Week 3–4: Phase 6

### Done Definition

- CI green, coverage targets met, roadmap acceptance criteria checked
