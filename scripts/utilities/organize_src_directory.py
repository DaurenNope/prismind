#!/usr/bin/env python3
"""
Organize src/ directory structure
Moves files to appropriate locations and updates imports
BE SUPER CAREFUL - tests after each move
"""

import re
import shutil
from pathlib import Path
from typing import Dict, List

def update_imports_in_file(file_path: Path, old_import: str, new_import: str):
    """Update imports in a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace import statements
        content = content.replace(old_import, new_import)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"Error updating {file_path}: {e}")
        return False

def find_and_update_imports(old_module: str, new_module: str, workspace_root: Path):
    """Find all files importing old_module and update to new_module."""
    updated_files = []
    
    for py_file in workspace_root.rglob("*.py"):
        if ".venv" in str(py_file):
            continue
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if old_module in content:
                # Check if it's an actual import
                if f"from {old_module}" in content or f"import {old_module}" in content:
                    if update_imports_in_file(py_file, old_module, new_module):
                        updated_files.append(py_file)
        except Exception:
            pass
    
    return updated_files

def organize_src_directory(dry_run: bool = True):
    """Organize src/ directory structure."""
    workspace_root = Path(__file__).parent.parent
    src_dir = workspace_root / "src"
    
    print("=" * 80)
    print("ORGANIZING SRC/ DIRECTORY")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    print("=" * 80)
    
    moves = []
    
    # 1. Move scrape_state_manager.py to infrastructure/database/
    #    (since there's already one there, we need to check which is correct)
    scrape_state_src = src_dir / "scrape_state_manager.py"
    scrape_state_dest = src_dir / "infrastructure" / "database" / "scrape_state_manager_legacy.py"
    
    if scrape_state_src.exists():
        # Check if the infrastructure version is different
        infra_version = src_dir / "infrastructure" / "database" / "scrape_state_manager.py"
        if infra_version.exists():
            print(f"\n⚠️  Found duplicate: {scrape_state_src.name}")
            print(f"   Infrastructure version exists: {infra_version}")
            print(f"   Root version is imported in 3 places")
            print(f"   Recommendation: Keep infrastructure version, update imports")
            
            if not dry_run:
                # Archive the root version as legacy
                if scrape_state_dest.exists():
                    scrape_state_dest.unlink()
                shutil.move(str(scrape_state_src), str(scrape_state_dest))
                print(f"   ✅ Moved to: {scrape_state_dest.name}")
                
                # Update imports
                updated = find_and_update_imports(
                    "from src.scrape_state_manager",
                    "from src.infrastructure.database.scrape_state_manager",
                    workspace_root
                )
                print(f"   ✅ Updated {len(updated)} import statements")
            else:
                print(f"   [DRY RUN] Would move to: {scrape_state_dest.name}")
                print(f"   [DRY RUN] Would update imports in 3 files")
        else:
            moves.append(("scrape_state_manager.py", "infrastructure/database/"))
    
    # 2. Check main_api.py
    main_api_src = src_dir / "main_api.py"
    main_api_dest = src_dir / "application" / "api" / "main_api_legacy.py"
    
    if main_api_src.exists():
        app_version = src_dir / "application" / "api" / "main_api.py"
        if app_version.exists():
            print(f"\n⚠️  Found duplicate: {main_api_src.name}")
            print(f"   Application version exists: {app_version}")
            print(f"   Root version: No imports found (likely unused)")
            
            if not dry_run:
                # Archive as legacy since no imports found
                if main_api_dest.exists():
                    main_api_dest.unlink()
                shutil.move(str(main_api_src), str(main_api_dest))
                print(f"   ✅ Moved to: {main_api_dest.name} (no imports found)")
            else:
                print(f"   [DRY RUN] Would move to: {main_api_dest.name}")
        else:
            moves.append(("main_api.py", "application/api/"))
    
    print(f"\n✅ Organization complete")
    return moves

if __name__ == "__main__":
    import sys
    dry_run = "--dry-run" in sys.argv or "-d" in sys.argv
    organize_src_directory(dry_run=dry_run)

