#!/usr/bin/env python3
"""
Comprehensive Python Cache Cleanup Script
Removes all __pycache__ directories and .pyc files
"""
import os
import shutil
import sys
from pathlib import Path
from datetime import datetime
import json

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def should_exclude(path: Path) -> bool:
    """Check if path should be excluded from cleanup"""
    path_str = str(path.absolute())
    exclude_patterns = [
        "/.venv/",
        "/venv/",
        "/env/",
        "/node_modules/",
        "/.git/",
    ]
    # Only exclude if path is inside these directories
    return any(pattern in path_str for pattern in exclude_patterns)


def get_cache_items():
    """Find all cache files and directories"""
    cache_items = {
        "directories": [],
        "pyc_files": [],
        "pyo_files": [],
        "pyd_files": [],
        "test_cache": [],
        "type_cache": [],
        "linter_cache": []
    }
    
    total_size = 0
    project_root = Path(".")
    
    # Find cache directories
    cache_dir_patterns = ["__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"]
    for pattern in cache_dir_patterns:
        for item in project_root.rglob(pattern):
            if should_exclude(item) or not item.is_dir():
                continue
            
            # Calculate size
            size = sum(
                f.stat().st_size for f in item.rglob("*") if f.is_file()
            )
            
            if pattern == "__pycache__":
                cache_items["directories"].append((item, size))
            elif pattern == ".pytest_cache":
                cache_items["test_cache"].append((item, size))
            elif pattern == ".mypy_cache":
                cache_items["type_cache"].append((item, size))
            elif pattern == ".ruff_cache":
                cache_items["linter_cache"].append((item, size))
            
            total_size += size
    
    # Find cache files
    cache_file_patterns = ["*.pyc", "*.pyo", "*.pyd"]
    for pattern in cache_file_patterns:
        for item in project_root.rglob(pattern):
            if should_exclude(item) or not item.is_file():
                continue
            
            size = item.stat().st_size
            
            if pattern == "*.pyc":
                cache_items["pyc_files"].append((item, size))
            elif pattern == "*.pyo":
                cache_items["pyo_files"].append((item, size))
            elif pattern == "*.pyd":
                cache_items["pyd_files"].append((item, size))
            
            total_size += size
    
    return cache_items, total_size


def dry_run():
    """Perform dry run - list what would be deleted"""
    print("=" * 60)
    print("PYTHON CACHE CLEANUP - DRY RUN")
    print("=" * 60)
    
    cache_items, total_size = get_cache_items()
    
    print(f"\n[DRY RUN] Would delete:")
    print(f"  - {len(cache_items['directories'])} __pycache__ directories")
    print(f"  - {len(cache_items['pyc_files'])} .pyc files")
    print(f"  - {len(cache_items['pyo_files'])} .pyo files")
    print(f"  - {len(cache_items['pyd_files'])} .pyd files")
    print(f"  - {len(cache_items['test_cache'])} test cache directories")
    print(f"  - {len(cache_items['type_cache'])} type checker cache directories")
    print(f"  - {len(cache_items['linter_cache'])} linter cache directories")
    
    total_items = (
        len(cache_items['directories']) +
        len(cache_items['pyc_files']) +
        len(cache_items['pyo_files']) +
        len(cache_items['pyd_files']) +
        len(cache_items['test_cache']) +
        len(cache_items['type_cache']) +
        len(cache_items['linter_cache'])
    )
    
    print(f"\n[DRY RUN] Total items: {total_items}")
    print(f"[DRY RUN] Would free: {total_size / 1024 / 1024:.2f} MB")
    
    return cache_items, total_size


