# CLEANING TICKET #009: Clean var/ and data/ Directories

**Priority:** MEDIUM  
**Status:** OPEN  
**Estimated Time:** 1 hour  
**Assignee:** Cleaning Agent

## Problem

The `var/` and `data/` directories contain various runtime files, cached data, and temporary files that should be cleaned according to retention policies. These directories are **744 KB** and growing.

## Current State

**var/ Directory (744 KB):**
- `collection_history.json`
- `collection_logs.json`
- `diary_entries.json`
- `github_trending.json`
- `last_platform_fix.txt`
- `posts.db`
- `prismind.db`
- `scrape_state.db`
- `sessions/telegram_scraper.session`
- `twitter_bookmarks.json`

**data/ Directory:**
- `ab_tests/ab_tests.json`
- `analytics/query_performance.jsonl`
- `analytics/rewrite_log.jsonl`
- `curated_posts/qronoya_curated.jsonl`
- `learning_loop/content_performance.json`
- `output_backup/scraped_qronoya_posts_backup.json`
- `vector_db/examples.json`

## Impact

- Wastes disk space
- Clutters data directories
- Old cached data not needed
- Database files can grow large
- JSON files accumulate over time
- Makes it hard to find current data

## Requirements

Clean `var/` and `data/` directories according to retention policies:
- Keep recent data files (last 30 days)
- Archive old data files (30-90 days)
- Delete very old data files (>90 days)
- Clean old database files
- Clean old session files
- Clean old backup files in `data/output_backup/`

### Safety Rules

**NEVER DELETE:**
- Recent data files (last 30 days)
- Active database files
- Configuration files
- Files currently in use

**ALWAYS ARCHIVE:**
- Data files older than 30 days but less than 90 days
- Move to archive before deletion

## Checkpoints

### Checkpoint 1: Audit var/ Directory
- [ ] List all files in `var/`
- [ ] Check file modification dates
- [ ] Categorize by type:
  - Database files (.db)
  - JSON data files
  - Session files
  - Log files
  - Temporary files
- [ ] Calculate file ages
- [ ] Identify files to clean

**Code:**
```python
var_dir = Path("var")
current_time = time.time()
keep_cutoff = current_time - (30 * 24 * 60 * 60)  # 30 days
delete_cutoff = current_time - (90 * 24 * 60 * 60)  # 90 days

var_files = {
    "databases": [],
    "json_files": [],
    "sessions": [],
    "logs": [],
    "other": []
}

for file in var_dir.rglob("*"):
    if file.is_dir():
        continue
    
    file_mtime = file.stat().st_mtime
    age_days = (current_time - file_mtime) / (24 * 60 * 60)
    
    if file.suffix == ".db":
        var_files["databases"].append((file, age_days))
    elif file.suffix == ".json":
        var_files["json_files"].append((file, age_days))
    elif file.suffix == ".session":
        var_files["sessions"].append((file, age_days))
    elif "log" in file.name.lower():
        var_files["logs"].append((file, age_days))
    else:
        var_files["other"].append((file, age_days))
```

### Checkpoint 2: Audit data/ Directory
- [ ] List all files in `data/`
- [ ] Check file modification dates
- [ ] Categorize by subdirectory:
  - `ab_tests/`
  - `analytics/`
  - `curated_posts/`
  - `learning_loop/`
  - `output_backup/`
  - `vector_db/`
- [ ] Calculate file ages
- [ ] Identify files to clean

**Code:**
```python
data_dir = Path("data")
data_files = {
    "ab_tests": [],
    "analytics": [],
    "curated_posts": [],
    "learning_loop": [],
    "output_backup": [],
    "vector_db": []
}

for subdir in ["ab_tests", "analytics", "curated_posts", "learning_loop", "output_backup", "vector_db"]:
    subdir_path = data_dir / subdir
    if not subdir_path.exists():
        continue
    
    for file in subdir_path.glob("*"):
        if file.is_file():
            file_mtime = file.stat().st_mtime
            age_days = (current_time - file_mtime) / (24 * 60 * 60)
            data_files[subdir].append((file, age_days))
```

### Checkpoint 3: Create Archive Directories
- [ ] Create `var/archive/` if it doesn't exist
- [ ] Create `data/archive/` if it doesn't exist
- [ ] Create subdirectories for organization
- [ ] Verify write permissions

**Code:**
```python
var_archive = Path("var/archive")
data_archive = Path("data/archive")

var_archive.mkdir(parents=True, exist_ok=True)
data_archive.mkdir(parents=True, exist_ok=True)

# Create subdirectories
(var_archive / "databases").mkdir(exist_ok=True)
(var_archive / "json").mkdir(exist_ok=True)
(data_archive / "analytics").mkdir(exist_ok=True)
(data_archive / "backups").mkdir(exist_ok=True)
```

### Checkpoint 4: Clean var/ Directory Files
- [ ] Archive JSON files older than 30 days but less than 90 days
- [ ] Delete JSON files older than 90 days
- [ ] Archive old session files
- [ ] Clean old log files
- [ ] Keep recent database files (last 30 days)
- [ ] Archive old database files (30-90 days)
- [ ] Delete very old database files (>90 days)

**Code:**
```python
for file, age_days in var_files["json_files"]:
    if age_days > 90:
        # Delete
        size = file.stat().st_size
        file.unlink()
        logger.info(f"Deleted old JSON file: {file.name} ({age_days:.0f} days old)")
        stats["files_removed"] += 1
        stats["bytes_freed"] += size
    elif age_days > 30:
        # Archive
        archive_path = var_archive / "json" / file.name
        shutil.move(str(file), str(archive_path))
        logger.info(f"Archived JSON file: {file.name}")
        stats["files_archived"] += 1
```

