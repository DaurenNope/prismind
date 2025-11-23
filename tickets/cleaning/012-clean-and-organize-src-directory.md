# CLEANING TICKET #012: Clean and Organize src/ Directory

**Priority:** HIGH  
**Status:** OPEN  
**Estimated Time:** 2-3 hours  
**Assignee:** Cleaning Agent

## Problem

The `src/` directory contains **496 Python files** (10 MB) and needs organization, cleanup of unused code, and consolidation of duplicate functionality.

## Current State

**Location:** `src/` directory

**Statistics:**
- **496 Python files** total
- **10 MB** total size
- **25 `__pycache__` directories** (need cleanup)
- **105 `.pyc` files** (need cleanup)
- Multiple subdirectories with potential duplicates

**Subdirectories:**
- `src/agents/` - AI agents
- `src/api/` - API endpoints
- `src/core/` - Core business logic
- `src/database/` - Database operations
- `src/domain/` - Domain logic
- `src/infrastructure/` - Infrastructure code
- `src/observability/` - Observability tools
- `src/pipeline/` - Pipeline orchestration
- `src/publishing/` - Publishing system
- `src/services/` - Service layer
- `src/shared/` - Shared utilities
- `src/storage/` - Storage adapters
- And more...

## Impact

- Large codebase makes navigation difficult
- Potential duplicate code
- Unused imports and dead code
- Cache files waste space
- Hard to maintain and understand

## Requirements

Clean and organize `src/` directory:
- Remove all cache files (`__pycache__`, `.pyc`)
- Identify and remove unused/dead code
- Consolidate duplicate functionality
- Organize imports
- Remove unused dependencies
- Document structure
- **SUPER WELL ORGANIZED** - Folders must be perfectly structured

## ⚠️ CRITICAL SAFETY REQUIREMENTS

**BEFORE STARTING ANY CLEANUP:**

1. **✅ PUSH BACKUP TO GITHUB**
   - Commit all current changes
   - Push to GitHub: `git push origin main` (or current branch)
   - Create backup branch: `git branch backup-before-cleanup-YYYYMMDD`
   - Push backup branch: `git push origin backup-before-cleanup-YYYYMMDD`
   - **DO NOT PROCEED WITHOUT GITHUB BACKUP**

2. **✅ TEST EVERYTHING BEFORE DELETION**
   - Run full test suite: `pytest tests/` or `python -m pytest`
   - Run application: `python main.py` (or main entry point)
   - Verify all imports work: `python -c "import src"`
   - Test critical functionality
   - **DO NOT DELETE ANYTHING UNTIL TESTS PASS**

3. **✅ VERIFY BEFORE DELETION**
   - For each file/directory to delete:
     - Verify it's not imported anywhere
     - Verify it's not referenced in documentation
     - Verify it's not used in automation/CI
     - Run dry-run first
   - **WHEN IN DOUBT, DON'T DELETE**

### Safety Rules

**NEVER DELETE:**
- Active source code files
- Configuration files
- Migration files
- Test files (unless duplicates)
- Files referenced in imports

**SAFE TO DELETE:**
- Cache files (`__pycache__`, `.pyc`, `.pyo`, `.pyd`)
- Unused/duplicate files (after verification)
- Dead code (after verification)

## Checkpoints

### Checkpoint 0: Pre-Cleanup Safety
- [ ] **PUSH BACKUP TO GITHUB** (CRITICAL - DO NOT SKIP)
  - Commit all changes: `git add . && git commit -m "Pre-cleanup backup"`
  - Push to main: `git push origin main`
  - Create backup branch: `git branch backup-before-src-cleanup-$(date +%Y%m%d)`
  - Push backup branch: `git push origin backup-before-src-cleanup-$(date +%Y%m%d)`
- [ ] **RUN FULL TEST SUITE** (CRITICAL - DO NOT SKIP)
  - Run: `pytest tests/` or `python -m pytest`
  - Verify all tests pass
  - Document any failing tests
- [ ] **VERIFY APPLICATION WORKS**
  - Run: `python main.py` (or main entry point)
  - Verify application starts successfully
  - Test critical functionality
