# CLEANING TICKET #011: Clean Temporary Files

**Priority:** LOW  
**Status:** OPEN  
**Estimated Time:** 30 minutes  
**Assignee:** Cleaning Agent

## Problem

The codebase contains temporary files (`.tmp`, `.bak`, `.old`, `.swp`, `*~`) that accumulate over time and should be removed.

## Current State

**Temporary File Patterns:**
- `.tmp` files
- `.bak` files
- `.old` files
- `.swp` files (vim swap files)
- `*~` files (backup files)
- `.DS_Store` files (macOS)
- `Thumbs.db` files (Windows)
- `.pyc` files (should be handled by cache cleanup)

## Impact

- Wastes disk space
- Clutters codebase
- Not needed (temporary files)
- Can cause confusion
- Some can be large

## Requirements

Remove all temporary files safely.

### Safety Rules

**SAFE TO DELETE:**
- All `.tmp` files
- All `.bak` files
- All `.old` files (except intentionally named)
- All `.swp` files
- All `*~` files
- All `.DS_Store` files
- All `Thumbs.db` files

**NEVER DELETE:**
- Files with `.old` in name that are intentional (e.g., `config.old.json` - review first)
- Files in `.git/`, `.venv/`, `node_modules/`

## Checkpoints

### Checkpoint 1: Find All Temporary Files
- [ ] Find all `.tmp` files
- [ ] Find all `.bak` files
- [ ] Find all `.old` files
- [ ] Find all `.swp` files
- [ ] Find all `*~` files
- [ ] Find all `.DS_Store` files
- [ ] Find all `Thumbs.db` files
- [ ] Count total files
- [ ] Calculate total size

**Command:**
```bash
find . -type f \( -name "*.tmp" -o -name "*.bak" -o -name "*.old" -o -name "*.swp" -o -name "*~" -o -name ".DS_Store" -o -name "Thumbs.db" \) \
  -not -path "./.git/*" -not -path "./.venv*/*" -not -path "./node_modules/*"
```

### Checkpoint 2: Categorize Temporary Files
- [ ] Categorize by type
- [ ] Identify intentional `.old` files (review)
- [ ] Mark for deletion
- [ ] Review questionable files

### Checkpoint 3: Dry Run
- [ ] List all files that would be deleted
- [ ] Review list
- [ ] Verify no important files included
- [ ] Calculate space that would be freed

### Checkpoint 4: Delete Temporary Files
- [ ] Delete all `.tmp` files
- [ ] Delete all `.bak` files
- [ ] Delete all `.swp` files
- [ ] Delete all `*~` files
- [ ] Delete all `.DS_Store` files
- [ ] Delete all `Thumbs.db` files
- [ ] Review and delete `.old` files (carefully)
- [ ] Log each deletion
- [ ] Handle errors gracefully

### Checkpoint 5: Verify Cleanup
- [ ] Verify temporary files are removed
- [ ] Check disk space saved
- [ ] Verify no important files deleted

### Checkpoint 6: Generate Report
- [ ] Generate cleanup report
- [ ] Include files deleted by type
- [ ] Include disk space saved
- [ ] Save report

## Acceptance Criteria

- [ ] All temporary files removed
- [ ] No important files deleted
- [ ] Cleanup report generated
- [ ] Disk space freed

## Related Issues

- General codebase cleanup

## Notes

- This is a safe operation
- Run dry-run first
- Review `.old` files carefully
- Can be run regularly

