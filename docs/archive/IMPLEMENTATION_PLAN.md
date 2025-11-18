# 📋 Core Stabilization Plan — Scrape → Analyze → Discover → Surface

Focused two-week plan to deliver a robust, provably working core: collectors and storage first, then analysis quality, then RSS/discoveries, then thin UI/Bot on top. Includes safety precautions to avoid account bans.

---

## 🎯 Objectives (Order Matters)
1. Scraping + Storage: perfect, deterministic collectors with idempotent persistence
2. Analysis Quality: complete, consistent AI fields; deterministic scoring
3. RSS/Discoveries: stable ingestion, dedupe, ranking, Supabase sync
4. Surface: minimal Svelte Discoveries and minimal Telegram commands

Guardrails:
- No schema changes; use `posts`, `discoveries`, `telegram_messages`
- Logic stays in services/core; UI/Bot are read-only clients
- Deterministic code paths, timeouts, retries, idempotent writes

---

## ✅ Replacement To‑Do List (Prioritized)

Phase 0 — Safety (anti-ban)
1) p0-safety-rate-limits: Implement per-platform action budgets and jittered delays
2) p0-safety-backoff: Add exponential backoff + circuit breakers on 403/429/5xx
3) p0-safety-session: Enforce single active session per account; cookie refresh flow
4) p0-safety-scroll: Cap scroll depth, stagger sessions, strict stop-at-last
5) p0-safety-telemetry: Structured, redacted logs + safety metrics

Phase 1 — Collectors + Storage
6) p1-twitter-threads: Re-enable Twitter thread extraction with safe selectors/fallbacks
7) p1-reddit-harden: Harden Reddit saved collector (timeouts, rate limit handling)
8) p1-threads-auth: Fix Threads cookie auth + selectors; add retries/backoff
9) p1-storage-idempotent: Idempotent upserts and last-post tracking
10) p1-supabase-sync: Verify stable Supabase sync for posts and discoveries

Phase 2 — Analysis Quality
11) p2-ai-parse-lists: Ensure AI list fields never None; robust JSON parsing
12) p2-ai-schema: Normalize provider outputs into one analysis schema
13) p2-ai-scoring: Define/apply deterministic value/quality thresholds

Phase 3 — RSS/Discoveries
14) p3-rss-validate: Validate 60-source RSS intake with guards and normalization
15) p3-discover-dedupe-rank: Cross-source dedupe, categorize, rank, persist to discoveries

Phase 4 — Surface (thin UI/Bot)
16) p4-ui-discoveries: Read-only Discoveries tab with filters + pagination
17) p4-bot-minimal: Stabilize /latest and /status; defer advanced commands

Tests
18) tests-add: Add light tests for collectors, analysis, discoveries, basic UI

---

## 📂 Files To Touch
- Collectors: `src/core/extraction/twitter_extractor_playwright.py`, `src/core/extraction/twitter/`, `src/core/extraction/reddit_extractor.py`, `src/core/extraction/threads_extractor.py`
- Orchestration/Storage: `src/services/collection/platform_collectors.py`, `src/services/database_operations.py`, `src/services/database_queries.py`
- Supabase: `src/services/supabase/post_inserter.py`, `src/supabase_manager.py`
- Analysis: `src/core/analysis/content_analyzer_core.py`, `src/services/analysis_service.py`, `src/services/analysis/post_analyzer.py`
- RSS/Discoveries: `src/services/autonomous_discovery.py`, `src/core/extraction/edgy_sources.py`, `src/core/extraction/article_extractor.py`
- UI/Bot: `src/web/app.py`, `src/web/components/discoveries_tab.py`, `src/services/telegram_bot.py`, `src/services/telegram_formatting.py`

---

## 🔒 Safety Specifications
- Budgets: Twitter ≤ 12 actions/min, ≤ 150/day; Reddit per headers; Threads 1 nav/8–12s
- Human-like Playwright behavior: UA, viewport, jitter 300–1200ms, reuse sessions
- Backoff: exponential with jitter; respect Retry-After; circuit breaker cool-downs
- Scrolling: enforce stop-at-last; limit scroll depth; stagger sessions
- Identity: single active session per account; stable residential IP

Proposed `config/collection.json` extensions:
```json
{
  "safety": { "enabled": true, "global_max_parallel_sessions": 1, "telemetry_level": "warn" },
  "twitter": { "actions_per_min": 12, "actions_per_day_cap": 150, "scroll_limit": 5, "jitter_ms": [300, 1200], "backoff": { "base_ms": 800, "max_ms": 15000, "retries": 4, "circuit_cooldown_s": 1800 } },
  "reddit": { "requests_per_hour_cap": 60, "respect_retry_after": true, "backoff": { "base_ms": 500, "max_ms": 10000, "retries": 5 } },
  "threads": { "nav_interval_s": [8, 12], "max_retries": 3, "backoff": { "base_ms": 1000, "max_ms": 20000, "retries": 4 } }
}
```

---

## ✅ Verification Checklist
- Collectors: `pytest tests/test_twitter_collector.py -v`, `pytest tests/test_reddit_collector.py -v`, `pytest tests/test_threads_collector.py -v`
- Analysis: `pytest tests/test_ai_analyzer.py -v`, `pytest tests/test_post_analyzer.py -v`
- Discovery: `pytest tests/test_collection.py -v`, `pytest tests/test_collectors.py -v`
- UI/Bot smoke: `svelte run src/web/app.py` and `/status`, `/latest 5`

Success criteria:
- Deterministic incremental collection; no bans; 0 critical errors in logs
- AI fields populated (no None lists); stable scores and ranges
- Discoveries populated, deduped, ranked; Supabase sync healthy
- UI read-only list with filters; Telegram basic commands stable

---

**Last Updated:** October 31, 2025
**Current Phase:** Phase 0–1 (Safety + Collectors)
**Status:** Ready to implement 🚀
