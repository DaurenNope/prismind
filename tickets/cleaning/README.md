# Cleaning Agent Tickets

This directory contains tickets for the Cleaning Agent to maintain a clean and organized codebase.

## ⚠️ CRITICAL: READ BEFORE STARTING

**BEFORE EXECUTING ANY CLEANUP TICKET:**

1. **✅ PUSH BACKUP TO GITHUB** (MANDATORY)
   - Commit all changes and push to GitHub
   - Create backup branch before starting
   - **DO NOT PROCEED WITHOUT GITHUB BACKUP**

2. **✅ TEST EVERYTHING** (MANDATORY)
   - Run full test suite before cleanup
   - Test application after cleanup
   - **DO NOT DELETE ANYTHING UNTIL TESTS PASS**

3. **✅ FOLDERS MUST BE SUPER WELL ORGANIZED**
   - Perfect organization is required
   - Follow best practices
   - Create logical hierarchy

See [Safety Rules](#-critical-safety-rules-mandatory) below for details.

## Ticket Index

1. **[001: Archive Completed Documentation](./001-archive-completed-documentation.md)** - MEDIUM, 1 hour
   - Archive completed status reports to `docs/archive/completed/`
   - Safe operation (archive, not delete)
   - ~50-100 files to archive

2. **[002: Rotate Log Files](./002-rotate-log-files.md)** - MEDIUM, 30 min
   - Keep last 7 days, archive 7-30 days, delete >30 days
   - Compress archived logs
   - Clean JSON trace files and PNG files

3. **[003: Clean Backup Files](./003-clean-backup-files.md)** - MEDIUM, 30 min
   - Keep last 3 database backups
   - Clean JSON backups older than 30 days
   - Manage environment backups

4. **[004: Clean Python Cache](./004-clean-python-cache.md)** - LOW, 15 min
   - Remove `__pycache__/` directories and `.pyc` files
   - Very safe (regenerates automatically)
   - Can free significant disk space

5. **[005: Identify Deprecated Code](./005-identify-deprecated-code.md)** - LOW, 1 hour
   - Report deprecated code for manual review
   - No auto-removal (reporting only)
   - Creates removal tickets for high-priority items

## Comprehensive Cleanup Tickets (NEW)

6. **[006: Comprehensive Python Cache Cleanup](./006-comprehensive-python-cache-cleanup.md)** - ✅ COMPLETE
   - Script executed: `clean_python_cache.py` ✅
   - Removed 796 __pycache__ directories, freed 103.77 MB ✅
   - Re-executed 2025-11-23 ✅

7. **[007: Clean Log and Trace Files](./007-clean-log-trace-files.md)** - HIGH, 45 min
   - Clean 916+ log/trace files
   - Archive old logs (7-30 days)
   - Delete very old logs (>30 days)
   - Clean JSON trace files and PNG screenshots
   - **Target: 2+ MB freed**

8. **[008: Clean Empty Directories](./008-clean-empty-directories.md)** - MEDIUM, 20 min
   - Remove 10+ empty directories
   - Organize directory structure
   - **Target: Cleaner structure**

9. **[009: Clean var/ and data/ Directories](./009-clean-var-and-data-directories.md)** - MEDIUM, 1 hour
   - Clean runtime files in var/
   - Clean cached data in data/
   - Archive old files (30-90 days)
   - Delete very old files (>90 days)
   - **Target: 500+ KB freed**

10. **[010: Comprehensive Documentation Cleanup](./010-comprehensive-documentation-cleanup.md)** - MEDIUM, 2 hours
    - Archive 100+ documentation files
    - Remove duplicate documentation
    - Organize by category
    - Create documentation index
    - **Target: 2+ MB freed, organized docs/**

11. **[011: Clean Temporary Files](./011-clean-temporary-files.md)** - LOW, 30 min
    - Remove .tmp, .bak, .swp, *~ files
    - Remove .DS_Store, Thumbs.db
    - **Target: Variable space savings**

## Folder-by-Folder Organization Tickets (NEW)

12. **[012: Clean and Organize src/ Directory](./012-clean-and-organize-src-directory.md)** - ✅ COMPLETE
    - Script executed: `organize_src_directory.py` ✅
    - Result: No files to organize (already well organized) ✅
    - Status: Directory is clean and organized ✅

13. **[013: Clean and Organize scripts/ Directory](./013-clean-and-organize-scripts-directory.md)** - MEDIUM, 1-2 hours
    - Organize 168 Python files (1.6 MB)
    - Remove unused scripts, consolidate duplicates
    - Organize by category, document active scripts
    - **Target: Cleaner, more navigable scripts directory**

14. **[014: Clean and Organize tests/ Directory](./014-clean-and-organize-tests-directory.md)** - ✅ COMPLETE
    - Script executed: `organize_tests.py` ✅
    - Result: 0 files to move (already organized) ✅
    - Status: Tests properly organized ✅

15. **[015: Clean and Organize config/ Directory](./015-clean-and-organize-config-directory.md)** - LOW, 30 min
    - Organize configuration files
    - Remove duplicates, unused configs
    - Organize by category, document configs
    - **Target: Cleaner, more navigable config directory**

16. **[016: Clean and Organize Root Directory](./016-clean-and-organize-root-directory.md)** - MEDIUM, 1 hour
    - Keep only essential files in root
    - Move other files to appropriate locations
    - Remove duplicates, organize structure
    - **Target: Professional, minimal root directory**

## Master Plan

📋 **[MASTER_CLEANUP_PLAN.md](./MASTER_CLEANUP_PLAN.md)** - Comprehensive cleanup strategy and execution plan

## ⚠️ CRITICAL SAFETY RULES (MANDATORY)

### BEFORE ANY CLEANUP - DO THESE FIRST:

1. **✅ PUSH BACKUP TO GITHUB (REQUIRED)**
   ```bash
   # Commit all changes
   git add .
   git commit -m "Pre-cleanup backup"
   
   # Push to main
   git push origin main
   
   # Create backup branch
   git branch backup-before-cleanup-$(date +%Y%m%d)
   git push origin backup-before-cleanup-$(date +%Y%m%d)
   ```
   - **DO NOT PROCEED WITHOUT GITHUB BACKUP**
   - This allows easy rollback if something goes wrong

2. **✅ TEST EVERYTHING BEFORE DELETION (REQUIRED)**
   ```bash
   # Run full test suite
   pytest tests/  # or python -m pytest
   
   # Run application
   python main.py  # or main entry point
   
   # Verify imports
   python -c "import src"
   ```
   - **DO NOT DELETE ANYTHING UNTIL TESTS PASS**
   - Document test results before cleanup
   - Run tests after each major change

3. **✅ VERIFY BEFORE DELETION (REQUIRED)**
   - For each file/directory to delete:
     - Verify it's not imported anywhere
     - Verify it's not referenced in documentation
     - Verify it's not used in automation/CI
     - Run dry-run first
   - **WHEN IN DOUBT, DON'T DELETE**

### Never Delete
- Source code files (`.py`) - unless verified unused
- Configuration files (`.json`, `.yaml`, `.toml`) - unless verified unused
- Database files (`.db`, `.sqlite`) - unless old backups
- Active documentation
- Recent backups/logs
- Migration files
- Files in protected directories (`.git/`, `node_modules/`, `.venv/`)

### Always Archive Before Delete
- Move files to archive directories
- Preserve file structure
- Compress archives to save space
- Create archive indexes

### Always Dry-Run First
- Test cleanup rules before applying
- Review what would be cleaned
- Verify no critical files affected
- Get approval for destructive operations

### Organization Requirements
- **FOLDERS MUST BE SUPER WELL ORGANIZED**
- Each directory should have clear purpose
- Follow best practices for project structure
- Create logical hierarchy
- Perfect organization is mandatory for folder-by-folder tickets

## Priority Order

### Phase 1: Critical Cleanup (HIGH Priority)
1. **Ticket #006: Comprehensive Python Cache Cleanup** (HIGH, 30 min) - Remove 6,924 .pyc files + 64 directories
2. **Ticket #007: Clean Log and Trace Files** (HIGH, 45 min) - Clean 916+ files, free 2+ MB

### Phase 2: Organization (MEDIUM Priority)
3. **Ticket #010: Comprehensive Documentation Cleanup** (MEDIUM, 2 hours) - Archive 100+ docs, organize
4. **Ticket #009: Clean var/ and data/ Directories** (MEDIUM, 1 hour) - Clean runtime/cached data
5. **Ticket #008: Clean Empty Directories** (MEDIUM, 20 min) - Remove empty dirs

### Phase 3: Final Cleanup (LOW Priority)
6. **Ticket #011: Clean Temporary Files** (LOW, 30 min) - Remove .tmp, .bak, etc.

### Phase 4: Folder-by-Folder Organization (NEW)
7. **Ticket #012: Clean and Organize src/ Directory** (HIGH, 2-3 hours) - Clean 496 Python files
8. **Ticket #013: Clean and Organize scripts/ Directory** (MEDIUM, 1-2 hours) - Organize 168 scripts
9. **Ticket #014: Clean and Organize tests/ Directory** (MEDIUM, 1-2 hours) - Organize 131 tests
10. **Ticket #015: Clean and Organize config/ Directory** (LOW, 30 min) - Organize configs
11. **Ticket #016: Clean and Organize Root Directory** (MEDIUM, 1 hour) - Minimal root

### Legacy Tickets (Previous Work)
- **Ticket #001:** Archive Completed Documentation (partially complete)
- **Ticket #002:** Rotate Log Files (completed - no action needed)
- **Ticket #003:** Clean Backup Files (completed - no action needed)
- **Ticket #004:** Clean Python Cache (partially complete - needs comprehensive cleanup)
- **Ticket #005:** Identify Deprecated Code (completed)

## Total Estimated Time

- **Phase 1 (Critical):** ~1.25 hours
- **Phase 2 (Organization):** ~3.5 hours
- **Phase 3 (Final):** ~0.5 hours
- **Phase 4 (Folder Organization):** ~6-8 hours
- **Total: ~13-15 hours** (all phases)
- **Legacy tickets:** ~3.5 hours (mostly complete)

## Cleanup Schedule

### Weekly: Light Cleanup
- Clean Python cache
- Rotate logs (if needed)
- Quick backup check

### Monthly: Documentation & Backups
- Archive completed documentation
- Clean old backups
- Full log rotation

### Quarterly: Comprehensive Cleanup
- All cleanup tasks
- Deprecated code identification
- Full report generation

## Current State

### File Counts
- **Total files:** 16,653
- **Python cache:** 6,924 .pyc files + 64 __pycache__ directories
- **Documentation:** 258 markdown files (2.3 MB)
- **Log/trace files:** 916+ files (5.0 MB)
- **Backup files:** 8.7 MB
- **var/ directory:** 744 KB

### Expected Results
- **Files to remove:** 7,000+ files
- **Disk space to free:** 55+ MB
- **Documentation to archive:** 100+ files
- **Codebase cleanliness:** Significantly improved
- **Folder organization:** All major directories cleaned and organized
- **Code quality:** Unused code removed, duplicates consolidated

## Notes

- All cleaning operations are safe (archive before delete)
- Dry-run mode available for testing
- Reports generated after each cleanup
- Can be run on schedule (weekly/monthly)
- Files can be restored from archive if needed
- **Significant disk space savings possible (55+ MB)**
- **Comprehensive cleanup will drastically improve codebase organization**

## Related Documentation

- [CLEANUP_RULES.md](../../docs/CLEANUP_RULES.md) - Detailed cleanup rules
- [CLEANUP_PROCESS.md](../../docs/CLEANUP_PROCESS.md) - How to use cleanup system