- [ ] **VERIFY IMPORTS**
  - Run: `python -c "import src; print('Imports OK')"`
  - Check for import errors
- [ ] **DOCUMENT CURRENT STATE**
  - List all files in `src/`
  - Document current structure
  - Take snapshot of directory tree

### Checkpoint 1: Remove Cache Files
- [ ] Remove all `__pycache__` directories in `src/`
- [ ] Remove all `.pyc` files in `src/`
- [ ] Remove all `.pyo` files in `src/`
- [ ] Remove all `.pyd` files in `src/`
- [ ] Verify no cache files remain
- [ ] **TEST AFTER CACHE REMOVAL**: Run tests to ensure nothing broke

### Checkpoint 2: Identify Unused Files
- [ ] Scan for files with no imports
- [ ] Identify files not referenced anywhere
- [ ] Check for duplicate functionality
- [ ] Generate report of potentially unused files

### Checkpoint 3: Identify Dead Code
- [ ] Find unused functions/classes
- [ ] Find unused imports
- [ ] Find commented-out code blocks
- [ ] Generate report

### Checkpoint 4: Consolidate Duplicates
- [ ] Find duplicate functions/classes
- [ ] Identify which to keep
- [ ] Update imports to use consolidated version
- [ ] **TEST AFTER EACH CONSOLIDATION**: Run tests to ensure nothing broke
- [ ] Remove duplicates (only after tests pass)
- [ ] **VERIFY NO BROKEN IMPORTS**: Check all imports still work

### Checkpoint 5: Organize Structure (SUPER WELL ORGANIZED)
- [ ] **PLAN STRUCTURE FIRST**: Design perfect folder organization
  - Each subdirectory should have clear purpose
  - Follow Python package best practices
  - Group related functionality together
  - Create logical hierarchy
- [ ] Verify directory structure makes sense
- [ ] Move misplaced files to correct locations
- [ ] Ensure consistent naming conventions
- [ ] Update imports if files moved
- [ ] **TEST AFTER EACH MOVE**: Run tests to ensure imports still work
- [ ] **VERIFY STRUCTURE IS PERFECT**: Review organization - must be super well organized

### Checkpoint 6: Clean Imports
- [ ] Remove unused imports
- [ ] Organize imports (stdlib, third-party, local)
- [ ] Fix circular imports if any
- [ ] Verify all imports work

### Checkpoint 7: Generate Report
- [ ] Generate cleanup report
- [ ] Document files removed
- [ ] Document files consolidated
- [ ] Document structure changes
- [ ] Save report to `docs/cleanup_reports/src_cleanup_YYYYMMDD_HHMMSS.json`

## Acceptance Criteria

- [ ] **GITHUB BACKUP CREATED** (MANDATORY)
- [ ] **ALL TESTS PASS** (MANDATORY)
- [ ] All cache files removed from `src/`
- [ ] Unused files identified and removed (after verification)
- [ ] Dead code removed (after verification)
- [ ] Duplicates consolidated
- [ ] Imports cleaned
- [ ] **Structure SUPER WELL ORGANIZED** (MANDATORY - must be perfect)
- [ ] No broken imports
- [ ] **FINAL TEST SUITE PASSES** (MANDATORY)
- [ ] **APPLICATION WORKS** (MANDATORY)
- [ ] Cleanup report generated

## Safety Exclusions

**Files to NEVER delete:**
- Source `.py` files (unless verified unused)
- `__init__.py` files
- Configuration files
- Files in active use

## Related Issues

- Cleaning Ticket #006: Comprehensive Python Cache Cleanup (cache removal part)

## Notes

- This is a complex task requiring careful verification
- Run tests after cleanup to ensure nothing breaks
- Keep backups before major changes
- Document all changes
- Significant space savings possible

## Success Metrics

- **Target:** 0 cache files in `src/`
- **Target:** 10+ unused files identified
- **Target:** 5+ duplicate functions consolidated
- **Target:** Cleaner, more maintainable codebase

