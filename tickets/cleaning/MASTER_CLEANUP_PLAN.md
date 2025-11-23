# Master Cleanup Plan

**Created:** 2025-11-23  
**Status:** ACTIVE  
**Total Estimated Time:** ~6-8 hours  
**Priority:** HIGH

## Overview

This is a comprehensive cleanup plan to drastically reduce file clutter and organize the codebase. The codebase currently has **16,653 files** with significant cleanup opportunities.

## Current State Analysis

### File Counts
- **Total files:** 16,653
- **Python cache files:** 6,924 .pyc files
- **Cache directories:** 64+ __pycache__ directories
- **Documentation files:** 258 markdown files (2.3 MB)
- **Log/trace files:** 916+ files (5.0 MB)
- **Backup files:** Multiple (8.7 MB)
- **var/ directory:** 744 KB
- **Empty directories:** 10+ found

### Disk Space
- **docs/:** 2.3 MB
- **logs/:** 5.0 MB
- **backups/:** 8.7 MB
- **var/:** 744 KB
- **Total:** ~16.7 MB (and growing)

## Cleanup Tickets

### Phase 1: Critical Cleanup (HIGH Priority)

#### Ticket #006: Comprehensive Python Cache Cleanup
- **Priority:** HIGH
- **Time:** 30 minutes
- **Impact:** Remove 6,924 .pyc files + 64 __pycache__ directories
- **Space Savings:** 50-100+ MB
- **Status:** OPEN

#### Ticket #007: Clean Log and Trace Files
- **Priority:** HIGH
- **Time:** 45 minutes
- **Impact:** Clean 916+ log/trace files
- **Space Savings:** 2+ MB
- **Status:** OPEN

### Phase 2: Organization (MEDIUM Priority)

#### Ticket #010: Comprehensive Documentation Cleanup
- **Priority:** MEDIUM
- **Time:** 2 hours
- **Impact:** Archive 100+ docs, remove duplicates
- **Space Savings:** 2+ MB
- **Status:** OPEN

#### Ticket #009: Clean var/ and data/ Directories
- **Priority:** MEDIUM
- **Time:** 1 hour
- **Impact:** Clean runtime files and cached data
- **Space Savings:** 500+ KB
- **Status:** OPEN

#### Ticket #008: Clean Empty Directories
- **Priority:** MEDIUM
- **Time:** 20 minutes
- **Impact:** Remove 10+ empty directories
- **Space Savings:** Minimal (organizational)
- **Status:** OPEN

### Phase 3: Final Cleanup (LOW Priority)

#### Ticket #011: Clean Temporary Files
- **Priority:** LOW
- **Time:** 30 minutes
- **Impact:** Remove .tmp, .bak, .swp, etc.
- **Space Savings:** Variable
- **Status:** OPEN

## Execution Plan

### Week 1: Critical Cleanup
1. **Day 1:** Ticket #006 (Python Cache) - 30 min
2. **Day 1:** Ticket #007 (Log/Trace Files) - 45 min
3. **Day 2:** Verify Phase 1 completion

### Week 2: Organization
4. **Day 3:** Ticket #010 (Documentation) - 2 hours
5. **Day 4:** Ticket #009 (var/data) - 1 hour
6. **Day 5:** Ticket #008 (Empty Dirs) - 20 min
7. **Day 6:** Verify Phase 2 completion

### Week 3: Final Cleanup
8. **Day 7:** Ticket #011 (Temporary Files) - 30 min
9. **Day 8:** Final verification and report

## Success Metrics

### Phase 1 Targets
- ✅ Remove all 6,924 .pyc files
- ✅ Remove all 64 __pycache__ directories
- ✅ Clean 916+ log/trace files
- ✅ Free 50+ MB disk space

### Phase 2 Targets
- ✅ Archive 100+ documentation files
- ✅ Remove 10+ duplicate docs
- ✅ Clean var/ and data/ directories
- ✅ Remove empty directories
- ✅ Free 2+ MB additional space

### Phase 3 Targets
- ✅ Remove all temporary files
- ✅ Final verification
- ✅ Generate comprehensive report

## Total Expected Results

- **Files Removed:** 7,000+ files
- **Directories Cleaned:** 100+ directories
- **Disk Space Freed:** 55+ MB
- **Documentation Organized:** 100+ files archived
- **Codebase Cleanliness:** Significantly improved

## ⚠️ CRITICAL SAFETY RULES

### MANDATORY: Before ANY Cleanup

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
- Perfect organization is mandatory

## Reporting

After each ticket:
- Generate cleanup report
- Update master plan status
- Document space savings
- Note any issues

Final report will include:
- Total files removed
- Total space freed
- Organization improvements
- Remaining cleanup opportunities

## Maintenance Schedule

### Weekly
- Clean Python cache
- Rotate logs (if needed)

### Monthly
- Archive completed documentation
- Clean old backups
- Clean var/ and data/ directories

### Quarterly
- Comprehensive cleanup (all tickets)
- Review and update cleanup plan
- Generate maintenance report

## Notes

- All operations are safe (archive before delete)
- Dry-run mode available for testing
- Reports generated after each cleanup
- Can be run on schedule
- Files can be restored from archive if needed
- Significant disk space savings possible
- Codebase will be much cleaner after completion

