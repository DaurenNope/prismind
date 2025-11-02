# Mimesis → Prismind Integration Plan

## Current State (Messy)

### Two Separate Codebases
1. **`/mimesis/`** - Original standalone mimesis project (97 references to `from app.`)
   - Full automation/posting system
   - Twitter, Threads, Telegram posters
   - Autoposter service (FastAPI)
   - Complete UI (Streamlit)
   - Scheduler, queue, editor

2. **`/src/mimesis/`** - Partially integrated (12 references to `from src.mimesis`)
   - Only database bridge copied
   - Transformer and personalities
   - **Incomplete integration**

### Duplicates/Conflicts
- `src/publishing/` exists but unclear purpose
- `src/services/twitter_poster.py` (new) vs `mimesis/app/services/posting/twitter_poster.py` (original)
- `src/services/threads_poster.py` (new) vs `mimesis/app/automation/platforms/threads.py` (original)
- Database bridges in multiple places

### What Works Now
✅ Twitter posting - Direct API via `src/services/twitter_poster.py`
✅ Telegram posting - Direct API via `publisher_worker.py`
⚠️ Threads posting - Incomplete (created poster but not integrated)
⚠️ Content transformation - Uses `src.mimesis.services.transformer`
⚠️ Personality system - Uses `src.mimesis.services.personalities`

## Goal: Single Unified Project

All functionality accessible as **one project** called **prismind** with:
- Collection (Reddit, Twitter, Threads) → Analysis → Publishing
- No duplicate files
- Clear, consistent imports
- All features working

## Integration Strategy

### Option A: Move Everything to src/ (RECOMMENDED)
```
prismind/
├── src/
│   ├── collection/           # Reddit, Twitter, Threads extractors
│   ├── analysis/             # AI analysis, content analyzer
│   ├── publishing/           # All posting functionality
│   │   ├── database/         # Publishing DB operations
│   │   ├── transformer.py    # Content transformation
│   │   ├── personalities.py  # Personality configs
│   │   ├── posters/
│   │   │   ├── twitter.py
│   │   │   ├── telegram.py
│   │   │   └── threads.py
│   │   └── scheduler.py      # Scheduling logic
│   ├── automation/           # Browser automation (if needed)
│   └── web/
│       └── components/
│           ├── collection_tab.py
│           ├── analysis_tab.py
│           └── publishing_tab.py  # Combined publishing UI
├── config/
├── data/
└── mimesis/ → ARCHIVE (keep for reference)
```

### Option B: Keep mimesis/ as Submodule
- More complex
- Harder to maintain
- **NOT RECOMMENDED**

## Detailed Migration Steps

### Phase 1: Complete Posting Integration ✅ (Partially Done)
1. ✅ Twitter poster in `src/services/twitter_poster.py`
2. ✅ Telegram posting in `publisher_worker.py`
3. ⚠️ **TODO**: Threads poster integration
4. ⚠️ **TODO**: Consolidate posting logic

### Phase 2: Unify Publishing System
1. **Move** `src/mimesis/services/` → `src/publishing/`
   - `database/bridge.py` → `src/publishing/database.py`
   - `transformer.py` → `src/publishing/transformer.py`
   - `personalities.py` → `src/publishing/personalities.py`

2. **Consolidate posters** into `src/publishing/posters/`
   - `twitter.py` (already in src/services, move it)
   - `telegram.py` (extract from publisher_worker)
   - `threads.py` (already created, integrate it)

3. **Update** `publisher_worker.py` to import from `src.publishing.posters`

4. **Merge** publishing UI components:
   - `mimesis_overview_tab.py` + `mimesis_queue_tab.py` + `mimesis_editor_tab.py` + `mimesis_scheduler_tab.py`
   - → Single `publishing_tab.py` with sub-sections

### Phase 3: Update All Imports
1. Find all `from src.mimesis` → Replace with `from src.publishing`
2. Remove `src/mimesis/` directory
3. Update web components to use new paths

