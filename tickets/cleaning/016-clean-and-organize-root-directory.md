# CLEANING TICKET #016: Clean and Organize Root Directory

**Priority:** MEDIUM  
**Status:** OPEN  
**Estimated Time:** 1 hour  
**Assignee:** Cleaning Agent

## Problem

The root directory may contain files that should be organized into appropriate subdirectories, duplicate files, or unnecessary clutter.

## Current State

**Location:** Root directory (`/`)

**Files Found:**
- `main.py` - Main entry point ✅
- `README.md` - Project documentation ✅
- `HOW_TO_RUN.md` - Setup guide ✅
- `pyproject.toml` - Project config ✅
- `pytest.ini` - Test config ✅
- `requirements.txt` - Dependencies ✅
- `requirements_frontend.txt` - Frontend dependencies ✅
- `docker-compose.yml` - Docker config ✅
- `mcp.json` - MCP config ✅
- `beyondlines.db` - Database file
- And potentially more...

## Impact

- Root directory should be minimal
- Only essential files should be in root
- Other files should be organized
- Makes project look unprofessional

## Requirements

Clean and organize root directory:
- Keep only essential files in root
- Move other files to appropriate locations
- Remove duplicate files
- Organize structure
- Document what stays in root
- **SUPER WELL ORGANIZED** - Root must be minimal and perfect

## ⚠️ CRITICAL SAFETY REQUIREMENTS

**BEFORE STARTING ANY CLEANUP:**

1. **✅ PUSH BACKUP TO GITHUB**
   - Commit all current changes
   - Push to GitHub: `git push origin main` (or current branch)
   - Create backup branch: `git branch backup-before-cleanup-YYYYMMDD`
   - Push backup branch: `git push origin backup-before-cleanup-YYYYMMDD`
   - **DO NOT PROCEED WITHOUT GITHUB BACKUP**

2. **✅ TEST EVERYTHING BEFORE DELETION**
   - Run application: `python main.py` (or main entry point)
   - Run test suite: `pytest tests/` or `python -m pytest`
   - Verify all imports work
   - Test critical functionality
   - **DO NOT DELETE ANYTHING UNTIL VERIFIED UNUSED**

3. **✅ VERIFY BEFORE DELETION**
   - For each file to delete:
     - Verify it's not referenced anywhere
     - Verify it's not in documentation
     - Verify it's not used in automation/CI
   - **WHEN IN DOUBT, DON'T DELETE**

### Safety Rules

**KEEP IN ROOT:**
- `main.py` - Entry point
- `README.md` - Main documentation
- `pyproject.toml` - Project config
- `pytest.ini` - Test config
- `requirements.txt` - Dependencies
- `docker-compose.yml` - Docker config
- `.gitignore` - Git config
- Essential config files

**MOVE TO SUBDIRECTORIES:**
- Database files (to `data/` or `var/`)
- Documentation files (to `docs/`)
- Script files (to `scripts/`)
- Test files (to `tests/`)
- Config files (to `config/`)

**SAFE TO DELETE:**
- Duplicate files
- Old backup files
- Temporary files

## Checkpoints

### Checkpoint 0: Pre-Cleanup Safety
- [ ] **PUSH BACKUP TO GITHUB** (CRITICAL - DO NOT SKIP)
  - Commit all changes: `git add . && git commit -m "Pre-cleanup backup"`
  - Push to main: `git push origin main`
  - Create backup branch: `git branch backup-before-root-cleanup-$(date +%Y%m%d)`
  - Push backup branch: `git push origin backup-before-root-cleanup-$(date +%Y%m%d)`
- [ ] **RUN FULL TEST SUITE** (CRITICAL - DO NOT SKIP)
  - Run: `pytest tests/` or `python -m pytest`
  - Verify all tests pass
- [ ] **TEST APPLICATION** (CRITICAL - DO NOT SKIP)
  - Run: `python main.py` (or main entry point)
  - Verify application starts successfully
  - Test critical functionality
- [ ] **DOCUMENT CURRENT STATE**
  - List all files in root
  - Document which files are essential
  - Take snapshot of root directory

### Checkpoint 1: Inventory Root Files
- [ ] List all files in root
- [ ] Categorize files:
  - Essential (keep in root)
  - Should move to subdirectory
  - Should delete
- [ ] Check file sizes and dates

### Checkpoint 2: Identify Files to Move
- [ ] Database files → `data/` or `var/`
- [ ] Documentation → `docs/`
- [ ] Scripts → `scripts/`
- [ ] Tests → `tests/`
- [ ] Configs → `config/`
- [ ] Generate list

### Checkpoint 3: Identify Files to Delete
- [ ] Duplicate files
- [ ] Old backup files
- [ ] Temporary files
- [ ] Unused files
- [ ] Generate list

### Checkpoint 4: Move Files
- [ ] Move files to appropriate locations
- [ ] Update references if needed
- [ ] Verify moves don't break anything
- [ ] Log each move

### Checkpoint 5: Delete Files
- [ ] Delete duplicate files
- [ ] Delete old backups
- [ ] Delete temporary files
- [ ] Log each deletion

### Checkpoint 6: Verify Root Structure (SUPER WELL ORGANIZED)
- [ ] **VERIFY STRUCTURE IS PERFECT**: Review root - must be minimal and professional
  - Only essential files should remain
  - Clean, organized appearance
  - Follows best practices
- [ ] Verify only essential files remain
- [ ] Check that all moved files are accessible
- [ ] Verify no broken references
- [ ] **TEST AFTER ALL MOVES**: Run tests and application
- [ ] Document final root structure

### Checkpoint 7: Generate Report
- [ ] Generate cleanup report
- [ ] Document files moved
- [ ] Document files deleted
- [ ] Document final root structure
- [ ] Save report

## Acceptance Criteria

- [ ] **GITHUB BACKUP CREATED** (MANDATORY)
- [ ] **ALL TESTS PASS** (MANDATORY)
- [ ] Root directory contains only essential files
- [ ] **Root SUPER WELL ORGANIZED** (MANDATORY - must be minimal and perfect)
- [ ] Other files moved to appropriate locations
- [ ] Duplicates removed (after verification)
- [ ] No broken references
- [ ] **APPLICATION WORKS** (MANDATORY - test after cleanup)
- [ ] Clean, professional root structure
- [ ] Cleanup report generated

## Related Issues

- General codebase organization

## Notes

- Root directory should be minimal and professional
- Only entry points and essential configs should be in root
- Be careful with moves - update all references
- Keep backups before major changes

## Success Metrics

- **Target:** 5+ files moved to subdirectories
- **Target:** Root directory minimal and clean
- **Target:** No broken references
- **Target:** Professional project structure

