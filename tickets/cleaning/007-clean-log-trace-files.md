# CLEANING TICKET #007: Clean Log and Trace Files

**Priority:** HIGH  
**Status:** OPEN  
**Estimated Time:** 45 minutes  
**Assignee:** Cleaning Agent

## Problem

The `logs/` directory contains **916+ log, JSON, and PNG files** including old trace files, network dumps, and debug screenshots that should be cleaned up. This wastes **5.0 MB** of disk space and clutters the logs directory.

## Current State

**Location:** `logs/` directory

**Files Found:**
- **6 log files** (beyondlines_*.log, automated_collection.log)
- **20+ JSON trace files** (threads_ajax_*, threads_graphql_*, threads_network_*)
- **3 PNG files** (auth_failure_attempt_*.png)
- **Total:** 29+ files visible, potentially more

**Disk Space:** 5.0 MB (and growing)

**File Types:**
- `.log` files (application logs)
- `.json` files (network traces, API responses)
- `.png` files (screenshot dumps)

## Impact

- Wastes disk space (5.0 MB currently, growing)
- Clutters logs directory
- Makes it hard to find recent logs
- Old trace files not needed for debugging
- Network dumps can be large
- Screenshots accumulate over time

## Requirements

Clean logs and trace files according to retention policy:
- Keep last 7 days of logs in `logs/`
- Archive logs older than 7 days to `logs/archive/`
- Compress archived logs (gzip)
- Delete logs older than 30 days
- Clean JSON trace files (archive or delete based on age)
- Clean PNG debug files (archive or delete based on age)
- Clean network trace files

### Safety Rules

**NEVER DELETE:**
- Logs from last 7 days
- Active log files being written to
- Error logs that might be needed
- Recent trace files (if needed for debugging)

**ALWAYS ARCHIVE:**
- Logs older than 7 days but less than 30 days
- Compress archives to save space
- Preserve file names with `.gz` extension

## Checkpoints

### Checkpoint 1: Identify All Log and Trace Files
- [ ] Scan `logs/` directory for `.log` files
- [ ] Scan for `.json` files (trace files)
- [ ] Scan for `.png` files (screenshots)
- [ ] Check file modification dates
- [ ] Calculate file ages
- [ ] Categorize by type and age:
  - Keep (0-7 days)
  - Archive (7-30 days)
  - Delete (>30 days)

**Code:**
```python
logs_dir = Path("logs")
current_time = time.time()
keep_cutoff = current_time - (7 * 24 * 60 * 60)  # 7 days
delete_cutoff = current_time - (30 * 24 * 60 * 60)  # 30 days

log_files = list(logs_dir.glob("*.log"))
json_files = list(logs_dir.glob("*.json"))
png_files = list(logs_dir.glob("*.png"))

# Categorize
files_to_keep = []
files_to_archive = []
files_to_delete = []

for file in log_files + json_files + png_files:
    file_mtime = file.stat().st_mtime
    age_days = (current_time - file_mtime) / (24 * 60 * 60)
    
    if age_days <= 7:
        files_to_keep.append(file)
    elif age_days <= 30:
        files_to_archive.append(file)
    else:
        files_to_delete.append(file)
```

### Checkpoint 2: Create Archive Directory Structure
- [ ] Create `logs/archive/` if it doesn't exist
- [ ] Create subdirectories:
  - `logs/archive/logs/` (for .log files)
  - `logs/archive/traces/` (for .json files)
  - `logs/archive/screenshots/` (for .png files)
- [ ] Ensure directory structure is ready
- [ ] Verify write permissions

**Code:**
```python
archive_dir = Path("logs/archive")
archive_dir.mkdir(parents=True, exist_ok=True)

(archive_dir / "logs").mkdir(exist_ok=True)
(archive_dir / "traces").mkdir(exist_ok=True)
(archive_dir / "screenshots").mkdir(exist_ok=True)
```

### Checkpoint 3: Archive Old Logs (7-30 days)
- [ ] Move logs between 7-30 days old to `logs/archive/logs/`
- [ ] Compress archived logs with gzip
- [ ] Preserve original filenames with `.gz` extension
- [ ] Log each archived file
- [ ] Update cleanup stats

**Code:**
```python
for log_file in files_to_archive:
    if log_file.suffix == ".log":
        archive_path = archive_dir / "logs" / f"{log_file.name}.gz"
    elif log_file.suffix == ".json":
        archive_path = archive_dir / "traces" / f"{log_file.name}.gz"
    elif log_file.suffix == ".png":
        archive_path = archive_dir / "screenshots" / f"{log_file.name}.gz"
    
    with open(log_file, 'rb') as f_in:
        with gzip.open(archive_path, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
    
    log_file.unlink()
    logger.info(f"Archived: {log_file.name} -> {archive_path}")
    stats["files_archived"] += 1
    stats["bytes_freed"] += log_file.stat().st_size
```

### Checkpoint 4: Delete Very Old Files (>30 days)
- [ ] Delete logs older than 30 days
- [ ] Delete JSON trace files older than 30 days
- [ ] Delete PNG screenshots older than 30 days
- [ ] Log each deleted file
- [ ] Update cleanup stats
- [ ] Handle errors gracefully

