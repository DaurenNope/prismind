# Prismind Codebase Cleanup Plan

## Current Situation Analysis

### What We Have
```
prismind/
├── src/              (3.2MB) - Active codebase
├── mimesis/          (1.6GB!) - Mostly unused standalone project
├── archive/          (1.4MB) - Old files
├── 16 markdown files in root
└── Multiple duplicate configs
```

### What's Actually Being Used from mimesis/

**ONLY ONE FILE:**
- `mimesis/config/personalities.json` (17KB)

**Everything else (1.6GB) is UNUSED!**

### Current Dependencies

```python
# These 12 files import from src.mimesis:
src/services/publisher_worker.py
src/web/components/mimesis_*.py (5 files)
src/publishing/services/*.py (3 files - just aliases)

# What they import:
from src.mimesis.services.database.bridge import MimesisDB
from src.mimesis.services.transformer import PersonaGenerator
from src.mimesis.services.personalities import get_persona_keys
```

## Cleanup Strategy

### Goals
1. **Professional structure** - Clear, logical organization
2. **No duplicates** - Single source of truth
3. **No dead code** - Remove unused 1.6GB
4. **Clear naming** - No "mimesis_" prefixes everywhere
5. **Proper separation** - Collection, Analysis, Publishing modules

## Phase-by-Phase Cleanup Plan

### Phase 1: Move Config File ✅ SAFE
**Risk: NONE** | **Time: 2 min**

```bash
# Copy the ONE file we need
cp mimesis/config/personalities.json config/

# Update personalities.py to use new location
# Change: Path("mimesis/config/personalities.json")
# To: Path("config/personalities.json")
```

**Test:** Verify personalities still load

---

### Phase 2: Rename src/mimesis → src/publishing ✅ SAFE
**Risk: LOW** | **Time: 10 min**

```bash
# Rename the directory
mv src/mimesis src/publishing

# Update imports (12 files):
# OLD: from src.mimesis.services.database.bridge import MimesisDB
# NEW: from src.publishing.database import PublishingDB

# Files to update:
- src/services/publisher_worker.py
- src/web/components/mimesis_*.py (5 files)
- src/publishing/services/*.py (3 files - delete, redundant)
```

**Test:** Run app, verify publishing tab works

---

### Phase 3: Consolidate Publishing Module ✅ MEDIUM RISK
**Risk: MEDIUM** | **Time: 20 min**

Flatten structure:
```bash
# Before:
src/publishing/
└── services/
    ├── database/bridge.py
    ├── transformer.py
    └── personalities.py

# After:
src/publishing/
├── __init__.py
├── database.py (was database/bridge.py)
├── transformer.py
├── personalities.py
└── posters/
    ├── __init__.py
    ├── twitter.py (move from src/services/)
    ├── telegram.py (extract from publisher_worker)
    └── threads.py (move from src/services/)
```

Update imports:
```python
# OLD
from src.publishing.services.database.bridge import MimesisDB
from src.services.twitter_poster import TwitterPoster

# NEW  
from src.publishing.database import PublishingDB
from src.publishing.posters.twitter import TwitterPoster
```

**Test:** All publishing functionality works

---

### Phase 4: Rename UI Components ✅ MEDIUM RISK
**Risk: MEDIUM** | **Time: 15 min**

```bash
# Rename files:
mv src/web/components/mimesis_overview_tab.py → publishing_overview.py
mv src/web/components/mimesis_queue_tab.py → publishing_queue.py
mv src/web/components/mimesis_editor_tab.py → publishing_editor.py
mv src/web/components/mimesis_scheduler_tab.py → publishing_scheduler.py
mv src/web/components/mimesis_analytics_tab.py → publishing_analytics.py

# Update imports in:
- src/web/components/publishing_page.py
- src/web/app.py (if referenced)
```

**Test:** Publishing tab loads and works

---

### Phase 5: Archive mimesis/ Folder ✅ SAFE
**Risk: NONE** | **Time: 2 min**

```bash
# Move to archive (keep for reference)
mv mimesis archive/mimesis-standalone-backup-$(date +%Y%m%d)

# Or delete if confident:
# rm -rf mimesis
```

**Test:** App still works (nothing should change)

---

### Phase 6: Consolidate Documentation ✅ SAFE
**Risk: NONE** | **Time: 10 min**

