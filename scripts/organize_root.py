#!/usr/bin/env python3
"""
Script to organize the root directory of the PrisMind project.
Moves files to their appropriate directories based on file type and purpose.
"""

import os
import shutil
from pathlib import Path
from typing import List, Dict, Optional

# Define file type mappings
FILE_MAPPINGS = {
    # Python files
    '*.py': 'src/',
    
    # Configuration files
    '*.yaml': 'config/',
    '*.yml': 'config/',
    '*.json': 'config/',
    '*.toml': 'config/',
    '.env*': 'config/',
    
    # Documentation
    '*.md': 'docs/',
    '*.rst': 'docs/',
    '*.txt': 'docs/',
    
    # Data files
    '*.csv': 'data/',
    '*.xlsx': 'data/',
    '*.xls': 'data/',
    '*.db': 'data/',
    '*.sqlite': 'data/',
    '*.sql': 'data/',
    
    # Scripts
    '*.sh': 'scripts/',
    '*.ps1': 'scripts/',
    '*.bat': 'scripts/',
    
    # Images and assets
    '*.png': 'assets/images/',
    '*.jpg': 'assets/images/',
    '*.jpeg': 'assets/images/',
    '*.gif': 'assets/images/',
    '*.svg': 'assets/images/',
    '*.ico': 'assets/images/',
    '*.css': 'assets/css/',
    '*.scss': 'assets/css/',
    '*.js': 'assets/js/',
    '*.ts': 'assets/js/',
}

# Files to exclude from moving
EXCLUDED_FILES = {
    'README.md',
    'LICENSE',
    '.gitignore',
    '.gitattributes',
    '.env',  # Keep .env in root for compatibility
    'requirements.txt',
    'pyproject.toml',
    'setup.py',
    'setup.cfg',
    'Makefile',
    'Dockerfile',
    'docker-compose.yml',
    '.dockerignore',
    'start.sh',
    'startup.sh',
    'run.py',
    'main.py',
    'app.py',  # Keep main app entry point in root
}

# Directories to exclude from processing
EXCLUDED_DIRS = {
    '.git',
    '.github',
    '.vscode',
    '.idea',
    '__pycache__',
    'venv',
    'env',
    '.venv',
    'node_modules',
    'build',
    'dist',
    '*.egg-info',
    '.pytest_cache',
    '.mypy_cache',
    '.ruff_cache',
    'docs',
    'tests',
    'src',
    'config',
    'scripts',
    'data',
    'assets',
}

def get_file_destination(filename: str) -> Optional[str]:
    """Determine the destination directory for a file based on its extension."""
    # Check for exact filename matches first
    if filename in EXCLUDED_FILES:
        return None
    
    # Check for file patterns
    for pattern, dest_dir in FILE_MAPPINGS.items():
        if pattern.startswith('*'):
            if filename.lower().endswith(pattern[1:].lower()):
                return dest_dir
        elif filename.lower() == pattern.lower():
            return dest_dir
    
    return None

def move_file_to_destination(filepath: Path, dry_run: bool = True) -> bool:
    """Move a file to its appropriate destination directory."""
    if filepath.name in EXCLUDED_FILES:
        print(f"Skipping excluded file: {filepath}")
        return False
    
    # Skip directories
    if filepath.is_dir():
        return False
    
    # Skip hidden files (except .env* which we handle separately)
    if filepath.name.startswith('.') and not filepath.name.startswith('.env'):
        return False
    
    dest_dir = get_file_destination(filepath.name)
    
    if not dest_dir:
        return False
    
    # Create destination directory if it doesn't exist
    dest_path = filepath.parent / dest_dir
    dest_path.mkdir(parents=True, exist_ok=True)
    
    # Skip if already in the correct location
    if filepath.parent.samefile(dest_path):
        return False
    
    # Handle naming conflicts
    new_path = dest_path / filepath.name
    counter = 1
    while new_path.exists():
        if filepath.samefile(new_path):
            return False
        
        # Add a counter to the filename
        name_parts = filepath.stem, filepath.suffix
        new_name = f"{name_parts[0]}_{counter}{name_parts[1]}"
        new_path = dest_path / new_name
        counter += 1
    
    if dry_run:
        print(f"Would move: {filepath} -> {new_path}")
    else:
        try:
            print(f"Moving: {filepath} -> {new_path}")
            shutil.move(str(filepath), str(new_path))
            return True
        except Exception as e:
            print(f"Error moving {filepath}: {e}")
            return False
    
    return False

def clean_empty_directories(root: Path) -> None:
    """Remove empty directories in the given directory."""
    for dirpath, dirnames, filenames in os.walk(root, topdown=False):
        # Skip excluded directories
        if any(dirpath.startswith(str(root / d)) for d in EXCLUDED_DIRS if not d.startswith('*')):
            continue
        
        # Skip directories that match excluded patterns
        dir_name = os.path.basename(dirpath)
        if any(d[1:] in dir_name for d in EXCLUDED_DIRS if d.startswith('*')):
            continue
        
        # Skip if directory is not empty
        if os.listdir(dirpath):
            continue
        
        # Skip root directory
        if os.path.samefile(dirpath, root):
            continue
        
        print(f"Removing empty directory: {dirpath}")
        try:
            os.rmdir(dirpath)
        except OSError as e:
            print(f"Error removing directory {dirpath}: {e}")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Organize files in the root directory.')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    parser.add_argument('--clean-empty', action='store_true', help='Remove empty directories')
    parser.add_argument('--root', type=str, default='.', help='Root directory to organize')
    
    args = parser.parse_args()
    
    root = Path(args.root).resolve()
    print(f"Organizing files in: {root}")
    
    # Process files in the root directory
    moved_count = 0
    for item in root.glob('*'):
        # Skip excluded directories
        if item.is_dir() and item.name in EXCLUDED_DIRS:
            print(f"Skipping excluded directory: {item}")
            continue
        
        # Skip if it's a directory that matches excluded patterns
        if item.is_dir() and any(d[1:] in item.name for d in EXCLUDED_DIRS if d.startswith('*')):
            print(f"Skipping excluded directory pattern: {item}")
            continue
        
        # Process files and top-level directories
        if item.is_file():
            if move_file_to_destination(item, dry_run=args.dry_run):
                moved_count += 1
        else:
            # Process files in subdirectories (one level deep)
            for subitem in item.glob('*'):
                if subitem.is_file():
                    if move_file_to_destination(subitem, dry_run=args.dry_run):
                        moved_count += 1
    
    # Clean up empty directories if requested
    if args.clean_empty and not args.dry_run:
        print("\nCleaning up empty directories...")
        clean_empty_directories(root)
    
    # Print summary
    print(f"\n{'Would move' if args.dry_run else 'Moved'} {moved_count} files")
    if args.dry_run:
        print("\nThis was a dry run. No files were actually moved.")
        print("Run without --dry-run to actually move files.")

if __name__ == "__main__":
    main()
