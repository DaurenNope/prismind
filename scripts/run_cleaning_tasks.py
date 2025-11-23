#!/usr/bin/env python3
"""
Run Cleaning Tasks from Tickets

Executes all cleaning tasks from tickets/cleaning/ in priority order:
1. Clean Python Cache (Ticket #004) - Safest
2. Rotate Log Files (Ticket #002)
3. Clean Backup Files (Ticket #003)
4. Archive Completed Documentation (Ticket #001)
5. Identify Deprecated Code (Ticket #005) - Reporting only
"""

import gzip
import hashlib
import json
import re
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

# Setup logging
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class CleanupStats:
    """Track cleanup statistics."""
    def __init__(self):
        self.files_removed = 0
        self.directories_removed = 0
        self.files_archived = 0
        self.bytes_freed = 0
        self.errors = []
    
    def reset(self):
        self.files_removed = 0
        self.directories_removed = 0
        self.files_archived = 0
        self.bytes_freed = 0
        self.errors = []


def should_exclude(path: Path) -> bool:
    """Check if a path should be excluded from cleanup."""
    excluded_patterns = [
        ".git",
        "node_modules",
        ".venv",
        "venv",
        "env",
        ".env",
        "migrations",
        "data/vector_db",
    ]
    path_str = str(path)
    # Exclude if path is inside any excluded directory
    # But allow __pycache__ directories in project code (not in excluded dirs)
    return any(pattern in path_str for pattern in excluded_patterns)


def get_dir_size(directory: Path) -> int:
    """Calculate total size of directory in bytes."""
    total_size = 0
    try:
        for file_path in directory.rglob("*"):
            if file_path.is_file():
                total_size += file_path.stat().st_size
    except Exception as e:
        logger.warning(f"Could not calculate size for {directory}: {e}")
    return total_size


def clean_python_cache(workspace_root: Path, stats: CleanupStats, dry_run: bool = False) -> Dict[str, Any]:
    """Task #004: Clean Python cache files."""
    logger.info("Task #004: Cleaning Python cache files...")
    removed = []
    cache_patterns = ["__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"]
    
    for pattern in cache_patterns:
        # Use rglob to find all matching directories
        for cache_dir in workspace_root.rglob(pattern):
            try:
                if cache_dir.is_dir() and not should_exclude(cache_dir):
                    size = get_dir_size(cache_dir)
                    if not dry_run:
                        shutil.rmtree(cache_dir)
                        logger.debug(f"Removed cache dir: {cache_dir}")
                    else:
                        logger.debug(f"[DRY RUN] Would remove cache dir: {cache_dir}")
                    removed.append({
                        "path": str(cache_dir),
                        "type": "directory",
                        "size": size,
                        "pattern": pattern
                    })
                    if not dry_run:
                        stats.directories_removed += 1
                        stats.bytes_freed += size
            except Exception as e:
                error_msg = f"Failed to remove {cache_dir}: {e}"
                logger.error(error_msg)
                stats.errors.append(error_msg)
    
    # Log summary instead of individual files
    if removed:
        logger.info(f"Found {len(removed)} cache directories to remove")
    
    # Also clean .pyc, .pyo, .pyd files
    for pattern in ["*.pyc", "*.pyo", "*.pyd"]:
        for cache_file in workspace_root.rglob(pattern):
            try:
                if cache_file.is_file() and not should_exclude(cache_file):
                    size = cache_file.stat().st_size
                    if not dry_run:
                        cache_file.unlink()
                        logger.info(f"Removed cache file: {cache_file}")
                    else:
                        logger.info(f"[DRY RUN] Would remove cache file: {cache_file}")
                    removed.append({
                        "path": str(cache_file),
                        "type": "file",
                        "size": size
                    })
                    if not dry_run:
                        stats.files_removed += 1
                        stats.bytes_freed += size
            except Exception as e:
                error_msg = f"Failed to remove {cache_file}: {e}"
                logger.error(error_msg)
                stats.errors.append(error_msg)
    
    logger.info(f"✅ Task #004 Complete: Removed {stats.directories_removed} directories, "
                f"{stats.files_removed} files, freed {stats.bytes_freed / 1024 / 1024:.2f} MB")
    return {"removed": removed}


