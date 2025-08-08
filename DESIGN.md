# PrisMind Design

## Architecture
- Ingest: `collect_multi_platform.py` calls platform extractors → creates `SocialPost` dicts.
- Analyze: `IntelligentContentAnalyzer` (providers: Ollama/Qwen → Mistral → Gemini → Basic).
- Persist: local SQLite (`data/prismind.db`) always; optional Supabase (`SAVE_TO_SUPABASE=1`).
- UI: `scripts/dashboard.py` reads from SQLite.

## Source of truth
- Supabase is the cloud source of truth for sharing/APIs.
- SQLite is a local cache/offline store for the dashboard.

## Analysis Providers
- Default: Ollama Qwen when `OLLAMA_URL` is set. Fallbacks: Mistral, Gemini, Basic.
- JSON schema: category, subcategory, content_type, topics, key_concepts, summary, actionable_items, etc.

## Scoring
- `intelligent_value_score` computed inside analyzer for ranking.
- Saving `value_score` to DB is gated by `USE_VALUE_SCORER` (default off). Ranking in UI still sorts by score if present.

## Feedback
- Local feedback system is disabled by default (`ENABLE_LOCAL_FEEDBACK=0`). Left in place for tests.

## Coding Rules
- Remove or quarantine redundant files.
- Clear naming, typed signatures, early returns, no deep nesting.
- Ask when intent is unclear. Keep this doc updated with changes.


