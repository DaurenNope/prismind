#!/usr/bin/env python3
"""
Script to clean up file naming and organization in the project.
- Renames files to follow snake_case convention
- Removes version suffixes and backup files
- Cleans up temporary and IDE-specific files
"""

import os
import re
import shutil
from pathlib import Path
from typing import List, Set, Tuple

# Define the project root
PROJECT_ROOT = Path(__file__).parent.parent.resolve()

# Files and directories to exclude from processing
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
}

# File patterns to remove
REMOVE_PATTERNS = [
    # Version suffixes
    r'_v\d+',  # _v1, _v2, etc.
    r'_new',
    r'_working',
    r'_copy',
    r'_old',
    r'_backup',
    r'\(\d+\)',  # (1), (2), etc.
    
    # Backup files
    r'\.bak$',
    r'\.backup$',
    r'~$',  # Backup files ending with ~
    
    # Temporary files
    r'\.tmp$',
    r'\.swp$',
    r'\.swo$',
    r'\.swn$',
    r'\..*\.sw[opn]$',  # Vim swap files
    r'\..*\..*\..*\..*',  # Files with 4+ dots
    r'^\._',  # macOS attribute files
    r'\.DS_Store$',  # macOS directory metadata
    r'Thumbs\.db$',  # Windows thumbnail cache
    r'desktop\.ini$',  # Windows folder customizations
    
    # IDE and editor files
    r'\.sublime-',
    r'\.vscode',
    r'\.idea',
    r'\.pytest_cache',
    r'\.mypy_cache',
    r'\.ruff_cache',
    r'\.coverage',
    'coverage\.xml',
    'htmlcov',
    '\.pytest',
    '\.ropeproject',
    '\.mypy_cache',
    '\.pydevproject',
    '\.project',
    '\.settings',
    '\.cache',
]

def find_files(directory: Path) -> List[Path]:
    """Find all files in the given directory and its subdirectories."""
    all_files = []
    
    for root, dirs, files in os.walk(directory):
        # Skip excluded directories
        dirs[:] = [d for d in dirs if not any(
            d == pattern or pattern.startswith('*') and d.endswith(pattern[1:])
            for pattern in EXCLUDED_DIRS
        )]
        
        for file in files:
            file_path = Path(root) / file
            all_files.append(file_path)
    
    return all_files

def should_remove_file(file_path: Path) -> bool:
    """Check if a file should be removed based on its name."""
    file_name = file_path.name
    
    # Check against remove patterns
    for pattern in REMOVE_PATTERNS:
        if re.search(pattern, file_name, re.IGNORECASE):
            return True
    
    return False

def rename_to_snake_case(file_path: Path) -> Tuple[bool, Path]:
    """Rename a file to follow snake_case convention."""
    # Skip if already in snake_case
    if file_path.name == file_path.name.lower() and '_' in file_path.name:
        return False, file_path
    
    # Convert to snake_case
    new_name = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', file_path.name)
    new_name = new_name.lower()
    new_name = re.sub(r'[^a-z0-9_.]', '_', new_name)
    new_name = re.sub(r'_+', '_', new_name)
    
    # Don't change the file extension
    if '.' in file_path.name:
        name_parts = file_path.name.rsplit('.', 1)
        new_name = f"{new_name.rsplit('.', 1)[0]}.{name_parts[1]}"
    
    new_path = file_path.parent / new_name
    
    # Skip if the name hasn't changed
    if new_path == file_path:
        return False, file_path
    
    # Handle naming conflicts
    counter = 1
    while new_path.exists():
        name_parts = new_path.stem, new_path.suffix
        new_name = f"{name_parts[0]}_{counter}{name_parts[1]}"
        new_path = new_path.parent / new_name
        counter += 1
    
    return True, new_path

def main():
    """Main function to clean up file naming and organization."""
    # Find all files in the project
    all_files = find_files(PROJECT_ROOT)
    
    print(f"Found {len(all_files)} files to process...")
    
    removed_count = 0
    renamed_count = 0
    
    for file_path in all_files:
        try:
            # Check if the file should be removed
            if should_remove_file(file_path):
                print(f"Removing: {file_path}")
                if file_path.is_file():
                    file_path.unlink()
                    removed_count += 1
                elif file_path.is_dir():
                    shutil.rmtree(file_path)
                    removed_count += 1
                continue
            
            # Rename to snake_case
            should_rename, new_path = rename_to_snake_case(file_path)
            if should_rename:
                print(f"Renaming: {file_path} -> {new_path}")
                file_path.rename(new_path)
                renamed_count += 1
        
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
    
    print(f"\nCleanup complete!")
    print(f"- Removed {removed_count} files/directories")
    print(f"- Renamed {renamed_count} files to snake_case")

if __name__ == "__main__":
    main()