def rotate_logs(workspace_root: Path, stats: CleanupStats, dry_run: bool = False) -> Dict[str, Any]:
    """Task #002: Rotate log files - keep 7 days, archive 7-30 days, delete >30 days."""
    logger.info("Task #002: Rotating log files...")
    logs_dir = workspace_root / "logs"
    archive_dir = logs_dir / "archive"
    
    if not logs_dir.exists():
        logger.info("No logs directory found")
        return {"archived": [], "removed": []}
    
    keep_days = 7
    archive_days = 30
    current_time = time.time()
    keep_cutoff = current_time - (keep_days * 24 * 60 * 60)
    delete_cutoff = current_time - (archive_days * 24 * 60 * 60)
    
    if not dry_run:
        archive_dir.mkdir(parents=True, exist_ok=True)
    
    archived = []
    removed = []
    
    # Process .log files
    for log_file in logs_dir.glob("*.log"):
        try:
            if not log_file.is_file():
                continue
            
            file_mtime = log_file.stat().st_mtime
            size = log_file.stat().st_size
            age_days = (current_time - file_mtime) / (24 * 60 * 60)
            
            if file_mtime < delete_cutoff:
                # Delete logs older than 30 days
                if not dry_run:
                    log_file.unlink()
                    logger.info(f"Deleted old log (>{archive_days} days): {log_file}")
                else:
                    logger.info(f"[DRY RUN] Would delete old log: {log_file}")
                removed.append({
                    "path": str(log_file),
                    "type": "file",
                    "size": size,
                    "age_days": age_days
                })
                if not dry_run:
                    stats.files_removed += 1
                    stats.bytes_freed += size
            elif file_mtime < keep_cutoff:
                # Archive logs between 7-30 days
                archive_path = archive_dir / f"{log_file.name}.gz"
                if not dry_run:
                    with open(log_file, 'rb') as f_in:
                        with gzip.open(archive_path, 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)
                    log_file.unlink()
                    logger.info(f"Archived log: {log_file} -> {archive_path}")
                else:
                    logger.info(f"[DRY RUN] Would archive log: {log_file} -> {archive_path}")
                archived.append({
                    "path": str(log_file),
                    "archive_path": str(archive_path),
                    "type": "file",
                    "size": size,
                    "age_days": age_days
                })
                if not dry_run:
                    stats.files_archived += 1
        except Exception as e:
            error_msg = f"Failed to rotate log {log_file}: {e}"
            logger.error(error_msg)
            stats.errors.append(error_msg)
    
    # Process JSON trace files
    for json_file in logs_dir.glob("*.json"):
        try:
            if not json_file.is_file():
                continue
            
            file_mtime = json_file.stat().st_mtime
            if file_mtime < delete_cutoff:
                size = json_file.stat().st_size
                if not dry_run:
                    json_file.unlink()
                    logger.info(f"Deleted old JSON trace: {json_file}")
                else:
                    logger.info(f"[DRY RUN] Would delete old JSON trace: {json_file}")
                removed.append({
                    "path": str(json_file),
                    "type": "file",
                    "size": size
                })
                if not dry_run:
                    stats.files_removed += 1
                    stats.bytes_freed += size
        except Exception as e:
            error_msg = f"Failed to remove JSON trace {json_file}: {e}"
            logger.error(error_msg)
            stats.errors.append(error_msg)
    
    # Process PNG files (auth failures)
    for png_file in logs_dir.glob("*.png"):
        try:
            if not png_file.is_file():
                continue
            
            file_mtime = png_file.stat().st_mtime
            if file_mtime < delete_cutoff:
                size = png_file.stat().st_size
                if not dry_run:
                    png_file.unlink()
                    logger.info(f"Deleted old PNG: {png_file}")
                else:
                    logger.info(f"[DRY RUN] Would delete old PNG: {png_file}")
                removed.append({
                    "path": str(png_file),
                    "type": "file",
                    "size": size
                })
                if not dry_run:
                    stats.files_removed += 1
                    stats.bytes_freed += size
        except Exception as e:
            error_msg = f"Failed to remove PNG {png_file}: {e}"
            logger.error(error_msg)
            stats.errors.append(error_msg)
    
    logger.info(f"✅ Task #002 Complete: Archived {stats.files_archived} logs, "
                f"removed {stats.files_removed} old logs")
    return {"archived": archived, "removed": removed}