def cleanup(dry_run_mode: bool = False):
    """Perform actual cleanup"""
    if dry_run_mode:
        return dry_run()
    
    print("=" * 60)
    print("PYTHON CACHE CLEANUP")
    print("=" * 60)
    
    cache_items, total_size = get_cache_items()
    
    stats = {
        "directories_removed": 0,
        "pyc_files_removed": 0,
        "pyo_files_removed": 0,
        "pyd_files_removed": 0,
        "test_cache_removed": 0,
        "type_cache_removed": 0,
        "linter_cache_removed": 0,
        "bytes_freed": 0,
        "errors": []
    }
    
    # Delete cache directories
    for item, size in cache_items["directories"]:
        try:
            shutil.rmtree(item)
            stats["directories_removed"] += 1
            stats["bytes_freed"] += size
            print(f"✅ Deleted: {item}")
        except Exception as e:
            error_msg = f"Failed to delete {item}: {e}"
            stats["errors"].append(error_msg)
            print(f"❌ {error_msg}")
    
    # Delete test cache
    for item, size in cache_items["test_cache"]:
        try:
            shutil.rmtree(item)
            stats["test_cache_removed"] += 1
            stats["bytes_freed"] += size
            print(f"✅ Deleted: {item}")
        except Exception as e:
            error_msg = f"Failed to delete {item}: {e}"
            stats["errors"].append(error_msg)
            print(f"❌ {error_msg}")
    
    # Delete type cache
    for item, size in cache_items["type_cache"]:
        try:
            shutil.rmtree(item)
            stats["type_cache_removed"] += 1
            stats["bytes_freed"] += size
            print(f"✅ Deleted: {item}")
        except Exception as e:
            error_msg = f"Failed to delete {item}: {e}"
            stats["errors"].append(error_msg)
            print(f"❌ {error_msg}")
    
    # Delete linter cache
    for item, size in cache_items["linter_cache"]:
        try:
            shutil.rmtree(item)
            stats["linter_cache_removed"] += 1
            stats["bytes_freed"] += size
            print(f"✅ Deleted: {item}")
        except Exception as e:
            error_msg = f"Failed to delete {item}: {e}"
            stats["errors"].append(error_msg)
            print(f"❌ {error_msg}")
    
    # Delete .pyc files
    for item, size in cache_items["pyc_files"]:
        try:
            item.unlink()
            stats["pyc_files_removed"] += 1
            stats["bytes_freed"] += size
        except Exception as e:
            error_msg = f"Failed to delete {item}: {e}"
            stats["errors"].append(error_msg)
            print(f"❌ {error_msg}")
    
    # Delete .pyo files
    for item, size in cache_items["pyo_files"]:
        try:
            item.unlink()
            stats["pyo_files_removed"] += 1
            stats["bytes_freed"] += size
        except Exception as e:
            error_msg = f"Failed to delete {item}: {e}"
            stats["errors"].append(error_msg)
            print(f"❌ {error_msg}")
    
    # Delete .pyd files
    for item, size in cache_items["pyd_files"]:
        try:
            item.unlink()
            stats["pyd_files_removed"] += 1
            stats["bytes_freed"] += size
        except Exception as e:
            error_msg = f"Failed to delete {item}: {e}"
            stats["errors"].append(error_msg)
            print(f"❌ {error_msg}")
    
    # Print summary
    print("\n" + "=" * 60)
    print("CLEANUP SUMMARY")
    print("=" * 60)
    print(f"Directories removed: {stats['directories_removed']}")
    print(f".pyc files removed: {stats['pyc_files_removed']}")
    print(f".pyo files removed: {stats['pyo_files_removed']}")
    print(f".pyd files removed: {stats['pyd_files_removed']}")
    print(f"Test cache removed: {stats['test_cache_removed']}")
    print(f"Type cache removed: {stats['type_cache_removed']}")
    print(f"Linter cache removed: {stats['linter_cache_removed']}")
    total_items = sum([
        stats['directories_removed'],
        stats['pyc_files_removed'],
        stats['pyo_files_removed'],
        stats['pyd_files_removed'],
        stats['test_cache_removed'],
        stats['type_cache_removed'],
        stats['linter_cache_removed']
    ])
    print(f"\nTotal items removed: {total_items}")
    print(f"Disk space freed: {stats['bytes_freed'] / 1024 / 1024:.2f} MB")
    
    if stats["errors"]:
        print(f"\nErrors: {len(stats['errors'])}")
        for error in stats["errors"][:10]:  # Show first 10 errors
            print(f"  - {error}")
    
    # Generate report
    report = {
        "timestamp": datetime.now().isoformat(),
        "operation": "comprehensive_python_cache_cleanup",
        "summary": {
            **stats,
            "total_items_removed": sum([
                stats['directories_removed'],
                stats['pyc_files_removed'],
                stats['pyo_files_removed'],
                stats['pyd_files_removed'],
                stats['test_cache_removed'],
                stats['type_cache_removed'],
                stats['linter_cache_removed']
            ]),
            "disk_space_saved_mb": round(stats['bytes_freed'] / 1024 / 1024, 2)
        }
    }
    
    # Save report
    reports_dir = project_root / "docs" / "cleanup_reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_file = reports_dir / f"python_cache_cleanup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\n✅ Report saved to: {report_file}")
    
    return stats


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Clean Python cache files")
    parser.add_argument("--dry-run", action="store_true", help="Perform dry run only")
    args = parser.parse_args()
    
    if args.dry_run:
        dry_run()
    else:
        print("⚠️  This will delete all Python cache files and directories.")
        print("⚠️  Cache files will be regenerated automatically by Python.")
        response = input("Continue? (yes/no): ")
        if response.lower() == "yes":
            cleanup()
        else:
            print("Cancelled.")

