#!/usr/bin/env python3
"""
Codebase restructuring script

This script performs the actual restructuring:
1. Moves files to new locations
2. Updates import statements
3. Creates __init__.py files
"""

import os
import re
import shutil
from pathlib import Path
from typing import Dict, List, Tuple

# Mapping of old paths to new paths
FILE_MOVES = {
    # Collection domain
    "src/core/collection": "src/domain/collection",
    "src/core/extraction": "src/domain/collection/extractors",
    "src/services/collection": "src/domain/collection/services",
    "src/services/unified_collection_service.py": "src/domain/collection/services/unified_collection_service.py",
    "src/services/telegram_collection_commands.py": "src/domain/collection/services/telegram_collection_commands.py",
    
    # Analysis domain
    "src/core/analysis": "src/domain/analysis/analyzers",
    "src/services/analysis": "src/domain/analysis/services",
    "src/services/analysis_runner.py": "src/domain/analysis/services/analysis_runner.py",
    "src/services/post_analyzer.py": "src/domain/analysis/services/post_analyzer.py",
    
    # Publishing domain (already in place, but ensure structure)
    "src/publishing": "src/domain/publishing",
    
    # Intelligence domain
    "src/agents": "src/domain/intelligence/agents",
    "src/research": "src/domain/intelligence/research",
    "src/intelligence": "src/domain/intelligence",
    
    # Infrastructure
    "src/database": "src/infrastructure/database",
    "src/messaging": "src/infrastructure/messaging",
    "src/monitoring": "src/infrastructure/monitoring",
    "src/observability": "src/infrastructure/observability",
    "src/storage": "src/infrastructure/database/storage",
    
    # Application
    "src/api": "src/application/api",
    "src/core/orchestration": "src/application/orchestration",
    "src/orchestration": "src/application/orchestration",
    "src/pipeline": "src/application/automation",
    
    # Shared
    "src/utils": "src/shared/utils",
    "src/core/schemas": "src/shared/schemas",
}

# Individual file moves
SINGLE_FILE_MOVES = {
    "src/main_api.py": "src/application/api/main_api.py",
    "src/scrape_state_manager.py": "src/infrastructure/database/scrape_state_manager.py",
}

# Import path mappings
IMPORT_MAPPINGS = {
    # Collection
    "src.core.collection": "src.domain.collection",
    "src.core.extraction": "src.domain.collection.extractors",
    "src.services.collection": "src.domain.collection.services",
    "src.services.unified_collection_service": "src.domain.collection.services.unified_collection_service",
    "src.services.telegram_collection_commands": "src.domain.collection.services.telegram_collection_commands",
    
    # Analysis
    "src.core.analysis": "src.domain.analysis.analyzers",
    "src.services.analysis": "src.domain.analysis.services",
    "src.services.analysis_runner": "src.domain.analysis.services.analysis_runner",
    "src.services.post_analyzer": "src.domain.analysis.services.post_analyzer",
    
    # Publishing
    "src.publishing": "src.domain.publishing",
    
    # Intelligence
    "src.agents": "src.domain.intelligence.agents",
    "src.research": "src.domain.intelligence.research",
    "src.intelligence": "src.domain.intelligence",
    
    # Infrastructure
    "src.database": "src.infrastructure.database",
    "src.messaging": "src.infrastructure.messaging",
    "src.monitoring": "src.infrastructure.monitoring",
    "src.observability": "src.infrastructure.observability",
    "src.storage": "src.infrastructure.database.storage",
    
    # Application
    "src.api": "src.application.api",
    "src.core.orchestration": "src.application.orchestration",
    "src.orchestration": "src.application.orchestration",
    "src.pipeline": "src.application.automation",
    
    # Shared
    "src.utils": "src.shared.utils",
    "src.core.schemas": "src.shared.schemas",
    
    # Special cases
    "src.main_api": "src.application.api.main_api",
    "src.scrape_state_manager": "src.infrastructure.database.scrape_state_manager",
}


def move_directory(src: Path, dst: Path):
    """Move a directory to a new location"""
    if not src.exists():
        print(f"⚠️  Source doesn't exist: {src}")
        return False
    
    if dst.exists():
        print(f"⚠️  Destination already exists: {dst}")
        return False
    
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        print(f"✅ Moved: {src} → {dst}")
        return True
    except Exception as e:
        print(f"❌ Error moving {src}: {e}")
        return False


