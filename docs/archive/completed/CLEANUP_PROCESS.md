# Cleanup Process Guide

This guide explains how to use the cleanup system, configure it, and maintain it.

## Overview

The cleanup system provides automated cleanup of the codebase through the `CleaningAgent`. It handles documentation archiving, log rotation, backup management, deprecated code detection, and more.

## Quick Start

### Manual Cleanup

```python
from src.agents.specialized.cleaning_agent import CleaningAgent

# Initialize the agent
agent = CleaningAgent()
await agent.initialize()

# Run cleanup
result = await agent.process({
    "artifacts": {
        "verification_result": {"verdict": "verified"},
        "dry_run": False
    }
})

print(f"Files removed: {result['artifacts']['cleanup_result']['stats']['files_removed']}")
print(f"Bytes freed: {result['artifacts']['cleanup_result']['stats']['bytes_freed']}")
```

### Dry Run (Test Mode)

```python
# Run in dry-run mode to see what would be cleaned
result = await agent.process({
    "artifacts": {
        "verification_result": {"verdict": "verified"},
        "dry_run": True
    }
})

# Review what would be cleaned
for item in result['artifacts']['cleanup_result']['items_removed']:
    print(f"Would remove: {item['path']}")
```

## Using the Cleaning Agent

### Initialization

```python
from src.agents.specialized.cleaning_agent import CleaningAgent

# Use default config
agent = CleaningAgent()

# Or specify custom config path
agent = CleaningAgent(config_path="custom/path/cleaning_agent.yaml")

# Initialize
await agent.initialize()
```

### Basic Cleanup

```python
# Run cleanup with verification
state = {
    "artifacts": {
        "verification_result": {"verdict": "verified"}
    }
}

result = await agent.process(state)

# Check results
cleanup_result = result["artifacts"]["cleanup_result"]
print(f"Status: {cleanup_result['status']}")
print(f"Files removed: {cleanup_result['stats']['files_removed']}")
print(f"Files archived: {cleanup_result['stats']['files_archived']}")
print(f"Bytes freed: {cleanup_result['stats']['bytes_freed']}")
```

### Scheduled Cleanup

The agent supports different cleanup schedules:

```python
# Weekly cleanup (logs, cache, temp files)
result = await agent.run_scheduled_cleanup("weekly")

# Monthly cleanup (documentation, backups)
result = await agent.run_scheduled_cleanup("monthly")

# Pre-release cleanup (full cleanup)
result = await agent.run_scheduled_cleanup("pre-release")
```

### Cleanup Without Verification

```python
# Disable verification requirement in config
# Or pass verification in state
state = {
    "artifacts": {
        "verification_result": {"verdict": "verified"}
    }
}

result = await agent.process(state)
```

## Configuration

### Configuration File

The cleanup agent is configured via `src/agents/config/cleaning_agent.yaml`.

### Key Configuration Sections

#### Cleanup Rules

```yaml
cleanup_rules:
  docs:
    archive_completed: true
    keep_active_only: true
    archive_location: "docs/archive/completed/"
  
  logs:
    keep_days: 7
    archive_days: 30
    archive_location: "logs/archive/"
  
  backups:
    keep_count: 3
    archive_days: 90
    archive_location: "backups/archive/"
  
  deprecated_code:
    detect: true
    remove: false  # Report only
  
  scripts:
    organize_archive: true
    keep_active_only: true
```

#### Safety Checks

```yaml
safety_checks:
  require_verification: true
  dry_run: false
  backup_before_delete: false
```

#### Exclusions

```yaml
exclusions:
  exclude_directories:
    - ".git"
    - "node_modules"
    - ".venv"
  
  exclude_patterns:
    - "*.db"
    - "*.py"
    - "*.md"
```

### Updating Configuration

1. Edit `src/agents/config/cleaning_agent.yaml`
2. Reload agent or restart application
3. Test with dry-run mode
4. Apply changes

## Cleanup Operations

### Documentation Cleanup

