#!/usr/bin/env python3
"""
Organize tests/ directory to mirror src/ structure
Categorizes test files and moves them to appropriate locations
"""

import shutil
from pathlib import Path
from typing import Dict, List

def categorize_test_file(filename: str) -> str:
    """Categorize a test file based on its name and content."""
    filename_lower = filename.lower()
    
    # Collection tests
    if any(x in filename_lower for x in ['collection', 'collector', 'reddit', 'twitter', 'threads']):
        return 'collection'
    
    # Analysis tests
    if any(x in filename_lower for x in ['analyzer', 'analysis', 'post_analyzer']):
        return 'analysis'
    
    # Database tests
    if any(x in filename_lower for x in ['database', 'sqlite', 'supabase', 'storage', 'sync']):
        return 'database'
    
    # Publishing/Rewriter tests
    if any(x in filename_lower for x in ['rewriter', 'rewrite', 'publishing', 'persona', 'mimesis']):
        return 'publishing'
    
    # Integration tests
    if 'integration' in filename_lower or 'e2e' in filename_lower:
        return 'integration'
    
    # API tests
    if 'api' in filename_lower or 'authentication' in filename_lower:
        return 'api'
    
    # Core/Infrastructure tests
    if any(x in filename_lower for x in ['orchestrator', 'circuit', 'observability', 'performance']):
        return 'core'
    
    # Agent tests
    if 'agent' in filename_lower:
        return 'agents'
    
    # Default to unit
    return 'unit'

def organize_tests_directory(dry_run: bool = True):
    """Organize tests/ directory."""
    workspace_root = Path(__file__).parent.parent
    tests_dir = workspace_root / "tests"
    
    print("=" * 80)
    print("ORGANIZING TESTS/ DIRECTORY")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    print("=" * 80)
    
    # Create directory structure
    categories = ['unit', 'collection', 'analysis', 'database', 'publishing', 'api', 'core', 'agents']
    for cat in categories:
        cat_dir = tests_dir / cat
        if not cat_dir.exists():
            if not dry_run:
                cat_dir.mkdir(exist_ok=True)
                (cat_dir / "__init__.py").touch()
            print(f"  📁 Would create: tests/{cat}/")
    
    # Categorize and move files
    root_tests = [f for f in tests_dir.iterdir() 
                   if f.is_file() and f.name.startswith('test_') and f.suffix == '.py']
    
    moves = []
    for test_file in root_tests:
        category = categorize_test_file(test_file.name)
        dest = tests_dir / category / test_file.name
        
        moves.append((test_file.name, category))
        if not dry_run:
            shutil.move(str(test_file), str(dest))
            print(f"  ✅ Moved {test_file.name} → {category}/")
        else:
            print(f"  [DRY RUN] Would move {test_file.name} → {category}/")
    
    print(f"\n✅ Organization complete")
    print(f"   Total files to move: {len(moves)}")
    return moves

if __name__ == "__main__":
    import sys
    dry_run = "--dry-run" not in sys.argv and "-d" not in sys.argv
    organize_tests_directory(dry_run=dry_run)