```bash
# Current root has 16 .md files!
ls *.md:
CLEANUP_COMPLETE.md
CLEANUP_PLAN.md
IMPLEMENTATION_PLAN.md  
MIMESIS_INTEGRATION_PLAN.md
MIMESIS_INTEGRATION_STATUS.md
POSTING_FIX_SUMMARY.md
README.md
... (9 more)

# Organize:
mkdir -p docs/integration
mv *MIMESIS*.md docs/integration/
mv *CLEANUP*.md docs/integration/
mv *POSTING*.md docs/integration/
mv *IMPLEMENTATION*.md docs/integration/

# Keep in root:
- README.md (main documentation)
- ARCHITECTURE.md (create this - final structure)
```

---

### Phase 7: Clean Up Root Directory ✅ SAFE
**Risk: NONE** | **Time: 5 min**

```bash
# Remove duplicate configs
diff .env mimesis/.env  # If identical, keep .env only

# Remove test files from root
mv test_*.py tests/

# Remove old scripts
mkdir -p scripts/archive
mv old_*.py scripts/archive/
```

---

## Final Professional Structure

```
prismind/
├── README.md                 # Main documentation
├── ARCHITECTURE.md           # System architecture
├── .env                      # Environment config
├── requirements.txt
│
├── config/                   # All configuration
│   ├── personalities.json
│   ├── platform_integrations.json
│   └── collection.json
│
├── src/                      # Main codebase
│   ├── collection/          # Data gathering
│   │   ├── reddit_extractor.py
│   │   ├── twitter_extractor.py
│   │   └── threads_extractor.py
│   │
│   ├── analysis/            # AI analysis
│   │   └── intelligent_content_analyzer.py
│   │
│   ├── publishing/          # Publishing system
│   │   ├── __init__.py
│   │   ├── database.py
│   │   ├── transformer.py
│   │   ├── personalities.py
│   │   └── posters/
│   │       ├── twitter.py
│   │       ├── telegram.py
│   │       └── threads.py
│   │
│   ├── services/            # Shared services
│   │   ├── publisher_worker.py
│   │   ├── supabase_manager.py
│   │   └── database_*.py
│   │
│   ├── storage/             # Database adapters
│   │   └── supabase_adapter.py
│   │
│   └── web/                 # UI
│       ├── app.py
│       └── components/
│           ├── collection_tab.py
│           ├── analysis_tab.py
│           ├── publishing_tab.py      # Main tab
│           ├── publishing_overview.py
│           ├── publishing_queue.py
│           ├── publishing_editor.py
│           ├── publishing_scheduler.py
│           ├── publishing_analytics.py
│           └── unified_feed_tab.py
│
├── scripts/                 # Utility scripts
│   ├── publish_scheduled.py
│   └── archive/
│
├── tests/                   # Test suite
│
├── data/                    # Runtime data
├── logs/                    # Log files
├── migrations/              # DB migrations
│
├── docs/                    # Documentation
│   ├── integration/         # Integration docs
│   ├── api/                 # API docs
│   └── guides/              # User guides
│
└── archive/                 # Historical reference
    └── mimesis-standalone-backup-20251101/
```

## Execution Order

### Do First (Low Risk)
1. ✅ Phase 1: Move config file
2. ✅ Phase 5: Archive mimesis/ folder  
3. ✅ Phase 6: Organize documentation
4. ✅ Phase 7: Clean root directory

### Do Second (Medium Risk, Test After Each)
5. ✅ Phase 2: Rename src/mimesis → src/publishing
6. ✅ Phase 3: Consolidate publishing module
7. ✅ Phase 4: Rename UI components

## Testing Checklist

After EACH phase:
- [ ] App starts: `streamlit run src/web/app.py`
- [ ] Publishing tab loads
- [ ] Can view scheduled posts
- [ ] Can post to Twitter (test)
- [ ] Can post to Telegram (test)
- [ ] Can post to Threads (test)
- [ ] Background worker runs
- [ ] No import errors in console

## Rollback Plan

Each phase is in git:
```bash
# If something breaks:
git status
git diff
git checkout -- path/to/file  # Undo changes
```

Or create a backup before starting:
```bash
cp -r /Users/mac/Documents/Development/prismind /Users/mac/Documents/Development/prismind-backup
```

## Benefits After Cleanup

1. **1.6GB removed** - Massive reduction
2. **Clear structure** - Easy to navigate
3. **No "mimesis" naming** - It's all "publishing" now
4. **Professional organization** - Module-based
5. **Easier maintenance** - Single source of truth
6. **Better onboarding** - New developers understand structure

## Time Estimate

- **Total time**: 60-90 minutes
- **Low risk phases**: 20 minutes
- **Medium risk phases**: 40 minutes  
- **Testing**: 30 minutes

## Ready to Execute?

Start with Phase 1 (safest) and work through systematically, testing after each phase.

Want me to start executing this plan?