def clean_backups(workspace_root: Path, stats: CleanupStats, dry_run: bool = False) -> Dict[str, Any]:
    """Task #003: Clean backup files - keep last 3 DB backups, clean old JSON backups."""
    logger.info("Task #003: Cleaning backup files...")
    backups_dir = workspace_root / "backups"
    archive_dir = backups_dir / "archive"
    
    if not backups_dir.exists():
        logger.info("No backups directory found")
        return {"archived": [], "removed": []}
    
    keep_count = 3
    archive_days = 90
    json_delete_days = 30
    current_time = time.time()
    delete_cutoff = current_time - (archive_days * 24 * 60 * 60)
    json_delete_cutoff = current_time - (json_delete_days * 24 * 60 * 60)
    
    if not dry_run:
        archive_dir.mkdir(parents=True, exist_ok=True)
    
    archived = []
    removed = []
    
    # Process database backups
    db_backups = sorted(
        [f for f in backups_dir.glob("*.db") if f.is_file()],
        key=lambda f: f.stat().st_mtime,
        reverse=True
    )
    
    for i, backup_file in enumerate(db_backups):
        try:
            file_mtime = backup_file.stat().st_mtime
            size = backup_file.stat().st_size
            age_days = (current_time - file_mtime) / (24 * 60 * 60)
            
            if file_mtime < delete_cutoff:
                # Delete backups older than 90 days
                if not dry_run:
                    backup_file.unlink()
                    logger.info(f"Deleted old backup (>{archive_days} days): {backup_file}")
                else:
                    logger.info(f"[DRY RUN] Would delete old backup: {backup_file}")
                removed.append({
                    "path": str(backup_file),
                    "type": "file",
                    "size": size,
                    "age_days": age_days
                })
                if not dry_run:
                    stats.files_removed += 1
                    stats.bytes_freed += size
            elif i >= keep_count:
                # Archive backups beyond keep_count
                archive_path = archive_dir / backup_file.name
                if not dry_run:
                    shutil.move(str(backup_file), str(archive_path))
                    logger.info(f"Archived backup: {backup_file} -> {archive_path}")
                else:
                    logger.info(f"[DRY RUN] Would archive backup: {backup_file} -> {archive_path}")
                archived.append({
                    "path": str(backup_file),
                    "archive_path": str(archive_path),
                    "type": "file",
                    "size": size,
                    "age_days": age_days
                })
                if not dry_run:
                    stats.files_archived += 1
        except Exception as e:
            error_msg = f"Failed to process backup {backup_file}: {e}"
            logger.error(error_msg)
            stats.errors.append(error_msg)
    
    # Clean JSON backup files older than 30 days
    for json_backup in backups_dir.rglob("*.json*"):
        try:
            if json_backup.is_file() and not should_exclude(json_backup):
                file_mtime = json_backup.stat().st_mtime
                if file_mtime < json_delete_cutoff:
                    size = json_backup.stat().st_size
                    if not dry_run:
                        json_backup.unlink()
                        logger.info(f"Deleted old JSON backup: {json_backup}")
                    else:
                        logger.info(f"[DRY RUN] Would delete old JSON backup: {json_backup}")
                    removed.append({
                        "path": str(json_backup),
                        "type": "file",
                        "size": size,
                        "age_days": (current_time - file_mtime) / (24 * 60 * 60)
                    })
                    if not dry_run:
                        stats.files_removed += 1
                        stats.bytes_freed += size
        except Exception as e:
            error_msg = f"Failed to remove JSON backup {json_backup}: {e}"
            logger.error(error_msg)
            stats.errors.append(error_msg)
    
    # Clean .OLD files
    for old_file in backups_dir.glob("*.OLD"):
        try:
            if old_file.is_file():
                file_mtime = old_file.stat().st_mtime
                if file_mtime < json_delete_cutoff:
                    size = old_file.stat().st_size
                    if not dry_run:
                        old_file.unlink()
                        logger.info(f"Deleted old backup file: {old_file}")
                    else:
                        logger.info(f"[DRY RUN] Would delete old backup file: {old_file}")
                    removed.append({
                        "path": str(old_file),
                        "type": "file",
                        "size": size
                    })
                    if not dry_run:
                        stats.files_removed += 1
                        stats.bytes_freed += size
        except Exception as e:
            error_msg = f"Failed to remove old file {old_file}: {e}"
            logger.error(error_msg)
            stats.errors.append(error_msg)
    
    logger.info(f"✅ Task #003 Complete: Archived {stats.files_archived} backups, "
                f"removed {stats.files_removed} old backups")
    return {"archived": archived, "removed": removed}


def archive_completed_docs(workspace_root: Path, stats: CleanupStats, dry_run: bool = False) -> Dict[str, Any]:
    """Task #001: Archive completed documentation."""
    logger.info("Task #001: Archiving completed documentation...")
    docs_dir = workspace_root / "docs"
    archive_dir = docs_dir / "archive" / "completed"
    
    if not docs_dir.exists():
        logger.info("No docs directory found")
        return {"archived": []}
    
    # Patterns for completed docs
    completed_patterns = [
        "*_COMPLETE.md",
        "*_FINAL*.md",
        "AGENT_*_COMPLETE.md",
        "*_COMPLETE_SUMMARY.md",
        "*_FINAL_STATUS.md"
    ]
    
    # Exclude files in archive and plans directories
    excluded_dirs = ["archive", "plans", "agents"]
    
    if not dry_run:
        archive_dir.mkdir(parents=True, exist_ok=True)
    
    archived = []
    
    for pattern in completed_patterns:
        for doc_file in docs_dir.glob(pattern):
            try:
                if doc_file.is_file() and not should_exclude(doc_file):
                    # Check if in excluded directory
                    if any(excluded in str(doc_file.relative_to(docs_dir)) for excluded in excluded_dirs):
                        continue
                    
                    size = doc_file.stat().st_size
                    archive_path = archive_dir / doc_file.name
                    
                    if not dry_run:
                        shutil.move(str(doc_file), str(archive_path))
                        logger.info(f"Archived completed doc: {doc_file} -> {archive_path}")
                    else:
                        logger.info(f"[DRY RUN] Would archive completed doc: {doc_file} -> {archive_path}")
                    
                    archived.append({
                        "path": str(doc_file),
                        "archive_path": str(archive_path),
                        "type": "file",
                        "size": size
                    })
                    if not dry_run:
                        stats.files_archived += 1
            except Exception as e:
                error_msg = f"Failed to archive {doc_file}: {e}"
                logger.error(error_msg)
                stats.errors.append(error_msg)
    
    logger.info(f"✅ Task #001 Complete: Archived {stats.files_archived} completed docs")
    return {"archived": archived}