def move_file(src: Path, dst: Path):
    """Move a file to a new location"""
    if not src.exists():
        print(f"⚠️  Source doesn't exist: {src}")
        return False
    
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        print(f"✅ Moved: {src} → {dst}")
        return True
    except Exception as e:
        print(f"❌ Error moving {src}: {e}")
        return False


def update_imports_in_file(file_path: Path, mappings: Dict[str, str]) -> bool:
    """Update import statements in a file"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        original_content = content
        
        # Update import statements
        for old_import, new_import in mappings.items():
            # Pattern for "from old_import import ..."
            pattern1 = re.compile(rf'from\s+{re.escape(old_import)}\s+import')
            content = pattern1.sub(f'from {new_import} import', content)
            
            # Pattern for "import old_import"
            pattern2 = re.compile(rf'import\s+{re.escape(old_import)}\b')
            content = pattern2.sub(f'import {new_import}', content)
        
        if content != original_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True
        return False
    except Exception as e:
        print(f"❌ Error updating imports in {file_path}: {e}")
        return False


def update_all_imports(root_dir: Path, mappings: Dict[str, str]):
    """Update imports in all Python files"""
    updated_count = 0
    for py_file in root_dir.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue
        
        if update_imports_in_file(py_file, mappings):
            updated_count += 1
    
    print(f"✅ Updated imports in {updated_count} files")


def create_init_files(dirs: List[Path]):
    """Create __init__.py files in directories"""
    for dir_path in dirs:
        init_file = dir_path / "__init__.py"
        if not init_file.exists():
            init_file.touch()
            print(f"✅ Created: {init_file}")


def main():
    """Main restructuring function"""
    root = Path(__file__).parent.parent
    src_dir = root / "src"
    
    print("🚀 Starting codebase restructuring...\n")
    
    # Step 1: Move directories
    print("📦 Moving directories...")
    for old_path, new_path in FILE_MOVES.items():
        old = src_dir.parent / old_path
        new = src_dir.parent / new_path
        if old.exists() and old.is_dir():
            move_directory(old, new)
    
    # Step 2: Move individual files
    print("\n📄 Moving individual files...")
    for old_path, new_path in SINGLE_FILE_MOVES.items():
        old = src_dir.parent / old_path
        new = src_dir.parent / new_path
        if old.exists() and old.is_file():
            move_file(old, new)
    
    # Step 3: Update imports
    print("\n🔄 Updating imports...")
    update_all_imports(src_dir.parent, IMPORT_MAPPINGS)
    
    # Step 4: Create __init__.py files
    print("\n📝 Creating __init__.py files...")
    init_dirs = [
        src_dir.parent / "src/domain",
        src_dir.parent / "src/domain/collection",
        src_dir.parent / "src/domain/collection/services",
        src_dir.parent / "src/domain/collection/extractors",
        src_dir.parent / "src/domain/analysis",
        src_dir.parent / "src/domain/analysis/services",
        src_dir.parent / "src/domain/analysis/analyzers",
        src_dir.parent / "src/domain/publishing",
        src_dir.parent / "src/domain/intelligence",
        src_dir.parent / "src/domain/intelligence/agents",
        src_dir.parent / "src/domain/intelligence/research",
        src_dir.parent / "src/infrastructure",
        src_dir.parent / "src/infrastructure/database",
        src_dir.parent / "src/infrastructure/messaging",
        src_dir.parent / "src/infrastructure/monitoring",
        src_dir.parent / "src/infrastructure/observability",
        src_dir.parent / "src/application",
        src_dir.parent / "src/application/api",
        src_dir.parent / "src/application/orchestration",
        src_dir.parent / "src/application/automation",
        src_dir.parent / "src/shared",
        src_dir.parent / "src/shared/utils",
        src_dir.parent / "src/shared/config",
        src_dir.parent / "src/shared/exceptions",
        src_dir.parent / "src/shared/schemas",
    ]
    create_init_files(init_dirs)
    
    print("\n✅ Restructuring complete!")


if __name__ == "__main__":
    main()

