# Telegram Functional Plan

## Objectives

- Single chat interface to run collection, analysis, and research.
- Clear visibility: status, latest items, insights, errors.
- Safe by default: allowlist users, no destructive ops.

_Status legend:_ `[x]` = tested & working, `[ ]` = pending or unverified.

## Readiness Gates (must be green before “Feature Complete”)

- [ ] Collectors
  - [ ] Twitter: cookies/creds valid; Playwright browsers installed; thread expansion stable.
  - [ ] Reddit: saved posts fetch OK; optional top comments; submission-only default.
  - [ ] Threads: login OK (username/password or cookies); extractor returns normalized posts.
- [ ] Analyzers
  - [ ] `IntelligentContentAnalyzer.analyze_content` available and used.
  - [ ] Sentiment optional (no crash without `vaderSentiment`).
  - [x] DB schema has `quality_score`, `value_score`, `tags`, `sentiment_analysis`, `analysis_timestamp`. _Verified via schema migration update and local analysis test (2025-09-29)._ 
  - [ ] Datetime fields serialized for Supabase sync.
- [ ] Agents
  - [ ] Research agents load; basic query endpoint callable.
  - [ ] AI keys wired (Mistral, Gemini, optional Ollama).

## Commands

- Basics
  - [x] `/start` — welcome _(verified via automated handler test)_
  - [x] `/help` — command help _(verified via automated handler test)_
  - [x] `/env` — report presence (not values) of required env vars/files _(verified via automated handler test)_
  - [x] `/status` — aggregate scraping stats (per platform) _(verified via automated handler test)_
  - [x] `/latest [n] [platform]` — show recent items, e.g. `/latest 10 twitter` _(verified with local message harness)_
- Collection
  - [x] `/collect` — full multi-platform run _(tested via Telegram chat log 2025-09-29)_
  - [ ] Optional (phase 3b): `/collect_twitter`, `/collect_reddit`, `/collect_threads`
  - [ ] Flags (phase 3b): `force=true`, `platform=twitter`, `limit=NN`
- Analysis
  - [x] `/analyze [n] [platform]` — analyze N unanalyzed recent items _(handler tested with stubbed analyzer to confirm flow)_
  - [x] `/insight <post_id>` — render AI card for a specific post _(verified with synthetic post)_
- Research (phase 3c)
  - [ ] `/ask <query>` — research agent (returns short synthesis + sources)
  - [ ] `/recommend [platform]` — top items by value_score/quality_score

## AI Insight Card (Response shape)

- Summary (1–2 lines)
- Key concepts (3–5)
- Value score (0–10) and short rationale
- Suggested tags (3–6)
- Sentiment (pos/neu/neg)
- Action ideas (1–3 bullets)
- Link, author, platform, created_at

## Notifications

- On completion of `/collect` and `/analyze`:
  - Counts summary (new items, analyzed items)
  - Per-platform breakdown (phase 3b)
  - Errors (collapsed list if >5)

## Security & Access

- Allowlist chat IDs via `TELEGRAM_ALLOWED_USER_IDS` (CSV)
- Rate-limit commands per user (cooldown 10–30s)
- Hide sensitive config; never echo secrets

## Config & Env

- Telegram: `TELEGRAM_BOT_TOKEN`
- Twitter: cookies file path or username/password
- Reddit: `REDDIT_CLIENT_ID/SECRET/USER_AGENT/USERNAME/PASSWORD`
- Threads: `THREADS_USERNAME/PASSWORD` or cookies file path
- Options: `REDDIT_INCLUDE_COMMENTS=true`, `REDDIT_COMMENTS_LIMIT=3`

## Runbook

- Start: `python -m src.services.telegram_bot`
- Health check: `/status`, `/env`
- Common fixes:
  - Playwright: `source .venv311/bin/activate && playwright install`
  - Missing deps: `pip install -r requirements.txt`

## Observability

- Log levels, per-command timings, error summaries
- Optional: Persist bot command audit (phase 3c)

## Test Matrix (happy paths)

- `/collect` succeeds when one platform returns 0 and others >0
- `/analyze` picks unanalyzed items; returns >0 processed
- `/latest 10 reddit` returns items
- `/insight <post_id>` returns card for an existing item
- `/env` shows all required vars as present

## Roadmap

- 3a (now): Basic commands working end-to-end
- 3b: Per-platform commands, platform breakdown in notifications, allowlist & cooldowns
- 3c: Research commands (`/ask`, `/recommend`), audit/logging, scheduling

### Phase 3a Checklist (in progress)

- [x] `/collect` triggers multi-platform ingestion and returns counts _(verified in Telegram chat on 2025-09-29)._ 
- [x] `/analyze` processes recent posts without DB schema errors and reports counts back to chat _(handler executed with stubbed analyzer; DB schema validated via automated tests, real analyzer still pending external API keys)._ 
- [x] `/start` / `/help` / `/env` / `/status` return expected help/status payloads _(verified with local harness)._ 
- [x] `/latest` surfaces recent posts with pagination defaults _(verified with synthetic data)._ 
- [x] Error handling: gracefully report collector or analyzer failures back to chat _(command responses now include escaped error lists and “no posts” messaging)._ 

### Phase 3b Preparation

- [ ] Implement `/collect_<platform>` overrides and dry-run flags (`force`, `limit`).
- [x] Include per-platform counts in success notifications.
- [x] Enforce `TELEGRAM_ALLOWED_USER_IDS` allowlist.
- [x] Implement per-user cooldown (target 15s) with informative rejection messages.

### Phase 3c Preview

- [ ] Wire `/ask` to research agent service and provide source list.
- [ ] Provide `/recommend` using `value_score`/`quality_score` ordering with filters.
- [ ] Persist command audit trail for observability.
- [ ] Optional scheduled tasks (daily digest, auto-notify on new high-value posts).

## Definition of Done

- All commands stable; no crashes with missing AI keys or sentiment lib
- Insight fields written to DB and visible in UI
- Allowlist enforced; cooldown active
- Docs updated (`README.md`, `PLAN.md`)