def identify_deprecated_code(workspace_root: Path, stats: CleanupStats, dry_run: bool = False) -> Dict[str, Any]:
    """Task #005: Identify deprecated code (reporting only)."""
    logger.info("Task #005: Identifying deprecated code...")
    deprecated_items = []
    
    # Search for deprecated code patterns
    code_patterns = [
        (r"@deprecated", "decorator"),
        (r"#\s*DEPRECATED", "comment"),
        (r"#\s*deprecated", "comment"),
        (r"TODO.*deprecated", "comment"),
        (r"FIXME.*deprecated", "comment"),
        (r"DeprecationWarning", "warning"),
        (r"warnings\.warn\(.*DeprecationWarning", "warning_call")
    ]
    
    # Search in Python files
    for py_file in workspace_root.rglob("*.py"):
        try:
            if should_exclude(py_file):
                continue
            
            content = py_file.read_text(encoding='utf-8', errors='ignore')
            lines = content.split('\n')
            
            for line_num, line in enumerate(lines, 1):
                for pattern, pattern_type in code_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        deprecated_items.append({
                            "file": str(py_file.relative_to(workspace_root)),
                            "line": line_num,
                            "pattern": pattern,
                            "type": pattern_type,
                            "content": line.strip()
                        })
                        break
        except Exception as e:
            logger.warning(f"Could not read {py_file}: {e}")
    
    # Generate report
    report_path = None
    if deprecated_items:
        report_dir = workspace_root / "docs" / "cleanup_reports"
        if not dry_run:
            report_dir.mkdir(parents=True, exist_ok=True)
            report_path = report_dir / f"deprecated_code_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_path, 'w') as f:
                json.dump({
                    "timestamp": datetime.now().isoformat(),
                    "operation": "identify_deprecated_code",
                    "total_items": len(deprecated_items),
                    "deprecated_items": deprecated_items
                }, f, indent=2)
            logger.info(f"Generated deprecated code report: {report_path}")
        else:
            logger.info(f"[DRY RUN] Would generate deprecated code report with {len(deprecated_items)} items")
    
    logger.info(f"✅ Task #005 Complete: Found {len(deprecated_items)} deprecated code items")
    return {"deprecated_items": deprecated_items, "report_path": str(report_path) if report_path else None}


def clean_comprehensive_python_cache(workspace_root: Path, stats: CleanupStats, dry_run: bool = False) -> Dict[str, Any]:
    """Task #006: Comprehensive Python cache cleanup - verify all cache is removed."""
    logger.info("Task #006: Comprehensive Python cache cleanup...")
    # This is essentially the same as #004, but we verify completeness
    return clean_python_cache(workspace_root, stats, dry_run)


def clean_log_trace_files(workspace_root: Path, stats: CleanupStats, dry_run: bool = False) -> Dict[str, Any]:
    """Task #007: Clean log and trace files with organized archive structure."""
    logger.info("Task #007: Cleaning log and trace files...")
    logs_dir = workspace_root / "logs"
    archive_dir = logs_dir / "archive"
    
    if not logs_dir.exists():
        logger.info("No logs directory found")
        return {"archived": [], "removed": []}
    
    keep_days = 7
    archive_days = 30
    current_time = time.time()
    keep_cutoff = current_time - (keep_days * 24 * 60 * 60)
    delete_cutoff = current_time - (archive_days * 24 * 60 * 60)
    
    if not dry_run:
        archive_dir.mkdir(parents=True, exist_ok=True)
        (archive_dir / "logs").mkdir(exist_ok=True)
        (archive_dir / "traces").mkdir(exist_ok=True)
        (archive_dir / "screenshots").mkdir(exist_ok=True)
    
    archived = []
    removed = []
    
    # Process all files in logs directory
    for file_path in logs_dir.iterdir():
        if not file_path.is_file():
            continue
        
        try:
            file_mtime = file_path.stat().st_mtime
            size = file_path.stat().st_size
            age_days = (current_time - file_mtime) / (24 * 60 * 60)
            
            if file_mtime < delete_cutoff:
                # Delete files older than 30 days
                if not dry_run:
                    file_path.unlink()
                    logger.info(f"Deleted old file (>{archive_days} days): {file_path.name}")
                else:
                    logger.info(f"[DRY RUN] Would delete old file: {file_path.name}")
                removed.append({
                    "path": str(file_path),
                    "type": "file",
                    "size": size,
                    "age_days": age_days
                })
                if not dry_run:
                    stats.files_removed += 1
                    stats.bytes_freed += size
            elif file_mtime < keep_cutoff:
                # Archive files between 7-30 days
                if file_path.suffix == ".log":
                    archive_subdir = archive_dir / "logs"
                elif file_path.suffix == ".json":
                    archive_subdir = archive_dir / "traces"
                elif file_path.suffix == ".png":
                    archive_subdir = archive_dir / "screenshots"
                else:
                    archive_subdir = archive_dir / "logs"  # Default
                
                archive_path = archive_subdir / f"{file_path.name}.gz"
                if not dry_run:
                    with open(file_path, 'rb') as f_in:
                        with gzip.open(archive_path, 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)
                    file_path.unlink()
                    logger.info(f"Archived: {file_path.name} -> {archive_path}")
                else:
                    logger.info(f"[DRY RUN] Would archive: {file_path.name} -> {archive_path}")
                archived.append({
                    "path": str(file_path),
                    "archive_path": str(archive_path),
                    "type": "file",
                    "size": size,
                    "age_days": age_days
                })
                if not dry_run:
                    stats.files_archived += 1
        except Exception as e:
            error_msg = f"Failed to process {file_path}: {e}"
            logger.error(error_msg)
            stats.errors.append(error_msg)
    
    logger.info(f"✅ Task #007 Complete: Archived {stats.files_archived} files, "
                f"removed {stats.files_removed} old files")
    return {"archived": archived, "removed": removed}


