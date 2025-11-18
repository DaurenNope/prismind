#!/usr/bin/env python3
"""
Find all Python files that are actually imported/used in the beyondlines app.
"""

import re
from collections import defaultdict
from pathlib import Path


def extract_imports(filepath):
    """Extract module imports from a Python file."""
    imports = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                # Match: from X import Y
                match = re.match(r"from\s+([\w\.]+)\s+import", line)
                if match:
                    imports.append(match.group(1))
                # Match: import X
                match = re.match(r"^import\s+([\w\.]+)", line)
                if match:
                    imports.append(match.group(1))
    except:
        pass
    return imports


def import_to_file(import_path, src_root):
    """Convert import path to possible file locations."""
    parts = import_path.split(".")
    if not parts[0] == "src":
        return []

    # Remove 'src' prefix
    parts = parts[1:]

    candidates = []
    # Try as package: src/foo/bar/__init__.py
    candidates.append(src_root / "/".join(parts) / "__init__.py")
    # Try as module: src/foo/bar.py
    candidates.append(src_root / (("/".join(parts)) + ".py"))

    return [c for c in candidates if c.exists()]


# Start from entry point
src_root = Path("/Users/mac/Documents/Development/beyondlines/src")
entry_point = src_root / "web" / "app.py"

used_files = set()
to_process = {entry_point}
processed = set()

print("Tracing imports from entry point...")

while to_process:
    current_file = to_process.pop()
    if current_file in processed:
        continue

    processed.add(current_file)
    used_files.add(current_file)

    # Extract imports
    imports = extract_imports(current_file)

    # Convert imports to files
    for imp in imports:
        if imp.startswith("src."):
            files = import_to_file(imp, src_root)
            for f in files:
                if f not in processed:
                    to_process.add(f)

print(f"\n=== ACTIVELY USED FILES ({len(used_files)}) ===\n")
for f in sorted(used_files):
    print(f.relative_to(src_root.parent))

# Group by directory
by_dir = defaultdict(list)
for f in used_files:
    relative = f.relative_to(src_root)
    dir_name = str(relative.parent) if relative.parent != Path(".") else "root"
    by_dir[dir_name].append(str(relative.name))

print(f"\n=== BY DIRECTORY ===\n")
for dir_name in sorted(by_dir.keys()):
    print(f"{dir_name}/:")
    for fname in sorted(by_dir[dir_name]):
        print(f"  {fname}")