### Checkpoint 5: Clean data/ Directory Files
- [ ] Clean `analytics/` old files (keep last 30 days)
- [ ] Clean `output_backup/` old backups (keep last 3, archive older)
- [ ] Clean `learning_loop/` old files
- [ ] Keep `curated_posts/` files (important data)
- [ ] Keep `vector_db/` files (important data)
- [ ] Keep `ab_tests/` files (configuration)

**Code:**
```python
# Clean analytics files
for file, age_days in data_files["analytics"]:
    if age_days > 90:
        size = file.stat().st_size
        file.unlink()
        logger.info(f"Deleted old analytics file: {file.name}")
        stats["files_removed"] += 1
        stats["bytes_freed"] += size

# Clean output_backup files
backup_files = sorted(data_files["output_backup"], key=lambda x: x[1], reverse=True)
keep_count = 3

for i, (file, age_days) in enumerate(backup_files):
    if i < keep_count:
        continue  # Keep recent backups
    
    if age_days > 90:
        size = file.stat().st_size
        file.unlink()
        logger.info(f"Deleted old backup: {file.name}")
        stats["files_removed"] += 1
        stats["bytes_freed"] += size
    elif age_days > 30:
        archive_path = data_archive / "backups" / file.name
        shutil.move(str(file), str(archive_path))
        logger.info(f"Archived backup: {file.name}")
        stats["files_archived"] += 1
```

### Checkpoint 6: Clean Database Files
- [ ] Identify old database files in `var/`
- [ ] Keep recent databases (last 30 days)
- [ ] Archive old databases (30-90 days)
- [ ] Delete very old databases (>90 days)
- [ ] Be careful with active databases

**Code:**
```python
for file, age_days in var_files["databases"]:
    # Check if database is in use (by checking if it's locked or recently accessed)
    if is_database_in_use(file):
        logger.info(f"Skipping active database: {file.name}")
        continue
    
    if age_days > 90:
        size = file.stat().st_size
        file.unlink()
        logger.info(f"Deleted old database: {file.name} ({age_days:.0f} days old)")
        stats["files_removed"] += 1
        stats["bytes_freed"] += size
    elif age_days > 30:
        archive_path = var_archive / "databases" / file.name
        shutil.move(str(file), str(archive_path))
        logger.info(f"Archived database: {file.name}")
        stats["files_archived"] += 1
```

### Checkpoint 7: Clean Session Files
- [ ] Identify old session files
- [ ] Archive or delete based on age
- [ ] Keep recent sessions (last 7 days)
- [ ] Archive sessions 7-30 days old
- [ ] Delete sessions older than 30 days

### Checkpoint 8: Verify Cleanup
- [ ] Verify recent files are kept
- [ ] Verify old files are archived or deleted
- [ ] Check disk space saved
- [ ] Verify no active files were deleted
- [ ] Count files before/after

**Verification:**
```python
# Count remaining files
remaining_var = len(list(var_dir.rglob("*"))) - len(list(var_dir.rglob("archive")))
remaining_data = len(list(data_dir.rglob("*"))) - len(list(data_dir.rglob("archive")))

print(f"var/ files: {remaining_var} remaining")
print(f"data/ files: {remaining_data} remaining")

# Check disk space
disk_space_saved = stats["bytes_freed"]
print(f"Disk space saved: {disk_space_saved / 1024:.2f} KB")
```

### Checkpoint 9: Generate Report
- [ ] Generate cleanup report
- [ ] Include files cleaned by directory
- [ ] Include disk space saved
- [ ] Include files kept (with reasons)
- [ ] Save report to `docs/cleanup_reports/var_data_cleanup_YYYYMMDD_HHMMSS.json`

**Report Format:**
```json
{
  "timestamp": "2025-11-23T17:00:00Z",
  "operation": "clean_var_data_directories",
  "summary": {
    "var_files_archived": 3,
    "var_files_deleted": 2,
    "data_files_archived": 1,
    "data_files_deleted": 1,
    "total_archived": 4,
    "total_deleted": 3,
    "disk_space_saved_bytes": 524288,
    "disk_space_saved_kb": 512.0
  },
  "by_directory": {
    "var": {
      "json_files": {"archived": 2, "deleted": 1},
      "databases": {"archived": 1, "deleted": 1},
      "sessions": {"archived": 0, "deleted": 0}
    },
    "data": {
      "analytics": {"archived": 0, "deleted": 1},
      "output_backup": {"archived": 1, "deleted": 0}
    }
  }
}
```

## Acceptance Criteria

- [ ] Recent files (0-30 days) kept
- [ ] Old files (30-90 days) archived
- [ ] Very old files (>90 days) deleted
- [ ] Database files handled carefully
- [ ] Session files cleaned
- [ ] No active files deleted
- [ ] Cleanup report generated
- [ ] Disk space freed
- [ ] Archive structure organized

## Safety Exclusions

**Files to NEVER delete:**
- Recent data files (last 30 days)
- Active database files
- Configuration files
- Files currently in use
- Important curated data

## Retention Policy

- **Recent files:** Keep last 30 days
- **Old files:** Archive 30-90 days
- **Very old files:** Delete after 90 days
- **Database files:** Keep last 30 days, archive 30-90 days, delete >90 days
- **Session files:** Keep last 7 days, archive 7-30 days, delete >30 days
- **Backup files:** Keep last 3, archive older, delete >90 days

## Related Issues

- General codebase cleanup

## Notes

- This is a safe operation (archive before delete)
- Be careful with database files (check if in use)
- Run dry-run first to verify
- Can be automated to run monthly
- Significant space savings possible

## Success Metrics

- **Target:** 500+ KB disk space saved
- **Target:** Old files archived or deleted
- **Target:** Recent files preserved
- **Target:** 0 errors during cleanup

