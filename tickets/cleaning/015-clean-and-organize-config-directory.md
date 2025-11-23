# CLEANING TICKET #015: Clean and Organize config/ Directory

**Priority:** LOW  
**Status:** OPEN  
**Estimated Time:** 30 minutes  
**Assignee:** Cleaning Agent

## Problem

The `config/` directory contains multiple configuration files that may have duplicates, unused configs, or need better organization.

## Current State

**Location:** `config/` directory

**Files Found:**
- `collection.json`
- `content_sources.json`
- `opinions.json`
- `personalities.json`
- `platform_formats.json`
- `platform_integrations.json`
- `qronoya_prompts.json`
- `rewrite_rules.json`
- `telegram_channels.txt`
- `threads_cookies.json`
- `voice_patterns.json`
- `requirements-dev.txt`
- `personas/` subdirectory (11 JSON files)
- `profiles/` subdirectory (4 JSON files)
- `cookies/` subdirectory

## Impact

- Potential duplicate configurations
- Unused configs waste space
- Hard to find the right config
- May have conflicting settings

## Requirements

Clean and organize `config/` directory:
- Remove duplicate configs
- Remove unused configs
- Organize by category
- Document config files
- Verify all configs are used
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
   - Run application: `python main.py` (or main entry point)
   - Verify all configs load correctly
   - Test critical functionality that uses configs
   - **DO NOT DELETE ANYTHING UNTIL VERIFIED UNUSED**

3. **✅ VERIFY BEFORE DELETION**
   - For each config to delete:
     - Verify it's not referenced in code
     - Verify it's not used by application
     - Verify it's not in documentation
   - **WHEN IN DOUBT, DON'T DELETE**

### Safety Rules

**NEVER DELETE:**
- Active configuration files
- Configs referenced in code
- Configs with user data
- Required configs

**SAFE TO DELETE:**
- Duplicate configs
- Unused configs (after verification)
- Old backup configs
- Test configs (if not needed)

## Checkpoints

### Checkpoint 0: Pre-Cleanup Safety
- [ ] **PUSH BACKUP TO GITHUB** (CRITICAL - DO NOT SKIP)
  - Commit all changes: `git add . && git commit -m "Pre-cleanup backup"`
  - Push to main: `git push origin main`
  - Create backup branch: `git branch backup-before-config-cleanup-$(date +%Y%m%d)`
  - Push backup branch: `git push origin backup-before-config-cleanup-$(date +%Y%m%d)`
- [ ] **TEST APPLICATION** (CRITICAL - DO NOT SKIP)
  - Run: `python main.py` (or main entry point)
  - Verify application starts successfully
  - Test functionality that uses configs
- [ ] **DOCUMENT CURRENT STATE**
  - List all config files
  - Document which configs are known to be used
  - Take snapshot of directory structure

### Checkpoint 1: Inventory Config Files
- [ ] List all config files
- [ ] Check file sizes and dates
- [ ] Identify config types:
  - Platform configs
  - Persona configs
  - Collection configs
  - Integration configs

### Checkpoint 2: Find References
- [ ] Search codebase for config file references
- [ ] Identify which configs are used
- [ ] Identify which configs are unused
- [ ] Generate report

### Checkpoint 3: Identify Duplicates
- [ ] Compare config files for duplicates
- [ ] Check for conflicting settings
- [ ] Identify which to keep
- [ ] Document duplicates

### Checkpoint 4: Organize Structure (SUPER WELL ORGANIZED)
- [ ] **PLAN STRUCTURE FIRST**: Design perfect folder organization
  - Each subdirectory should have clear purpose
  - Group related configs together
  - Create logical hierarchy
- [ ] Create subdirectories if needed:
  - `config/platforms/` - Platform configs
  - `config/personas/` - Persona configs (already exists)
  - `config/integrations/` - Integration configs
- [ ] Move configs to appropriate locations
- [ ] Update references if needed
- [ ] **TEST AFTER EACH MOVE**: Verify application still works
- [ ] **VERIFY STRUCTURE IS PERFECT**: Review organization - must be super well organized

### Checkpoint 5: Remove Unused Configs
- [ ] Remove unused configs (after verification)
- [ ] Remove duplicate configs
- [ ] Remove old backup configs
- [ ] Log each removal

### Checkpoint 6: Document Configs
- [ ] Create `config/README.md`
- [ ] Document each config file
- [ ] Include usage examples
- [ ] Document required vs optional configs

### Checkpoint 7: Generate Report
- [ ] Generate cleanup report
- [ ] Document configs removed
- [ ] Document configs organized
- [ ] Save report

## Acceptance Criteria

- [ ] **GITHUB BACKUP CREATED** (MANDATORY)
- [ ] Configs organized by category
- [ ] **Structure SUPER WELL ORGANIZED** (MANDATORY - must be perfect)
- [ ] Unused configs removed (after verification)
- [ ] Duplicates consolidated
- [ ] Active configs documented
- [ ] No broken references
- [ ] **APPLICATION WORKS** (MANDATORY - test after cleanup)
- [ ] Cleanup report generated

## Related Issues

- General codebase organization

## Notes

- Be very careful with config files
- Verify all configs are not in use before deleting
- Keep backups of configs before changes
- Configs may contain important settings

## Success Metrics

- **Target:** 5+ unused configs identified
- **Target:** Configs organized by category
- **Target:** Active configs documented
- **Target:** Cleaner, more navigable config directory

