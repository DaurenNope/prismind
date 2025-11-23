# CLEANING TICKET #013: Clean and Organize scripts/ Directory

**Priority:** MEDIUM  
**Status:** OPEN  
**Estimated Time:** 1-2 hours  
**Assignee:** Cleaning Agent

## Problem

The `scripts/` directory contains **168 Python files** (1.6 MB) and needs organization, removal of unused scripts, and consolidation of duplicate functionality.

## Current State

**Location:** `scripts/` directory

**Statistics:**
- **168 Python files** total
- **1.6 MB** total size
- **10 markdown files**
- **10 shell scripts**
- Potentially unused or duplicate scripts

## Impact

- Many scripts may be unused
- Duplicate functionality
- Hard to find the right script
- Clutters directory

## Requirements

Clean and organize `scripts/` directory:
- Remove unused scripts
- Consolidate duplicate scripts
- Organize by category
- Document active scripts
- Remove old/obsolete scripts
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
   - Test each script before considering deletion
   - Verify scripts are not used in automation/CI
   - Check documentation for script references
   - **DO NOT DELETE ANYTHING UNTIL VERIFIED UNUSED**

3. **✅ VERIFY BEFORE DELETION**
   - For each script to delete:
     - Verify it's not referenced anywhere
     - Verify it's not in documentation
     - Verify it's not used in automation
     - Run dry-run first
   - **WHEN IN DOUBT, DON'T DELETE**

### Safety Rules

**NEVER DELETE:**
- Active utility scripts
- Scripts referenced in documentation
- Scripts used in automation
- Entry point scripts

**SAFE TO DELETE:**
- Unused/obsolete scripts
- Duplicate scripts
- Old backup scripts
- Test scripts (if not needed)

## Checkpoints

### Checkpoint 0: Pre-Cleanup Safety
- [ ] **PUSH BACKUP TO GITHUB** (CRITICAL - DO NOT SKIP)
  - Commit all changes: `git add . && git commit -m "Pre-cleanup backup"`
  - Push to main: `git push origin main`
  - Create backup branch: `git branch backup-before-scripts-cleanup-$(date +%Y%m%d)`
  - Push backup branch: `git push origin backup-before-scripts-cleanup-$(date +%Y%m%d)`
- [ ] **DOCUMENT CURRENT STATE**
  - List all scripts
  - Document which scripts are known to be used
  - Take snapshot of directory structure

### Checkpoint 1: Categorize Scripts
- [ ] List all scripts
- [ ] Categorize by purpose:
  - Collection scripts
  - Analysis scripts
  - Publishing scripts
  - Utility scripts
  - Test scripts
  - Migration scripts
- [ ] Identify entry points

### Checkpoint 2: Identify Unused Scripts
- [ ] Check for scripts not referenced anywhere
- [ ] Check for scripts not in documentation
- [ ] Check for old/obsolete scripts
- [ ] Generate report

### Checkpoint 3: Identify Duplicates
- [ ] Find duplicate functionality
- [ ] Identify which to keep
- [ ] Document duplicates

### Checkpoint 4: Organize Structure (SUPER WELL ORGANIZED)
- [ ] **PLAN STRUCTURE FIRST**: Design perfect folder organization
  - Each subdirectory should have clear purpose
  - Group related scripts together
  - Create logical hierarchy
- [ ] Create subdirectories by category:
  - `scripts/collection/`
  - `scripts/analysis/`
  - `scripts/publishing/`
  - `scripts/utilities/`
  - `scripts/migrations/`
- [ ] Move scripts to appropriate directories
- [ ] Update references if needed
- [ ] **VERIFY STRUCTURE IS PERFECT**: Review organization - must be super well organized

### Checkpoint 5: Remove Unused Scripts
- [ ] Remove unused scripts (after verification)
- [ ] Remove duplicate scripts
- [ ] Remove obsolete scripts
- [ ] Log each removal

### Checkpoint 6: Document Active Scripts
- [ ] Create `scripts/README.md`
- [ ] Document each active script
- [ ] Include usage examples
- [ ] List entry points

### Checkpoint 7: Generate Report
- [ ] Generate cleanup report
- [ ] Document scripts removed
- [ ] Document scripts organized
- [ ] Save report

## Acceptance Criteria

- [ ] **GITHUB BACKUP CREATED** (MANDATORY)
- [ ] Scripts organized by category
- [ ] **Structure SUPER WELL ORGANIZED** (MANDATORY - must be perfect)
- [ ] Unused scripts removed (after verification)
- [ ] Duplicates consolidated
- [ ] Active scripts documented
- [ ] No broken references
- [ ] **ALL SCRIPTS TESTED** (MANDATORY)
- [ ] Cleanup report generated

## Related Issues

- General codebase organization

## Notes

- Be careful not to delete scripts in active use
- Check documentation and automation for references
- Keep entry point scripts in root of scripts/
- Significant organization improvement possible

## Success Metrics

- **Target:** 20+ unused scripts identified
- **Target:** Scripts organized into categories
- **Target:** Active scripts documented
- **Target:** Cleaner, more navigable scripts directory

