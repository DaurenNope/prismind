# Prismind Codebase Restructuring Plan

## Executive Summary

After successful cleanup of the 1.6GB mimesis/ folder, analysis reveals **critical structural issues** in the remaining codebase:

### Key Issues Identified:
1. **Duplicate modules**: Both `src/mimesis/` and `src/publishing/` exist with identical files
2. **Publishing folder is a facade**: Just imports from mimesis (not a real consolidation)
3. **23 unorganized service files** in `src/services/` directory
4. **5 database-related files** scattered across different locations
5. **Poor naming conventions**: "mimesis_" prefix on web components when it's actually "publishing"
6. **Root-level files** that should be in proper modules

---

## Current Structure Problems

### Problem 1: Duplicate Mimesis/Publishing Modules

```
src/
├── mimesis/                          # ❌ DUPLICATE
│   └── services/
│       ├── database/bridge.py        # Real implementation (149 lines)
│       ├── personalities.py          # Real implementation
│       └── transformer.py            # Real implementation
└── publishing/                       # ❌ FACADE (just imports mimesis)
    └── services/
        ├── database/bridge.py        # Just imports: "from src.mimesis..."
        ├── personalities.py          # Just imports: "from src.mimesis..."
        └── transformer.py            # Just imports: "from src.mimesis..."
```

**Impact**: 9 files import from these modules - some use `src.mimesis`, some use `src.publishing`, creating confusion.

**Files affected**:
- `src/services/publisher_worker.py` 
- `src/web/components/mimesis_scheduler_tab.py`
- `src/web/components/mimesis_analytics_tab.py`
- `src/web/components/mimesis_queue_tab.py`
- `src/web/components/mimesis_overview_tab.py`
- `src/web/components/mimesis_editor_tab.py`
- Plus the 3 publishing files themselves

### Problem 2: Services Directory Chaos (23 files, no organization)

```
src/services/
├── __init__.py
├── ai_summarizer.py                  # Analysis-related
├── analysis_service.py               # Analysis-related
├── autonomous_discovery.py           # Discovery-related
├── content_rewriter.py               # Publishing-related
├── database_analysis.py              # Database-related ❌
├── database_operations.py            # Database-related ❌
├── database_queries.py               # Database-related ❌
├── digest_generator.py               # Analysis-related
├── health_monitor.py                 # System-related
├── intelligence_automation.py        # Orchestration-related
├── new_database_manager.py           # Database-related ❌
├── notifier_webhook.py               # Publishing-related
├── posting_service.py                # Publishing-related
├── publisher_worker.py               # Publishing-related
├── supabase_webhook.py               # Database-related
├── telegram_bot.py                   # Publishing-related (Telegram)
├── telegram_bot_agents_extension.py  # Publishing-related (Telegram)
├── telegram_collection_commands.py   # Collection-related
├── telegram_formatting.py            # Publishing-related (Telegram)
├── threads_poster.py                 # Publishing-related
├── twitter_poster.py                 # Publishing-related
└── unified_collection_service.py     # Collection-related
```

**Analysis**:
- 4 database files (+ 1 more in root = 5 total)
- 8 publishing-related files
- 3 collection-related files
- 3 analysis-related files
- 2 Telegram-specific files
- 2 system/orchestration files

### Problem 3: Database Files Scattered (5 locations)

```
src/
├── scrape_state_database.py          # ❌ Root level (should be in module)
└── services/
    ├── database_analysis.py          # ❌ In generic services/
    ├── database_operations.py        # ❌ In generic services/
    ├── database_queries.py           # ❌ In generic services/
    └── new_database_manager.py       # ❌ In generic services/
```

Plus:
- `src/supabase_manager.py` (root level - shared by all)
- `src/storage/supabase_adapter.py`
- `src/mimesis/services/database/bridge.py` (publishing-specific)

### Problem 4: Confusing Web Component Names

```
src/web/components/
├── mimesis_analytics_tab.py          # ❌ Should be publishing_analytics_tab.py
├── mimesis_editor_tab.py             # ❌ Should be publishing_editor_tab.py
├── mimesis_overview_tab.py           # ❌ Should be publishing_overview_tab.py
├── mimesis_queue_tab.py              # ❌ Should be publishing_queue_tab.py
├── mimesis_scheduler_tab.py          # ❌ Should be publishing_scheduler_tab.py
```

### Problem 5: Root-Level Files That Should Be in Modules

```
src/
├── scrape_state_database.py          # ❌ Should be in src/storage/ or src/database/
├── scrape_state_manager.py           # ❌ Should be in src/storage/ or src/database/
└── supabase_manager.py               # ❌ Should be in src/storage/ or src/database/
```

---

## Proposed Professional Structure

Following Django/Flask/FastAPI conventions:

```
src/
├── core/                              # ✅ Core business logic (already good)
│   ├── analysis/
│   ├── collection/
│   ├── discovery/
│   ├── extraction/
│   ├── indexing/
│   ├── learning/
│   ├── normalization/
│   ├── rate_limiting/
│   ├── research/
│   └── validation/
│
├── database/                          # ✅ NEW: All database operations
│   ├── __init__.py
│   ├── manager.py                     # (from supabase_manager.py)
│   ├── operations.py                  # (from database_operations.py)
│   ├── queries.py                     # (from database_queries.py)
│   ├── analysis.py                    # (from database_analysis.py)
│   ├── scrape_state.py                # (from scrape_state_database.py)
│   └── publishing/                    # Publishing-specific DB
│       └── bridge.py                  # (from mimesis/services/database/bridge.py)
│
├── publishing/                        # ✅ CLEANED: All publishing functionality
│   ├── __init__.py
│   ├── personalities.py               # (from mimesis/services/personalities.py)
│   ├── transformer.py                 # (from mimesis/services/transformer.py)
│   ├── worker.py                      # (from services/publisher_worker.py)
│   ├── rewriter.py                    # (from services/content_rewriter.py)
│   └── platforms/                     # Platform-specific posters
│       ├── __init__.py
│       ├── twitter.py                 # (from services/twitter_poster.py)
│       ├── threads.py                 # (from services/threads_poster.py)
│       └── telegram/
│           ├── __init__.py
│           ├── bot.py                 # (from services/telegram_bot.py)
│           ├── formatting.py          # (from services/telegram_formatting.py)
│           └── agents.py              # (from services/telegram_bot_agents_extension.py)
│
├── services/                          # ✅ CLEANED: Only high-level services
│   ├── __init__.py
│   ├── analysis.py                    # (from analysis_service.py)
│   ├── summarizer.py                  # (from ai_summarizer.py)
│   ├── digest.py                      # (from digest_generator.py)
│   ├── collection.py                  # (from unified_collection_service.py)
│   ├── discovery.py                   # (from autonomous_discovery.py)
│   ├── automation.py                  # (from intelligence_automation.py)
│   └── health.py                      # (from health_monitor.py)
│
├── storage/                           # ✅ Existing (keep as-is)
│   └── supabase_adapter.py
│
├── utils/                             # ✅ Existing (keep as-is)
│   └── post_validator.py
│
├── web/                               # ✅ Web UI
│   ├── app.py
│   └── components/
│       ├── analysis_tab.py
│       ├── collection_tab.py
│       ├── publishing_analytics_tab.py    # ✅ RENAMED from mimesis_*
│       ├── publishing_editor_tab.py       # ✅ RENAMED from mimesis_*
│       ├── publishing_overview_tab.py     # ✅ RENAMED from mimesis_*
│       ├── publishing_queue_tab.py        # ✅ RENAMED from mimesis_*
│       ├── publishing_scheduler_tab.py    # ✅ RENAMED from mimesis_*
│       ├── settings_page.py
│       ├── sidebar.py
│       ├── status_bar.py
│       ├── tabs.py
│       ├── telegram_channels_manager.py
│       └── telegram_tab.py
│
└── pipeline/                          # ✅ Existing orchestrator (keep as-is)
    └── orchestrator.py
```

---

## Execution Plan (5 Phases)

### Phase 1: Consolidate Mimesis → Publishing (CRITICAL)

**Goal**: Remove duplicate mimesis/ folder, keep only publishing/

**Steps**:
1. Move real implementations from `src/mimesis/services/` to `src/publishing/`
2. Delete `src/publishing/services/` (the facade files)
3. Update 9 files that import from `src.mimesis` → `src.publishing`
4. Delete empty `src/mimesis/` directory
5. Test: Verify all imports work

**Files to modify**:
- `src/services/publisher_worker.py`
- `src/web/components/mimesis_scheduler_tab.py`
- `src/web/components/mimesis_analytics_tab.py`
- `src/web/components/mimesis_queue_tab.py`
- `src/web/components/mimesis_overview_tab.py`
- `src/web/components/mimesis_editor_tab.py`

**Risk**: Medium (import changes across 9 files)

---

### Phase 2: Create database/ Module & Consolidate

**Goal**: Move all 5 scattered database files into `src/database/`

**Steps**:
1. Create `src/database/` directory
2. Move & rename files:
   - `src/supabase_manager.py` → `src/database/manager.py`
   - `src/scrape_state_database.py` → `src/database/scrape_state.py`
   - `src/services/database_operations.py` → `src/database/operations.py`
   - `src/services/database_queries.py` → `src/database/queries.py`
   - `src/services/database_analysis.py` → `src/database/analysis.py`
3. Create `src/database/publishing/` subdirectory
4. Move `src/publishing/services/database/bridge.py` → `src/database/publishing/bridge.py`
5. Update ~30+ imports from `src.supabase_manager` → `src.database.manager`
6. Create `src/database/__init__.py` with convenient exports
7. Test: Verify database operations work

**Files to search and update**:
```bash
grep -r "from src.supabase_manager" src/
grep -r "from src.scrape_state_database" src/
grep -r "from src.services.database_" src/
```

**Risk**: High (many imports to update, core functionality)