**Code:**
```python
for file in files_to_delete:
    try:
        size = file.stat().st_size
        file.unlink()
        logger.info(f"Deleted old file (>{30} days): {file.name}")
        stats["files_removed"] += 1
        stats["bytes_freed"] += size
    except Exception as e:
        logger.error(f"Failed to delete {file}: {e}")
        stats["errors"].append(str(e))
```

### Checkpoint 5: Clean Specific Trace File Patterns
- [ ] Identify trace file patterns:
  - `threads_ajax_*.json` (network requests)
  - `threads_graphql_*.json` (GraphQL responses)
  - `threads_network_*.json` (network traces)
  - `*_request.json` (saved requests)
  - `*_response_*.json` (saved responses)
- [ ] Apply retention policy to each pattern
- [ ] Archive or delete based on age

**Patterns to Clean:**
- `threads_ajax_saved_request.json`
- `threads_ajax_saved_response_*.json` (0-9)
- `threads_graphql_request.json`
- `threads_graphql_response_*.json` (multiple)
- `threads_network_trace.json`

### Checkpoint 6: Clean Screenshot Files
- [ ] Identify PNG screenshot files
- [ ] Check modification dates
- [ ] Archive screenshots 7-30 days old
- [ ] Delete screenshots older than 30 days
- [ ] Keep recent screenshots (last 7 days) for debugging

**Files:**
- `auth_failure_attempt_1.png`
- `auth_failure_attempt_2.png`
- `auth_failure_attempt_3.png`

### Checkpoint 7: Verify Cleanup
- [ ] Verify logs directory only has recent files (0-7 days)
- [ ] Verify archive directory has compressed files
- [ ] Check disk space saved
- [ ] Verify no active logs were deleted
- [ ] Verify compressed files can be read
- [ ] Count files before/after

**Verification:**
```python
# Count recent files (should be <= 7 days old)
recent_files = [f for f in logs_dir.glob("*") 
                if f.is_file() and f.stat().st_mtime > keep_cutoff]
print(f"Recent files kept: {len(recent_files)}")

# Count archived files
archived_logs = len(list((archive_dir / "logs").glob("*.gz")))
archived_traces = len(list((archive_dir / "traces").glob("*.gz")))
archived_screenshots = len(list((archive_dir / "screenshots").glob("*.gz")))
print(f"Archived: {archived_logs} logs, {archived_traces} traces, {archived_screenshots} screenshots")

# Check disk space
disk_space_saved = stats["bytes_freed"]
print(f"Disk space saved: {disk_space_saved / 1024 / 1024:.2f} MB")
```

### Checkpoint 8: Generate Report
- [ ] Generate cleanup report
- [ ] Include files archived/deleted by type
- [ ] Include disk space saved
- [ ] Include compression ratio
- [ ] Save report to `docs/cleanup_reports/log_cleanup_YYYYMMDD_HHMMSS.json`

**Report Format:**
```json
{
  "timestamp": "2025-11-23T17:00:00Z",
  "operation": "clean_log_trace_files",
  "summary": {
    "logs_archived": 2,
    "logs_deleted": 0,
    "traces_archived": 15,
    "traces_deleted": 5,
    "screenshots_archived": 0,
    "screenshots_deleted": 0,
    "files_kept": 7,
    "total_archived": 17,
    "total_deleted": 5,
    "disk_space_saved_bytes": 2097152,
    "disk_space_saved_mb": 2.0,
    "compression_ratio": 0.3
  },
  "by_type": {
    "logs": {"archived": 2, "deleted": 0, "kept": 6},
    "traces": {"archived": 15, "deleted": 5, "kept": 0},
    "screenshots": {"archived": 0, "deleted": 0, "kept": 3}
  },
  "details": {
    "archived": [...],
    "deleted": [...]
  }
}
```

## Acceptance Criteria

- [ ] Logs older than 7 days archived
- [ ] Logs older than 30 days deleted
- [ ] Archived logs compressed (gzip)
- [ ] Recent logs (0-7 days) kept in `logs/`
- [ ] JSON trace files cleaned
- [ ] PNG files cleaned
- [ ] Network trace files cleaned
- [ ] No active logs deleted
- [ ] Cleanup report generated
- [ ] Disk space freed
- [ ] Compressed files can be read
- [ ] Archive structure organized

## Safety Exclusions

**Files to NEVER delete:**
- Logs from last 7 days
- Active log files (currently being written)
- Error logs that might be needed for debugging
- Recent trace files (last 7 days)

## Retention Policy

- **Active logs:** Keep last 7 days in `logs/`
- **Archived logs:** Keep 7-30 days in `logs/archive/` (compressed)
- **Old logs:** Delete after 30 days
- **Trace files:** Same policy as logs
- **PNG files:** Same policy as logs

## Related Issues

- Cleaning Ticket #002: Rotate Log Files (previous partial work)

## Notes

- This is a safe operation (archive before delete)
- Compressed archives can be restored if needed
- Run dry-run first to verify
- Consider log rotation schedule (weekly)
- Compression saves significant disk space
- Can be automated to run weekly
- Network trace files can be large, significant space savings

## Success Metrics

- **Target:** Only recent logs (0-7 days) in `logs/`
- **Target:** All old logs archived and compressed
- **Target:** 2+ MB disk space saved
- **Target:** 20+ trace files cleaned