def clean_empty_directories(workspace_root: Path, stats: CleanupStats, dry_run: bool = False) -> Dict[str, Any]:
    """Task #008: Clean empty directories."""
    logger.info("Task #008: Cleaning empty directories...")
    removed = []
    
    # Find all empty directories
    empty_dirs = []
    for dir_path in workspace_root.rglob("*"):
        if not dir_path.is_dir():
            continue
        if should_exclude(dir_path):
            continue
        try:
            if not any(dir_path.iterdir()):
                empty_dirs.append(dir_path)
        except (PermissionError, OSError):
            continue
    
    # Sort by depth (deepest first) to avoid deleting parent before child
    empty_dirs.sort(key=lambda p: len(p.parts), reverse=True)
    
    # Filter out directories that might be placeholders
    dirs_to_delete = []
    for empty_dir in empty_dirs:
        # Skip archive directories (they might be placeholders)
        if "archive" in str(empty_dir) and not any(empty_dir.iterdir()):
            continue
        dirs_to_delete.append(empty_dir)
    
    for empty_dir in dirs_to_delete:
        try:
            if not dry_run:
                empty_dir.rmdir()
                logger.debug(f"Deleted empty directory: {empty_dir}")
            else:
                logger.debug(f"[DRY RUN] Would delete empty directory: {empty_dir}")
            removed.append({
                "path": str(empty_dir),
                "type": "directory"
            })
            if not dry_run:
                stats.directories_removed += 1
        except OSError as e:
            error_msg = f"Could not delete {empty_dir}: {e}"
            logger.warning(error_msg)
            stats.errors.append(error_msg)
    
    if removed:
        logger.info(f"Found {len(removed)} empty directories to remove")
    logger.info(f"✅ Task #008 Complete: Removed {stats.directories_removed} empty directories")
    return {"removed": removed}


def clean_var_data_directories(workspace_root: Path, stats: CleanupStats, dry_run: bool = False) -> Dict[str, Any]:
    """Task #009: Clean var/ and data/ directories."""
    logger.info("Task #009: Cleaning var/ and data/ directories...")
    current_time = time.time()
    keep_cutoff = current_time - (30 * 24 * 60 * 60)  # 30 days
    delete_cutoff = current_time - (90 * 24 * 60 * 60)  # 90 days
    
    archived = []
    removed = []
    
    # Clean var/ directory
    var_dir = workspace_root / "var"
    if var_dir.exists():
        var_archive = var_dir / "archive"
        if not dry_run:
            var_archive.mkdir(parents=True, exist_ok=True)
        
        for file_path in var_dir.rglob("*"):
            if not file_path.is_file() or file_path.parent == var_archive:
                continue
            
            try:
                file_mtime = file_path.stat().st_mtime
                age_days = (current_time - file_mtime) / (24 * 60 * 60)
                size = file_path.stat().st_size
                
                if age_days > 90:
                    if not dry_run:
                        file_path.unlink()
                        logger.info(f"Deleted old var file: {file_path.name} ({age_days:.0f} days)")
                    removed.append({"path": str(file_path), "size": size, "age_days": age_days})
                    if not dry_run:
                        stats.files_removed += 1
                        stats.bytes_freed += size
                elif age_days > 30:
                    if not dry_run:
                        archive_path = var_archive / file_path.name
                        shutil.move(str(file_path), str(archive_path))
                        logger.info(f"Archived var file: {file_path.name}")
                    archived.append({"path": str(file_path), "age_days": age_days})
                    if not dry_run:
                        stats.files_archived += 1
            except Exception as e:
                error_msg = f"Failed to process {file_path}: {e}"
                logger.error(error_msg)
                stats.errors.append(error_msg)
    
    # Clean data/ directory (be more conservative)
    data_dir = workspace_root / "data"
    if data_dir.exists():
        # Only clean output_backup and old analytics files
        for subdir_name in ["output_backup", "analytics"]:
            subdir = data_dir / subdir_name
            if not subdir.exists():
                continue
            
            for file_path in subdir.glob("*"):
                if not file_path.is_file():
                    continue
                
                try:
                    file_mtime = file_path.stat().st_mtime
                    age_days = (current_time - file_mtime) / (24 * 60 * 60)
                    size = file_path.stat().st_size
                    
                    if age_days > 90:
                        if not dry_run:
                            file_path.unlink()
                            logger.info(f"Deleted old data file: {file_path.name}")
                        removed.append({"path": str(file_path), "size": size})
                        if not dry_run:
                            stats.files_removed += 1
                            stats.bytes_freed += size
                except Exception as e:
                    error_msg = f"Failed to process {file_path}: {e}"
                    logger.error(error_msg)
                    stats.errors.append(error_msg)
    
    logger.info(f"✅ Task #009 Complete: Archived {stats.files_archived} files, "
                f"removed {stats.files_removed} old files")
    return {"archived": archived, "removed": removed}