---

### Phase 3: Reorganize Publishing Services

**Goal**: Move 8 publishing-related files from services/ to publishing/

**Steps**:
1. Create `src/publishing/platforms/` directory
2. Move files:
   - `src/services/publisher_worker.py` → `src/publishing/worker.py`
   - `src/services/content_rewriter.py` → `src/publishing/rewriter.py`
   - `src/services/twitter_poster.py` → `src/publishing/platforms/twitter.py`
   - `src/services/threads_poster.py` → `src/publishing/platforms/threads.py`
3. Create `src/publishing/platforms/telegram/` subdirectory
4. Move Telegram files:
   - `src/services/telegram_bot.py` → `src/publishing/platforms/telegram/bot.py`
   - `src/services/telegram_formatting.py` → `src/publishing/platforms/telegram/formatting.py`
   - `src/services/telegram_bot_agents_extension.py` → `src/publishing/platforms/telegram/agents.py`
5. Update imports in web components
6. Test: Verify publishing/scheduling works

**Risk**: Medium (publishing is critical, but well-isolated)

---

### Phase 4: Clean Up services/ Directory

**Goal**: Rename remaining files for clarity, move collection services

**Steps**:
1. Rename for clarity:
   - `src/services/analysis_service.py` → `src/services/analysis.py`
   - `src/services/ai_summarizer.py` → `src/services/summarizer.py`
   - `src/services/digest_generator.py` → `src/services/digest.py`
   - `src/services/autonomous_discovery.py` → `src/services/discovery.py`
   - `src/services/intelligence_automation.py` → `src/services/automation.py`
   - `src/services/health_monitor.py` → `src/services/health.py`
2. Move collection service:
   - `src/services/unified_collection_service.py` → `src/services/collection.py`
3. Consider moving `src/services/telegram_collection_commands.py` to `src/core/collection/`
4. Update imports
5. Test: Verify services still work

**Risk**: Low (mostly renames)

---

### Phase 5: Rename Web Components (Remove "mimesis_" Prefix)

**Goal**: Rename 5 web components from `mimesis_*` to `publishing_*`

**Steps**:
1. Rename files:
   - `mimesis_analytics_tab.py` → `publishing_analytics_tab.py`
   - `mimesis_editor_tab.py` → `publishing_editor_tab.py`
   - `mimesis_overview_tab.py` → `publishing_overview_tab.py`
   - `mimesis_queue_tab.py` → `publishing_queue_tab.py`
   - `mimesis_scheduler_tab.py` → `publishing_scheduler_tab.py`
2. Update imports in `src/web/app.py`
3. Update any component references
4. Test: Verify all tabs load in UI

**Risk**: Low (just renames, UI will catch errors immediately)

---

## Testing Strategy

After each phase:

1. **Import Test**: Run Python to verify no import errors
   ```bash
   python -c "from src.web.app import *"
   ```

2. **Streamlit Test**: Start the web app
   ```bash
   streamlit run src/web/app.py
   ```

3. **Functional Test**: 
   - Phase 1: Check publishing tab loads
   - Phase 2: Verify database queries work
   - Phase 3: Test posting to Twitter/Telegram/Threads
   - Phase 4: Check analysis/collection services
   - Phase 5: Verify all tabs visible and functional

---

## Estimated Impact

### Files to Delete:
- `src/mimesis/` entire directory (3 files + facade structure)
- Old service files (will be moved, not deleted)

### Files to Create:
- `src/database/` module (5 files + 1 subdirectory)
- `src/publishing/platforms/` structure (reorganized)

### Files to Modify (imports):
- ~40-50 files will need import updates

### Lines of Code Changed:
- ~100-150 import statements to update

### Time Estimate:
- Phase 1: 15 minutes
- Phase 2: 30 minutes (most risky)
- Phase 3: 20 minutes
- Phase 4: 15 minutes
- Phase 5: 10 minutes
- **Total: ~90 minutes** (with testing)

---

## Rollback Strategy

Before starting:
1. Commit current state to git
2. Create backup branch: `git checkout -b backup-pre-restructure`
3. Work on new branch: `git checkout -b feature/professional-structure`

If issues arise:
```bash
git checkout main  # or cleanup/project-structure
git branch -D feature/professional-structure
```

---

## Success Criteria

✅ No duplicate modules (mimesis/ deleted)  
✅ All database files in `src/database/`  
✅ All publishing files in `src/publishing/`  
✅ Services directory has <10 files, all high-level  
✅ Web components use "publishing_" not "mimesis_"  
✅ Zero import errors  
✅ Streamlit UI loads all tabs  
✅ Publishing system can post to all 3 platforms  
✅ Collection/analysis systems still work  

---

## Next Steps

**Ready to execute?** I recommend proceeding phase-by-phase with your approval:

1. Review this plan
2. Execute Phase 1 (mimesis consolidation)
3. Test and verify
4. Proceed to Phase 2 only after Phase 1 success
5. Continue sequentially through all phases

Would you like me to start with Phase 1?
