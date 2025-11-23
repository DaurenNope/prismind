# Cleanup Rules and Standards

This document defines the cleanup rules, retention policies, and safety standards for the automated cleanup system.

## Overview

The cleanup system is designed to maintain a clean and organized codebase by automatically managing:
- Documentation files
- Log files
- Backup files
- Deprecated code
- Cache and temporary files
- Script organization

## Cleanup Categories

### 1. Documentation Cleanup

**Purpose**: Archive completed status reports and keep only active documentation.

**Rules**:
- Identify completed status reports using patterns:
  - `*_COMPLETE.md`
  - `*_FINAL*.md`
  - `AGENT_*_COMPLETE.md`
  - `*_COMPLETE_SUMMARY.md`
  - `*_FINAL_STATUS.md`
- Move completed docs to `docs/archive/completed/` (don't delete, archive)
- Keep only active documentation in `docs/`

**Retention Policy**:
- Completed status reports: Archive after 30 days
- Old migration guides: Archive after migration complete + 90 days
- Obsolete architecture docs: Archive after superseded

### 2. Log Rotation

**Purpose**: Manage log files to prevent disk space issues.

**Rules**:
- Keep last 7 days of logs in `logs/`
- Archive logs older than 7 days to `logs/archive/`
- Compress archived logs (gzip)
- Delete logs older than 30 days

**Retention Policy**:
- Active logs: Keep last 7 days
- Archived logs: Keep last 30 days, then delete
- Compress archives older than 7 days

### 3. Backup Management

**Purpose**: Manage database and configuration backups efficiently.

**Rules**:
- Keep last 3 database backups in `backups/`
- Move older backups to `backups/archive/`
- Delete backups older than 90 days
- Clean up JSON backup files older than 30 days

**Retention Policy**:
- Database backups: Keep last 3, archive older
- Config backups: Keep last 7, delete older
- JSON backups: Keep last 30 days

### 4. Code Cleanup (Deprecated Code)

**Purpose**: Identify and report deprecated code for manual review.

**Rules**:
- Detect deprecated code marked with:
  - `@deprecated` decorator
  - `# DEPRECATED` comments
  - `# deprecated` comments
  - `TODO.*deprecated` comments
  - `FIXME.*deprecated` comments
- Generate report of deprecated code
- **Do NOT auto-remove** (safety: manual removal only)

**Retention Policy**:
- Deprecated code: Report only, manual removal
- Unused imports: Auto-remove (with verification)
- Dead code: Report only, manual removal

### 5. Script Organization

**Purpose**: Organize scripts and archive obsolete test scripts.

**Rules**:
- Identify scripts in `scripts/archive/` that are truly obsolete
- Move old test scripts to `scripts/archive/old_tests/`
- Keep only active scripts in main `scripts/` directory

**Retention Policy**:
- Active scripts: Keep in main directory
- Obsolete scripts: Archive after verification
- Old test scripts: Move to archive after 90 days of inactivity

### 6. Cache Cleanup

**Purpose**: Remove build and cache artifacts.

**Rules**:
- Remove `__pycache__` directories
- Remove `.pytest_cache` directories
- Remove `.mypy_cache` directories
- Remove `.ruff_cache` directories
- Clean `node_modules/.cache` in frontend

**Retention Policy**:
- Cache directories: Remove on every cleanup (safe to regenerate)
- Build artifacts: Remove after build completion

### 7. Temp File Cleanup

**Purpose**: Remove temporary and test result files.

**Rules**:
- Clean `.tmp`, `.temp`, `.swp`, `.swo`, `*~` files
- Clean `test_results/` older than 7 days
- Clean `var/` directory if exists
- Remove any temporary files matching patterns

**Retention Policy**:
- Temp files: Remove immediately
- Test results: Keep last 7 days
- Var directory: Clean on each run

## Retention Policies Summary

### Documentation
- Completed status reports: Archive after 30 days
- Old migration guides: Archive after migration complete + 90 days
- Obsolete architecture docs: Archive after superseded

### Logs
- Active logs: Keep last 7 days
- Archived logs: Keep last 30 days, then delete
- Compress archives older than 7 days

### Backups
- Database backups: Keep last 3, archive older
- Config backups: Keep last 7, delete older
- JSON backups: Keep last 30 days

### Code
- Deprecated code: Report only, manual removal
- Unused imports: Auto-remove (with verification)
- Dead code: Report only, manual removal

## Safety Rules

### Never Delete Without Backup
- Always archive before delete
- Keep backups of critical files
- Verify backups before deletion

### Always Archive Before Delete
- Move files to archive directories
- Preserve file structure in archives
- Compress archives to save space

### Verify Before Deletion
- Dry-run mode for testing
- Review cleanup reports
- Verify exclusions are working

### Dry-Run Mode for Testing
- Test cleanup rules before applying
- Review what would be cleaned
- Verify no critical files are affected

### Approval Required for Destructive Operations
- Require verification from skeptic agent
- Manual approval for major cleanups
- Review cleanup reports before deletion

## Cleanup Schedule

### Weekly: Automated Cleanup
- **When**: Every Sunday at 2 AM
- **Scope**: Logs, cache, temp files
- **Type**: Light cleanup, safe operations

### Monthly: Documentation Archive
- **When**: First day of month at 3 AM
- **Scope**: Documentation, backups
- **Type**: Archive operations

### Quarterly: Major Cleanup Review
- **When**: First day of quarter at 4 AM
- **Scope**: Full cleanup pass
- **Type**: Comprehensive review and cleanup

### Pre-Release: Full Cleanup Pass
- **When**: Before each release
- **Scope**: All cleanup categories
- **Type**: Complete cleanup with verification

## Cleanup Checklist

### Pre-Cleanup Checklist
- [ ] Review cleanup configuration
- [ ] Verify exclusions are correct
- [ ] Run dry-run mode
- [ ] Review dry-run report
- [ ] Verify no critical files are affected
- [ ] Ensure backups are up to date

### Post-Cleanup Verification
- [ ] Review cleanup report
- [ ] Verify files were archived correctly
- [ ] Check for any errors
- [ ] Verify disk space freed
- [ ] Confirm no critical files were removed

### Rollback Procedures
- [ ] Restore from archive if needed
- [ ] Check git history for deleted files
- [ ] Restore from backups if critical files lost
- [ ] Review exclusion rules if issues found

## Exclusions

The following paths and patterns are **never** cleaned:

### Excluded Directories
- `.git`
- `node_modules`
- `.venv`, `venv`, `env`
- `.env`
- `migrations`
- `data/vector_db`

### Excluded File Patterns
- `*.db`, `*.sqlite`, `*.sqlite3`
- `requirements*.txt`
- `*.yaml`, `*.yml`
- `*.json`
- `*.md`
- `*.py`
- `*.sh`

## Examples

### Example: Weekly Cleanup
```yaml
Schedule: Weekly (Sunday 2 AM)
Operations:
  - Log rotation (keep 7 days)
  - Cache cleanup
  - Temp file removal
Expected: ~100MB freed, 50 files removed
```

### Example: Monthly Archive
```yaml
Schedule: Monthly (1st day, 3 AM)
Operations:
  - Archive completed docs
  - Archive old backups
  - Organize scripts
Expected: ~500MB archived, 20 files moved
```

### Example: Pre-Release Cleanup
```yaml
Schedule: Before release
Operations:
  - Full cleanup pass
  - All categories
  - With verification
Expected: ~1GB freed, comprehensive cleanup
```

## Configuration

Cleanup rules are configured in `src/agents/config/cleaning_agent.yaml`.

Key settings:
- `cleanup_rules`: Define what gets cleaned
- `safety_checks`: Safety mechanisms
- `exclusions`: Paths to never clean
- `file_age`: Age thresholds for files

## Reporting

Cleanup reports are generated after each run and saved to:
- `docs/cleanup_reports/cleanup_report_YYYYMMDD_HHMMSS.json`

Reports include:
- Summary of operations
- Files removed/archived
- Disk space freed
- Errors encountered
- Detailed operation log

## Best Practices

1. **Always run dry-run first**: Test cleanup rules before applying
2. **Review reports**: Check cleanup reports after each run
3. **Update exclusions**: Keep exclusions up to date
4. **Monitor disk space**: Track disk space before/after cleanup
5. **Archive before delete**: Always archive before deleting
6. **Verify backups**: Ensure backups are working before cleanup
7. **Test in dev**: Test cleanup rules in development first

## Troubleshooting

### Issue: Critical files deleted
**Solution**: Check exclusions, restore from archive/backup

### Issue: Cleanup not running
**Solution**: Check scheduler, verify configuration, check logs

### Issue: Too much/little cleaned
**Solution**: Adjust retention policies, update rules

### Issue: Archive directory full
**Solution**: Clean old archives, increase archive retention

## Related Documentation

- [CLEANUP_PROCESS.md](CLEANUP_PROCESS.md) - How to use the cleanup system
- [cleaning_agent.yaml](../src/agents/config/cleaning_agent.yaml) - Configuration file
- [cleaning_agent.py](../src/agents/specialized/cleaning_agent.py) - Implementation