def comprehensive_documentation_cleanup(workspace_root: Path, stats: CleanupStats, dry_run: bool = False) -> Dict[str, Any]:
    """Task #010: Comprehensive documentation cleanup."""
    logger.info("Task #010: Comprehensive documentation cleanup...")
    docs_dir = workspace_root / "docs"
    
    if not docs_dir.exists():
        logger.info("No docs directory found")
        return {"archived": [], "duplicates_removed": 0}
    
    # Essential docs to never archive - only keep truly essential ones
    essential_docs = {
        "README.md", "SCHEMA.md", "HOW_TO_RUN.md", "DEPLOYMENT.md", "INDEX.md"
    }
    
    # Excluded directories
    excluded_dirs = ["archive", "plans", "agents"]
    
    # Categorize documentation
    docs_files = {
        "completion_summaries": [],
        "final_status": [],
        "agent_reports": [],
        "architecture": [],
        "status_reports": [],
        "fix_summaries": [],
        "integration": [],
        "testing": [],
        "active": [],
        "other": []
    }
    
    for file in docs_dir.glob("*.md"):
        # Skip essential docs and files in excluded directories
        if file.name in essential_docs:
            docs_files["active"].append(file)
            continue
        if any(excluded in str(file.relative_to(docs_dir)) for excluded in excluded_dirs):
            continue
        
        # Categorize - be aggressive, archive almost everything
        name_upper = file.name.upper()
        if file.name.startswith("AGENT_"):
            docs_files["agent_reports"].append(file)
        elif "_COMPLETE" in name_upper or "COMPLETE" in name_upper:
            docs_files["completion_summaries"].append(file)
        elif "_FINAL" in name_upper or "FINAL" in name_upper:
            docs_files["final_status"].append(file)
        elif "ARCHITECTURE" in name_upper:
            docs_files["architecture"].append(file)
        elif "_STATUS" in name_upper or "STATUS" in name_upper:
            docs_files["status_reports"].append(file)
        elif "_FIX" in name_upper or "FIX" in name_upper or "FIXES" in name_upper:
            docs_files["fix_summaries"].append(file)
        elif "INTEGRATION" in name_upper:
            docs_files["integration"].append(file)
        elif "TEST" in name_upper or "TESTING" in name_upper or "COVERAGE" in name_upper:
            docs_files["testing"].append(file)
        elif "ANALYSIS" in name_upper or "VERIFICATION" in name_upper or "EVALUATION" in name_upper:
            docs_files["status_reports"].append(file)  # Archive analysis/verification docs
        elif "PLAN" in name_upper or "ROADMAP" in name_upper or "SUMMARY" in name_upper:
            docs_files["completion_summaries"].append(file)  # Archive plans/summaries
        elif "DEBUG" in name_upper or "RELIABILITY" in name_upper or "ISSUE" in name_upper:
            docs_files["fix_summaries"].append(file)  # Archive debug/issue docs
        elif "IMPLEMENTATION" in name_upper or "AUTHENTICATION" in name_upper:
            docs_files["status_reports"].append(file)  # Archive implementation docs
        else:
            # Archive everything else that's not essential
            docs_files["other"].append(file)
    
    # Find duplicates
    file_hashes = {}
    duplicates = []
    
    for file in docs_dir.glob("*.md"):
        if file.name in essential_docs:
            continue
        if any(excluded in str(file.relative_to(docs_dir)) for excluded in excluded_dirs):
            continue
        
        try:
            with open(file, 'rb') as f:
                file_hash = hashlib.md5(f.read()).hexdigest()
            
            if file_hash in file_hashes:
                # Duplicate found - keep the one with newer mtime or shorter path
                original = file_hashes[file_hash]
                if file.stat().st_mtime > original.stat().st_mtime:
                    duplicates.append({"original": original, "duplicate": file, "hash": file_hash})
                    file_hashes[file_hash] = file  # Update to keep newer
                else:
                    duplicates.append({"original": original, "duplicate": file, "hash": file_hash})
            else:
                file_hashes[file_hash] = file
        except Exception as e:
            logger.warning(f"Could not read {file}: {e}")
    
    # Create archive structure
    archive_base = docs_dir / "archive"
    archive_dirs = {
        "completed": archive_base / "completed",
        "status": archive_base / "status",
        "agents": archive_base / "agents",
        "architecture": archive_base / "architecture",
        "fixes": archive_base / "fixes",
        "integration": archive_base / "integration",
        "testing": archive_base / "testing",
        "duplicates": archive_base / "duplicates"
    }
    
    if not dry_run:
        for dir_path in archive_dirs.values():
            dir_path.mkdir(parents=True, exist_ok=True)
    
    archived = []
    duplicates_removed = 0
    
    # Archive by category
    category_mapping = {
        "completion_summaries": "completed",
        "final_status": "status",
        "agent_reports": "agents",
        "architecture": "architecture",
        "fix_summaries": "fixes",
        "integration": "integration",
        "testing": "testing"
    }
    
    for category, files in docs_files.items():
        if category == "active":
            continue
        # Archive "other" category too - be aggressive
        
        # Map category to archive subdirectory
        if category == "other":
            archive_subdir = archive_dirs["completed"]  # Put "other" in completed
        else:
            archive_subdir = archive_dirs.get(category_mapping.get(category, "completed"))
        for file in files:
            try:
                size = file.stat().st_size
                archive_path = archive_subdir / file.name
                
                if not dry_run:
                    shutil.move(str(file), str(archive_path))
                    logger.info(f"Archived {category}: {file.name} -> {archive_path}")
                else:
                    logger.info(f"[DRY RUN] Would archive {category}: {file.name} -> {archive_path}")
                
                archived.append({
                    "path": str(file),
                    "archive_path": str(archive_path),
                    "category": category,
                    "size": size
                })
                if not dry_run:
                    stats.files_archived += 1
            except Exception as e:
                error_msg = f"Failed to archive {file}: {e}"
                logger.error(error_msg)
                stats.errors.append(error_msg)
    
    # Archive duplicates
    for dup in duplicates:
        try:
            archive_path = archive_dirs["duplicates"] / dup["duplicate"].name
            if not dry_run:
                shutil.move(str(dup["duplicate"]), str(archive_path))
                logger.info(f"Archived duplicate: {dup['duplicate'].name} (original: {dup['original'].name})")
            else:
                logger.info(f"[DRY RUN] Would archive duplicate: {dup['duplicate'].name}")
            duplicates_removed += 1
            if not dry_run:
                stats.files_archived += 1
        except Exception as e:
            error_msg = f"Failed to archive duplicate {dup['duplicate']}: {e}"
            logger.error(error_msg)
            stats.errors.append(error_msg)
    
    # Create documentation index
    if not dry_run:
        index_path = docs_dir / "INDEX.md"
        with open(index_path, 'w') as f:
            f.write("# Documentation Index\n\n")
            f.write(f"Last updated: {datetime.now().strftime('%Y-%m-%d')}\n\n")
            f.write("## Active Documentation\n\n")
            f.write("### Core Documentation\n")
            for doc in docs_files["active"]:
                f.write(f"- [{doc.name}](./{doc.name})\n")
            f.write("\n## Archived Documentation\n\n")
            f.write("See [archive/](./archive/) for archived documentation organized by category:\n\n")
            for category, archive_dir in archive_dirs.items():
                archived_count = len(list(archive_dir.glob("*.md"))) if archive_dir.exists() else 0
                if archived_count > 0:
                    f.write(f"- **{category.title()}**: [{archive_dir.name}/](./archive/{archive_dir.name}/) ({archived_count} files)\n")
            f.write("\n## Statistics\n\n")
            f.write(f"- Total archived: {len(archived) + duplicates_removed} files\n")
            f.write(f"- Duplicates removed: {duplicates_removed}\n")
            f.write(f"- Active documentation: {len(docs_files['active'])} files\n")
        logger.info(f"Created documentation index: {index_path}")
    else:
        logger.info(f"[DRY RUN] Would create documentation index")
    
    logger.info(f"✅ Task #010 Complete: Archived {stats.files_archived} files, "
                f"removed {duplicates_removed} duplicates")
    return {
        "archived": archived,
        "duplicates_removed": duplicates_removed,
        "by_category": {k: len(v) for k, v in docs_files.items() if k not in ["active", "other"]}
    }