Archives completed status reports:

```python
# Automatically handled in full cleanup
# Or run individually (if exposed as method)
result = await agent._cleanup_completed_docs(dry_run=False)
```

**What it does**:
- Finds completed docs matching patterns (`*_COMPLETE.md`, `*_FINAL*.md`, etc.)
- Moves them to `docs/archive/completed/`
- Preserves file structure

### Log Rotation

Manages log files:

```python
result = await agent._rotate_logs(dry_run=False)
```

**What it does**:
- Keeps last 7 days of logs
- Archives logs older than 7 days (compressed)
- Deletes logs older than 30 days

### Backup Management

Manages database and config backups:

```python
result = await agent._cleanup_backups(dry_run=False)
```

**What it does**:
- Keeps last 3 database backups
- Archives older backups
- Deletes backups older than 90 days
- Cleans JSON backups older than 30 days

### Deprecated Code Detection

Identifies deprecated code:

```python
result = await agent._identify_deprecated_code(dry_run=False)
```

**What it does**:
- Searches for `@deprecated`, `# DEPRECATED`, etc.
- Generates report in `docs/cleanup_reports/`
- Does NOT auto-remove (safety)

### Script Organization

Organizes scripts:

```python
result = await agent._organize_scripts(dry_run=False)
```

**What it does**:
- Moves obsolete test scripts to `scripts/archive/old_tests/`
- Keeps active scripts in main directory

### Cache Cleanup

Removes cache directories:

```python
result = await agent._remove_pycache_dirs(dry_run=False)
```

**What it does**:
- Removes `__pycache__`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`
- Cleans `node_modules/.cache` in frontend

### Temp File Cleanup

Removes temporary files:

```python
result = await agent._remove_temp_files(dry_run=False)
```

**What it does**:
- Removes `.tmp`, `.temp`, `.swp`, `.swo`, `*~` files
- Cleans `test_results/` older than 7 days
- Cleans `var/` directory

## Verification

### How to Verify Cleanup

1. **Check Cleanup Report**:
   ```python
   # Reports are saved to docs/cleanup_reports/
   import json
   from pathlib import Path
   
   report_path = Path("docs/cleanup_reports/cleanup_report_*.json")
   with open(report_path) as f:
       report = json.load(f)
       print(json.dumps(report, indent=2))
   ```

2. **Review Statistics**:
   ```python
   stats = result["artifacts"]["cleanup_result"]["stats"]
   print(f"Files removed: {stats['files_removed']}")
   print(f"Files archived: {stats['files_archived']}")
   print(f"Bytes freed: {stats['bytes_freed']}")
   print(f"Errors: {len(stats['errors'])}")
   ```

3. **Check Archive Directories**:
   - `docs/archive/completed/` - Archived docs
   - `logs/archive/` - Archived logs
   - `backups/archive/` - Archived backups

4. **Verify Exclusions**:
   - Check that excluded files/directories were not touched
   - Review cleanup report for any unexpected removals

## Scheduling

### Automated Scheduling

The cleanup can be scheduled using cron or a task scheduler:

#### Weekly Cleanup (Cron)

```bash
# Add to crontab
0 2 * * 0 cd /path/to/project && python -m scripts.run_cleanup weekly
```

#### Monthly Cleanup (Cron)

```bash
# Add to crontab
0 3 1 * * cd /path/to/project && python -m scripts.run_cleanup monthly
```

#### Pre-Release Cleanup

Run manually before releases:

```bash
python -m scripts.run_cleanup pre-release
```

### Programmatic Scheduling

```python
import asyncio
from datetime import datetime, timedelta

async def schedule_cleanup():
    agent = CleaningAgent()
    await agent.initialize()
    
    # Weekly cleanup
    while True:
        await agent.run_scheduled_cleanup("weekly")
        await asyncio.sleep(7 * 24 * 60 * 60)  # Wait 7 days

