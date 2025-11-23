# CLEANING TICKET #014: Clean and Organize tests/ Directory

**Priority:** MEDIUM  
**Status:** OPEN  
**Estimated Time:** 1-2 hours  
**Assignee:** Cleaning Agent

## Problem

The `tests/` directory contains **131 Python files** (1.3 MB) and needs organization, removal of unused tests, and consolidation of duplicate test cases.

## Current State

**Location:** `tests/` directory

**Statistics:**
- **131 Python files** total
- **1.3 MB** total size
- Potentially unused or duplicate tests
- May not match current codebase structure

## Impact

- Unused tests waste space
- Duplicate tests waste time
- Hard to find relevant tests
- Tests may not match code structure

## Requirements

Clean and organize `tests/` directory:
- Remove unused/broken tests
- Consolidate duplicate tests
- Organize to match `src/` structure
- Remove obsolete tests
- Ensure tests are up to date
- **SUPER WELL ORGANIZED** - Must perfectly mirror `src/` structure

## ⚠️ CRITICAL SAFETY REQUIREMENTS

**BEFORE STARTING ANY CLEANUP:**

1. **✅ PUSH BACKUP TO GITHUB**
   - Commit all current changes
   - Push to GitHub: `git push origin main` (or current branch)
   - Create backup branch: `git branch backup-before-cleanup-YYYYMMDD`
   - Push backup branch: `git push origin backup-before-cleanup-YYYYMMDD`
   - **DO NOT PROCEED WITHOUT GITHUB BACKUP**

2. **✅ RUN FULL TEST SUITE BEFORE DELETION**
   - Run: `pytest tests/` or `python -m pytest`
   - Document current test results
   - Identify broken tests
   - **DO NOT DELETE TESTS UNTIL VERIFIED UNUSED/BROKEN**

3. **✅ VERIFY BEFORE DELETION**
   - For each test to delete:
     - Verify it's truly broken/unused
     - Verify it's not testing critical functionality
     - Verify it's not referenced in CI/CD
   - **WHEN IN DOUBT, DON'T DELETE**

### Safety Rules

**NEVER DELETE:**
- Active test files
- Tests referenced in CI/CD
- Tests for critical functionality
- Integration tests

**SAFE TO DELETE:**
- Broken/unused tests
- Duplicate tests
- Obsolete tests
- Tests for removed features

## Checkpoints

### Checkpoint 0: Pre-Cleanup Safety
- [ ] **PUSH BACKUP TO GITHUB** (CRITICAL - DO NOT SKIP)
  - Commit all changes: `git add . && git commit -m "Pre-cleanup backup"`
  - Push to main: `git push origin main`
  - Create backup branch: `git branch backup-before-tests-cleanup-$(date +%Y%m%d)`
  - Push backup branch: `git push origin backup-before-tests-cleanup-$(date +%Y%m%d)`
- [ ] **RUN FULL TEST SUITE** (CRITICAL - DO NOT SKIP)
  - Run: `pytest tests/` or `python -m pytest`
  - Document test results
  - Save test output for comparison
- [ ] **DOCUMENT CURRENT STATE**
  - List all test files
  - Document test structure
  - Take snapshot of directory tree

### Checkpoint 1: Analyze Test Structure
- [ ] List all test files
- [ ] Check if tests match `src/` structure
- [ ] Identify test categories:
  - Unit tests
  - Integration tests
  - End-to-end tests
  - Performance tests

### Checkpoint 2: Identify Broken Tests
- [ ] Run test suite
- [ ] Identify broken tests
- [ ] Check if tests reference removed code
- [ ] Generate report

### Checkpoint 3: Identify Unused Tests
- [ ] Find tests for removed features
- [ ] Find tests not in test suite
- [ ] Find duplicate test cases
- [ ] Generate report

### Checkpoint 4: Organize Structure (SUPER WELL ORGANIZED)
- [ ] **PLAN STRUCTURE FIRST**: Design perfect folder organization
  - Must perfectly mirror `src/` structure
  - Each test file should match source file location
  - Group by test type: unit, integration, e2e
  - Create logical hierarchy matching codebase
- [ ] Organize to match `src/` structure:
  - `tests/unit/` - Unit tests (mirror `src/` structure)
  - `tests/integration/` - Integration tests
  - `tests/e2e/` - End-to-end tests
  - Mirror `src/` structure where possible
- [ ] Move tests to appropriate locations
- [ ] Update imports if needed
- [ ] **VERIFY STRUCTURE IS PERFECT**: Review organization - must perfectly mirror `src/`
- [ ] **RUN TESTS AFTER EACH MOVE**: Ensure tests still work after reorganization

### Checkpoint 5: Remove Unused Tests
- [ ] Remove broken tests (after verification)
- [ ] Remove duplicate tests
- [ ] Remove obsolete tests
- [ ] Log each removal

### Checkpoint 6: Update Test Configuration
- [ ] Verify `pytest.ini` is correct
- [ ] Update test paths if structure changed
- [ ] Ensure test discovery works
- [ ] Run full test suite

### Checkpoint 7: Generate Report
- [ ] Generate cleanup report
- [ ] Document tests removed
- [ ] Document tests organized
- [ ] Document test coverage
- [ ] Save report

## Acceptance Criteria

- [ ] **GITHUB BACKUP CREATED** (MANDATORY)
- [ ] **INITIAL TEST SUITE RUN** (MANDATORY - document results)
- [ ] Tests organized to match `src/` structure
- [ ] **Structure SUPER WELL ORGANIZED** (MANDATORY - must perfectly mirror `src/`)
- [ ] Broken tests removed or fixed
- [ ] Unused tests removed (after verification)
- [ ] Duplicates consolidated
- [ ] **FINAL TEST SUITE RUNS SUCCESSFULLY** (MANDATORY)
- [ ] **ALL TESTS PASS** (MANDATORY)
- [ ] Cleanup report generated

## Related Issues

- General codebase organization

## Notes

- Be careful not to delete important tests
- Run test suite before and after cleanup
- Keep tests that provide value
- Ensure test coverage is maintained

## Success Metrics

- **Target:** 10+ unused tests identified
- **Target:** Tests organized to match code structure
- **Target:** Test suite runs successfully
- **Target:** Cleaner, more maintainable test directory

