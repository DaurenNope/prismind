#!/usr/bin/env python3
"""
Script to update import statements in Python files to reflect the new project structure.
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Define the project root
PROJECT_ROOT = Path(__file__).parent.parent.resolve()

# Define the source directory
SRC_DIR = PROJECT_ROOT / 'src'

# Map of old import paths to new import paths
IMPORT_MAPPINGS = {
    # Old pattern: New pattern
    '^from core\.': 'from src.core.',
    '^from services\.': 'from src.services.',
    '^from utils\.': 'from src.utils.',
    '^from web\.': 'from src.web.',
    '^from \.core\.': 'from src.core.',
    '^from \.services\.': 'from src.services.',
    '^from \.utils\.': 'from src.utils.',
    '^from \.web\.': 'from src.web.',
    '^import core\.': 'import src.core.',
    '^import services\.': 'import src.services.',
    '^import utils\.': 'import src.utils.',
    '^import web\.': 'import src.web.',
    '^import \.core\.': 'import src.core.',
    '^import \.services\.': 'import src.services.',
    '^import \.utils\.': 'import src.utils.',
    '^import \.web\.': 'import src.web.',
}

def find_python_files(directory: Path) -> List[Path]:
    """Find all Python files in the given directory and its subdirectories."""
    python_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                python_files.append(Path(root) / file)
    return python_files

def update_imports_in_file(file_path: Path) -> Tuple[int, int]:
    """Update import statements in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        updated = False
        updated_lines = 0
        
        # Apply each import mapping
        for old_pattern, new_pattern in IMPORT_MAPPINGS.items():
            new_content, num_subs = re.subn(
                old_pattern,
                new_pattern,
                content,
                flags=re.MULTILINE
            )
            if num_subs > 0:
                content = new_content
                updated = True
                updated_lines += num_subs
        
        # Write the updated content back to the file if changes were made
        if updated:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return (1, updated_lines)
        
        return (0, 0)
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return (0, 0)

def main():
    """Main function to update imports in all Python files."""
    # Find all Python files in the project
    python_files = find_python_files(PROJECT_ROOT)
    
    print(f"Found {len(python_files)} Python files to process...")
    
    # Update imports in each file
    updated_files = 0
    total_updates = 0
    
    for file_path in python_files:
        file_updates, line_updates = update_imports_in_file(file_path)
        updated_files += file_updates
        total_updates += line_updates
    
    print(f"Updated imports in {updated_files} files with {total_updates} changes.")

if __name__ == "__main__":
    main()