# Run in background
asyncio.create_task(schedule_cleanup())
```

## Cleanup Reports

### Report Location

Reports are saved to: `docs/cleanup_reports/cleanup_report_YYYYMMDD_HHMMSS.json`

### Report Structure

```json
{
  "timestamp": "2024-01-15T10:30:00",
  "summary": {
    "files_removed": 50,
    "directories_removed": 10,
    "files_archived": 20,
    "bytes_freed": 104857600,
    "errors_count": 0
  },
  "operations": [
    "remove_pycache",
    "rotate_logs",
    "cleanup_backups"
  ],
  "details": {
    "dry_run": false,
    "rules_applied": [...],
    "items_removed": [...]
  },
  "errors": []
}
```

### Reading Reports

```python
import json
from pathlib import Path

# Find latest report
reports_dir = Path("docs/cleanup_reports")
latest_report = max(reports_dir.glob("cleanup_report_*.json"), key=lambda p: p.stat().st_mtime)

with open(latest_report) as f:
    report = json.load(f)
    print(f"Last cleanup: {report['timestamp']}")
    print(f"Files removed: {report['summary']['files_removed']}")
    print(f"Bytes freed: {report['summary']['bytes_freed']}")
```

## Troubleshooting

### Cleanup Not Running

1. **Check Configuration**:
   ```python
   agent = CleaningAgent()
   print(agent.config)  # Verify config loaded
   ```

2. **Check Verification**:
   - Ensure `verification_result` is passed
   - Or disable `require_verification` in config

3. **Check Logs**:
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

### Files Not Being Cleaned

1. **Check Exclusions**:
   - Verify file/directory is not in exclusions
   - Check exclusion patterns

2. **Check Rules**:
   - Verify rule is enabled in config
   - Check rule conditions (age, count, etc.)

3. **Check Permissions**:
   - Ensure agent has write permissions
   - Check file/directory permissions

### Too Much/Little Cleaned

1. **Adjust Retention Policies**:
   ```yaml
   logs:
     keep_days: 14  # Increase from 7
   
   backups:
     keep_count: 5  # Increase from 3
   ```

2. **Update Exclusions**:
   ```yaml
   exclusions:
     exclude_patterns:
       - "*.custom"
   ```

3. **Review Rules**:
   - Enable/disable specific rules
   - Adjust thresholds

### Errors During Cleanup

1. **Check Error Logs**:
   ```python
   errors = result["artifacts"]["cleanup_result"]["stats"]["errors"]
   for error in errors:
       print(error)
   ```

2. **Check Permissions**:
   - Verify write permissions
   - Check disk space

3. **Review Exclusions**:
   - Ensure critical files are excluded

## Best Practices

1. **Always Test First**:
   - Run in dry-run mode
   - Review what would be cleaned
   - Verify no critical files affected

2. **Review Reports**:
   - Check cleanup reports after each run
   - Monitor disk space freed
   - Track errors

3. **Update Exclusions**:
   - Keep exclusions up to date
   - Add new critical paths
   - Review exclusion patterns

4. **Schedule Regularly**:
   - Weekly for logs/cache
   - Monthly for docs/backups
   - Pre-release for full cleanup

5. **Monitor Disk Space**:
   - Track before/after cleanup
   - Adjust retention if needed
   - Clean archives periodically

## Integration

### With Agent Graph

```python
from src.application.orchestration.agent_graph import AgentGraph

graph = AgentGraph()
# Cleaner is automatically included in workflow
result = await graph.process_cleanup_task()
```

### With Monitoring

```python
# Cleanup metrics are automatically recorded
health = await agent.health_check()
print(f"Cleanup count: {health['cleanup_count']}")
print(f"Last cleanup: {health['last_cleanup']}")
```

## Related Documentation

- [CLEANUP_RULES.md](CLEANUP_RULES.md) - Cleanup rules and standards
- [cleaning_agent.yaml](../src/agents/config/cleaning_agent.yaml) - Configuration reference
- [cleaning_agent.py](../src/agents/specialized/cleaning_agent.py) - Implementation details

