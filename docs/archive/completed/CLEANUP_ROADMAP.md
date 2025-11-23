# Prismind Cleanup Roadmap

**Last Updated:** 2025-11-20  
**Status:** Phase 3 Complete ✅

---

## ✅ Completed Phases

### Phase 1: Root Directory Cleanup ✅
- **Status:** Complete
- **What was done:**
  - Moved 21 test files to `tests/`
  - Moved 13 utility scripts to `scripts/`
  - Moved 5 completed docs to `docs/archive/completed/`
  - Moved 8 planning docs to `docs/plans/`
  - Moved 6 `.env` backups to `backups/env_backups/`
  - Moved frontend files to `frontend/`
  - Moved Twitter docs to `docs/twitter/`
  - Moved database files to `backups/`
  - Moved data directories to `data/`
- **Impact:** Root directory significantly cleaner

### Phase 2: Scripts Directory Organization ✅
- **Status:** Complete
- **What was done:**
  - Organized 130+ scripts into logical subdirectories
  - Reduced to 76 active scripts (41% reduction)
  - Created `scripts/SCRIPT_INVESTIGATION_REPORT.md`
  - Archived 56 obsolete/one-time scripts
- **Impact:** Much easier to find and understand scripts

### Phase 3: Code Quality Improvements ✅
- **Status:** Complete
- **What was done:**
  - Removed unused imports from 50+ files
  - Standardized import ordering with isort
  - Fixed duplicate imports
  - Fixed logical inconsistencies (8 files):
    - Unreachable code removed
    - Missing logger imports added
    - Exception variable fixes
    - Duplicate logger definitions removed
    - Inconsistent logger usage fixed
- **Impact:** Cleaner, more maintainable code

---

## 📋 Remaining Phases

### Phase 4: Large Files Refactoring
**Status:** Pending  
**Risk Level:** Medium  
**Priority:** Medium

**Goal:** Split monolithic files into smaller, focused modules

**Files to refactor:**
1. `src/core/extraction/twitter_extractor_playwright.py` - **4,746 lines**
   - Split into: authentication, extraction, parsing, error handling
2. `src/core/extraction/threads_extractor.py` - **3,458 lines**
   - Split into: extraction, parsing, media handling
3. `src/core/analysis/intelligent_content_analyzer.py` - **2,804 lines**
   - Split into: analysis, scoring, categorization
4. `src/publishing/platforms/telegram/bot.py` - **2,394 lines**
   - Split into: bot setup, commands, handlers, utilities

**Approach:**
- Document current structure first
- Identify logical boundaries
- Extract into separate modules
- Update imports gradually
- Test after each split

---

### Phase 5: Configuration Cleanup
**Status:** Pending  
**Risk Level:** Low  
**Priority:** Medium

**Goal:** Standardize configuration file locations and structure

**Tasks:**
1. **Cookie file locations:**
   - Currently: Multiple locations (`config/`, `cookies/`, env vars)
   - Standardize to: `config/cookies/` or single location
   - Update all references

2. **Config file review:**
   - Audit all config files in `config/`
   - Identify duplicates or redundant configs
   - Consolidate where possible

3. **Environment variables:**
   - Document all required env vars
   - Create `.env.example` template
   - Verify all are used

---

### Phase 6: Database Manager Consolidation
**Status:** Pending  
**Risk Level:** Low (audit only)  
**Priority:** Low

**Goal:** Audit and document usage of multiple database managers

**Current managers:**
- `DatabaseAgent` - Centralized operations layer
- `SupabaseManager` - Supabase-specific operations
- `NewDatabaseManager` - New database interface
- `StorageFacade` - Storage abstraction
- `SupabaseAdapter` - Supabase adapter
- `SQLiteAdapter` - SQLite adapter
- `DatabaseOperations` - Basic CRUD operations

**Tasks:**
1. Document what each manager does
2. Map usage across codebase
3. Identify consolidation opportunities
4. Create migration plan (if needed)

**Note:** This is an audit/documentation phase. Actual consolidation would be Phase 6.5 if needed.

---

### Phase 7: Deprecated Code Migration - ContentRewriter
**Status:** Pending  
**Risk Level:** High  
**Priority:** Medium

**Goal:** Migrate from deprecated `ContentRewriter` to `ModularRewriter`

**Current state:**
- `ContentRewriter` is deprecated (3,187 lines)
- `ModularRewriter` is the new implementation
- **22 files** still use `ContentRewriter`

**Files to migrate:**
- `src/publishing/platforms/telegram/agents.py`
- `src/publishing/platforms/telegram/bot.py`
- `scripts/analysis/production_content_pipeline.py`
- `scripts/publishing/*.py` (multiple scripts)
- And 17 more files...

**Approach:**
1. Test `ModularRewriter` thoroughly
2. Migrate one file at a time
3. Test after each migration
4. Update scripts last
5. Archive `ContentRewriter` after all migrations

---

### Phase 8: Deprecated Code Migration - AutonomousDiscovery
**Status:** Pending  
**Risk Level:** Medium  
**Priority:** Low

**Goal:** Replace `AutonomousDiscovery` with orchestrator methods

**Current state:**
- `AutonomousDiscovery` is deprecated
- Should be integrated into `Orchestrator`
- **5 files** still use it

**Files to migrate:**
- `src/pipeline/orchestrator.py` (already has deprecation warning)
- `scripts/collection/run_full_collection.py`
- And 3 more files...

**Approach:**
1. Implement discovery logic in `Orchestrator`
2. Update one file at a time
3. Test after each update
4. Archive `AutonomousDiscovery` after migration

---

## 📊 Summary

### Completed: 3/8 Phases (37.5%)
- ✅ Phase 1: Root Directory Cleanup
- ✅ Phase 2: Scripts Organization
- ✅ Phase 3: Code Quality

### Remaining: 5 Phases
- ⏳ Phase 4: Large Files Refactoring (Medium risk, Medium priority)
- ⏳ Phase 5: Configuration Cleanup (Low risk, Medium priority)
- ⏳ Phase 6: Database Manager Audit (Low risk, Low priority)
- ⏳ Phase 7: ContentRewriter Migration (High risk, Medium priority)
- ⏳ Phase 8: AutonomousDiscovery Migration (Medium risk, Low priority)

---

## 🎯 Recommended Next Steps

**Option 1: Low Risk Path (Recommended)**
1. **Phase 5:** Configuration Cleanup (Low risk, quick wins)
2. **Phase 6:** Database Manager Audit (Documentation only)
3. **Phase 4:** Large Files Refactoring (Medium risk, but well-defined)

**Option 2: High Impact Path**
1. **Phase 4:** Large Files Refactoring (Biggest impact on maintainability)
2. **Phase 5:** Configuration Cleanup (Clean up after refactoring)
3. **Phase 7:** ContentRewriter Migration (Remove deprecated code)

**Option 3: Deprecated Code First**
1. **Phase 7:** ContentRewriter Migration (Remove 3,187 lines of deprecated code)
2. **Phase 8:** AutonomousDiscovery Migration (Complete deprecation cleanup)
3. **Phase 4:** Large Files Refactoring (Then refactor what's left)

---

## 📝 Notes

- All phases are independent and can be done in any order
- Phases 5 and 6 are low risk and can be done anytime
- Phases 7 and 8 remove deprecated code, reducing technical debt
- Phase 4 has the biggest impact on code maintainability
- Each phase should be tested thoroughly before moving to the next






