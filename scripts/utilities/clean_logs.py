#!/usr/bin/env python3
"""
Clean Log and Trace Files Script
Archives logs 7-30 days old, deletes logs older than 30 days
"""
import os
import shutil
import sys
import gzip
import time
from pathlib import Path
from datetime import datetime, timedelta
import json

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def categorize_files(logs_dir: Path):
    """Categorize files by age"""
    current_time = time.time()
    keep_cutoff = current_time - (7 * 24 * 60 * 60)  # 7 days
    delete_cutoff = current_time - (30 * 24 * 60 * 60)  # 30 days
    
    files_to_keep = []
    files_to_archive = []
    files_to_delete = []
    
    # Find all log, json, and png files
    log_files = list(logs_dir.glob("*.log"))
    json_files = list(logs_dir.glob("*.json"))
    png_files = list(logs_dir.glob("*.png"))
    
    all_files = log_files + json_files + png_files
    
    for file in all_files:
        if not file.is_file():
            continue
        
        file_mtime = file.stat().st_mtime
        age_days = (current_time - file_mtime) / (24 * 60 * 60)
        
        if age_days <= 7:
            files_to_keep.append(file)
        elif age_days <= 30:
            files_to_archive.append(file)
        else:
            files_to_delete.append(file)
    
    return files_to_keep, files_to_archive, files_to_delete


def create_archive_structure(logs_dir: Path):
    """Create archive directory structure"""
    archive_dir = logs_dir / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    
    (archive_dir / "logs").mkdir(exist_ok=True)
    (archive_dir / "traces").mkdir(exist_ok=True)
    (archive_dir / "screenshots").mkdir(exist_ok=True)
    
    return archive_dir


def archive_file(file: Path, archive_dir: Path):
    """Archive a file by compressing it"""
    if file.suffix == ".log":
        archive_path = archive_dir / "logs" / f"{file.name}.gz"
    elif file.suffix == ".json":
        archive_path = archive_dir / "traces" / f"{file.name}.gz"
    elif file.suffix == ".png":
        archive_path = archive_dir / "screenshots" / f"{file.name}.gz"
    else:
        archive_path = archive_dir / "logs" / f"{file.name}.gz"
    
    try:
        with open(file, 'rb') as f_in:
            with gzip.open(archive_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        original_size = file.stat().st_size
        file.unlink()
        return original_size
    except Exception as e:
        print(f"❌ Failed to archive {file}: {e}")
        return 0


def cleanup_logs(dry_run: bool = False):
    """Clean up log and trace files"""
    logs_dir = Path("logs")
    
    if not logs_dir.exists():
        print(f"⚠️  Logs directory not found: {logs_dir}")
        return
    
    print("=" * 60)
    print("LOG AND TRACE FILES CLEANUP")
    print("=" * 60)
    
    files_to_keep, files_to_archive, files_to_delete = categorize_files(logs_dir)
    
    print(f"\nFiles to keep (0-7 days): {len(files_to_keep)}")
    print(f"Files to archive (7-30 days): {len(files_to_archive)}")
    print(f"Files to delete (>30 days): {len(files_to_delete)}")
    
    if dry_run:
        print("\n[DRY RUN] Would archive:")
        for file in files_to_archive:
            age_days = (time.time() - file.stat().st_mtime) / (24 * 60 * 60)
            print(f"  - {file.name} ({age_days:.1f} days old)")
        
        print("\n[DRY RUN] Would delete:")
        for file in files_to_delete:
            age_days = (time.time() - file.stat().st_mtime) / (24 * 60 * 60)
            print(f"  - {file.name} ({age_days:.1f} days old)")
        
        total_size = sum(f.stat().st_size for f in files_to_archive + files_to_delete)
        print(f"\n[DRY RUN] Would free: {total_size / 1024 / 1024:.2f} MB")
        return
    
    stats = {
        "logs_archived": 0,
        "logs_deleted": 0,
        "traces_archived": 0,
        "traces_deleted": 0,
        "screenshots_archived": 0,
        "screenshots_deleted": 0,
        "files_kept": len(files_to_keep),
        "bytes_freed": 0,
        "errors": []
    }
    
    # Create archive structure
    archive_dir = create_archive_structure(logs_dir)
    
    # Archive files
    for file in files_to_archive:
        try:
            size = archive_file(file, archive_dir)
            stats["bytes_freed"] += size
            
            if file.suffix == ".log":
                stats["logs_archived"] += 1
            elif file.suffix == ".json":
                stats["traces_archived"] += 1
            elif file.suffix == ".png":
                stats["screenshots_archived"] += 1
            
            print(f"✅ Archived: {file.name}")
        except Exception as e:
            error_msg = f"Failed to archive {file}: {e}"
            stats["errors"].append(error_msg)
            print(f"❌ {error_msg}")
    
    # Delete old files
    for file in files_to_delete:
        try:
            size = file.stat().st_size
            file.unlink()
            stats["bytes_freed"] += size
            
            if file.suffix == ".log":
                stats["logs_deleted"] += 1
            elif file.suffix == ".json":
                stats["traces_deleted"] += 1
            elif file.suffix == ".png":
                stats["screenshots_deleted"] += 1
            
            print(f"✅ Deleted: {file.name}")
        except Exception as e:
            error_msg = f"Failed to delete {file}: {e}"
            stats["errors"].append(error_msg)
            print(f"❌ {error_msg}")
    
    # Print summary
    print("\n" + "=" * 60)
    print("CLEANUP SUMMARY")
    print("=" * 60)
    print(f"Logs archived: {stats['logs_archived']}")
    print(f"Logs deleted: {stats['logs_deleted']}")
    print(f"Traces archived: {stats['traces_archived']}")
    print(f"Traces deleted: {stats['traces_deleted']}")
    print(f"Screenshots archived: {stats['screenshots_archived']}")
    print(f"Screenshots deleted: {stats['screenshots_deleted']}")
    print(f"Files kept: {stats['files_kept']}")
    print(f"Disk space freed: {stats['bytes_freed'] / 1024 / 1024:.2f} MB")
    
    if stats["errors"]:
        print(f"\nErrors: {len(stats['errors'])}")
        for error in stats["errors"][:10]:
            print(f"  - {error}")
    
    # Generate report
    report = {
        "timestamp": datetime.now().isoformat(),
        "operation": "clean_log_trace_files",
        "summary": {
            **stats,
            "total_archived": stats["logs_archived"] + stats["traces_archived"] + stats["screenshots_archived"],
            "total_deleted": stats["logs_deleted"] + stats["traces_deleted"] + stats["screenshots_deleted"],
            "disk_space_saved_mb": round(stats["bytes_freed"] / 1024 / 1024, 2)
        }
    }
    
    # Save report
    reports_dir = project_root / "docs" / "cleanup_reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_file = reports_dir / f"log_cleanup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\n✅ Report saved to: {report_file}")
    
    return stats


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Clean log and trace files")
    parser.add_argument("--dry-run", action="store_true", help="Perform dry run only")
    args = parser.parse_args()
    
    if args.dry_run:
        cleanup_logs(dry_run=True)
    else:
        print("⚠️  This will archive logs 7-30 days old and delete logs older than 30 days.")
        response = input("Continue? (yes/no): ")
        if response.lower() == "yes":
            cleanup_logs()
        else:
            print("Cancelled.")