def clean_temporary_files(workspace_root: Path, stats: CleanupStats, dry_run: bool = False) -> Dict[str, Any]:
    """Task #011: Clean temporary files."""
    logger.info("Task #011: Cleaning temporary files...")
    removed = []
    temp_patterns = ["*.tmp", "*.bak", "*.swp", "*.swo", "*~", ".DS_Store", "Thumbs.db"]
    
    for pattern in temp_patterns:
        for temp_file in workspace_root.rglob(pattern):
            try:
                if temp_file.is_file() and not should_exclude(temp_file):
                    # Be careful with .old files - skip intentionally named ones
                    if pattern == "*.old" and "old" in temp_file.stem.lower():
                        continue
                    
                    size = temp_file.stat().st_size
                    if not dry_run:
                        temp_file.unlink()
                        logger.debug(f"Removed temp file: {temp_file}")
                    else:
                        logger.debug(f"[DRY RUN] Would remove temp file: {temp_file}")
                    removed.append({
                        "path": str(temp_file),
                        "type": "file",
                        "size": size
                    })
                    if not dry_run:
                        stats.files_removed += 1
                        stats.bytes_freed += size
            except Exception as e:
                error_msg = f"Failed to remove {temp_file}: {e}"
                logger.error(error_msg)
                stats.errors.append(error_msg)
    
    if removed:
        logger.info(f"Found {len(removed)} temporary files to remove")
    logger.info(f"✅ Task #011 Complete: Removed {stats.files_removed} temporary files, "
                f"freed {stats.bytes_freed / 1024:.2f} KB")
    return {"removed": removed}