### Phase 4: Archive Original mimesis/
1. Move `mimesis/` → `archive/mimesis-standalone/`
2. Keep for reference but not in active codebase
3. Update README to reflect single project structure

### Phase 5: Testing
1. Test all posting (Twitter, Telegram, Threads)
2. Test content transformation
3. Test scheduling and queueing
4. Test UI components
5. Integration test: Full flow from collection → analysis → posting

## Immediate Action Plan

### Step 1: Complete Threads Posting (NOW)
```bash
# Already created: src/services/threads_poster.py
# TODO: Add to publisher_worker.py
# TODO: Add to mimesis_scheduler_tab.py
# TODO: Test with your THREADS_TOKEN_ACCESS
```

### Step 2: Create Unified Publishing Module
```bash
# Move files
mv src/mimesis/services/* src/publishing/
mv src/services/twitter_poster.py src/publishing/posters/
mv src/services/threads_poster.py src/publishing/posters/

# Create telegram_poster.py from publisher_worker function
# Update imports everywhere
```

### Step 3: Update Web UI
```bash
# Consolidate publishing tabs into one clean interface
# Update imports from src.mimesis → src.publishing
```

### Step 4: Test & Document
```bash
# Test all functionality
# Update README
# Create INTEGRATION_COMPLETE.md
```

## File Mapping (What Goes Where)

### From mimesis/ (Keep for Reference)
- `mimesis/app/automation/` → **Reference only** (Playwright automation if needed)
- `mimesis/app/services/posting/` → **Already copied to src/services/**
- `mimesis/scripts/autoposter_service.py` → **Keep separate** (optional external service)

### From src/mimesis/ (Move to src/publishing/)
- `src/mimesis/services/database/bridge.py` → `src/publishing/database.py`
- `src/mimesis/services/transformer.py` → `src/publishing/transformer.py`
- `src/mimesis/services/personalities.py` → `src/publishing/personalities.py`

### From src/services/ (Reorganize to src/publishing/posters/)
- `src/services/twitter_poster.py` → `src/publishing/posters/twitter.py`
- `src/services/threads_poster.py` → `src/publishing/posters/threads.py`
- Extract telegram functions → `src/publishing/posters/telegram.py`
- Keep `publisher_worker.py` in services (orchestrator level)

## Expected Final Structure

```
prismind/
├── src/
│   ├── collection/          # Data gathering (existing)
│   ├── analysis/            # AI analysis (existing)
│   ├── publishing/          # NEW: Unified publishing
│   │   ├── __init__.py
│   │   ├── database.py      # MimesisDB bridge
│   │   ├── transformer.py   # Content transformation
│   │   ├── personalities.py # Personality configs
│   │   └── posters/
│   │       ├── __init__.py
│   │       ├── twitter.py
│   │       ├── telegram.py
│   │       └── threads.py
│   ├── services/
│   │   ├── publisher_worker.py  # Orchestrates posting
│   │   └── ... (other services)
│   └── web/
│       └── components/
│           ├── collection_tab.py
│           ├── analysis_tab.py
│           └── publishing_tab.py  # Unified publishing UI
├── config/
│   ├── personalities.json
│   └── platform_integrations.json
├── data/
├── archive/
│   └── mimesis-standalone/  # Original project for reference
└── README.md                # Updated for unified project
```

## Benefits of Unified Structure

1. **Single source of truth** - No duplicate code
2. **Clear imports** - `from src.publishing.posters import TwitterPoster`
3. **Easier maintenance** - One codebase to update
4. **Better testing** - Unified test suite
5. **Simpler deployment** - One application
6. **Clear documentation** - One project structure

## Next Actions

1. ✅ Finish Threads posting integration
2. Create `src/publishing/` module structure
3. Move all publishing code to new structure
4. Update imports across codebase
5. Archive original mimesis/
6. Test everything
7. Update documentation

Ready to proceed?