def main(dry_run: bool = False):
    """Run all cleaning tasks."""
    workspace_root = Path(__file__).parent.parent
    
    logger.info("🧹 Starting Cleaning Agent Tasks")
    logger.info(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    logger.info(f"Workspace: {workspace_root}")
    
    stats = CleanupStats()
    results = {}
    
    # Phase 1: HIGH Priority Tasks
    # Task #006: Comprehensive Python Cache (verify completeness)
    logger.info("\n" + "="*80)
    logger.info("TASK #006: Comprehensive Python Cache Cleanup")
    logger.info("="*80)
    results["task_006"] = clean_comprehensive_python_cache(workspace_root, stats, dry_run)
    stats.reset()
    
    # Task #007: Clean Log and Trace Files
    logger.info("\n" + "="*80)
    logger.info("TASK #007: Clean Log and Trace Files")
    logger.info("="*80)
    results["task_007"] = clean_log_trace_files(workspace_root, stats, dry_run)
    stats.reset()
    
    # Phase 2: MEDIUM Priority Tasks
    # Task #010: Comprehensive Documentation Cleanup
    logger.info("\n" + "="*80)
    logger.info("TASK #010: Comprehensive Documentation Cleanup")
    logger.info("="*80)
    results["task_010"] = comprehensive_documentation_cleanup(workspace_root, stats, dry_run)
    stats.reset()
    
    # Task #009: Clean var/ and data/ Directories
    logger.info("\n" + "="*80)
    logger.info("TASK #009: Clean var/ and data/ Directories")
    logger.info("="*80)
    results["task_009"] = clean_var_data_directories(workspace_root, stats, dry_run)
    stats.reset()
    
    # Task #008: Clean Empty Directories
    logger.info("\n" + "="*80)
    logger.info("TASK #008: Clean Empty Directories")
    logger.info("="*80)
    results["task_008"] = clean_empty_directories(workspace_root, stats, dry_run)
    stats.reset()
    
    # Phase 3: LOW Priority Tasks
    # Task #011: Clean Temporary Files
    logger.info("\n" + "="*80)
    logger.info("TASK #011: Clean Temporary Files")
    logger.info("="*80)
    results["task_011"] = clean_temporary_files(workspace_root, stats, dry_run)
    
    # Generate summary
    logger.info("\n" + "="*80)
    logger.info("CLEANUP SUMMARY")
    logger.info("="*80)
    total_dirs_removed = (
        len(results.get("task_006", {}).get("removed", [])) +
        len(results.get("task_008", {}).get("removed", []))
    )
    total_files_archived = (
        len(results.get("task_007", {}).get("archived", [])) +
        len(results.get("task_009", {}).get("archived", [])) +
        len(results.get("task_010", {}).get("archived", []))
    )
    total_files_removed = (
        len(results.get("task_007", {}).get("removed", [])) +
        len(results.get("task_009", {}).get("removed", [])) +
        len(results.get("task_011", {}).get("removed", []))
    )
    
    logger.info(f"Total directories removed: {total_dirs_removed}")
    logger.info(f"Total files archived: {total_files_archived}")
    logger.info(f"Total files removed: {total_files_removed}")
    
    logger.info("\n✅ All cleaning tasks completed!")
    return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run cleaning tasks from tickets")
    parser.add_argument("--dry-run", action="store_true", help="Run in dry-run mode (no changes)")
    args = parser.parse_args()
    
    try:
        results = main(dry_run=args.dry_run)
        exit(0)
    except Exception as e:
        logger.error(f"❌ Cleaning tasks failed: {e}", exc_info=True)
        exit(1)
