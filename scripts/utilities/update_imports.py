#!/usr/bin/env python3
"""
Update all import statements to reflect new structure
"""

import re
from pathlib import Path
from typing import Dict, List, Tuple

# Import path mappings (old -> new)
IMPORT_MAPPINGS = [
    # Collection domain
    (r'from src\.core\.collection', 'from src.domain.collection'),
    (r'from src\.services\.collection', 'from src.domain.collection.services'),
    (r'import src\.core\.collection', 'import src.domain.collection'),
    (r'import src\.services\.collection', 'import src.domain.collection.services'),
    
    # Collection extractors
    (r'from src\.core\.extraction', 'from src.domain.collection.extractors'),
    (r'import src\.core\.extraction', 'import src.domain.collection.extractors'),
    
    # Collection services
    (r'from src\.services\.unified_collection_service', 'from src.domain.collection.services.unified_collection_service'),
    (r'from src\.services\.telegram_collection_commands', 'from src.domain.collection.services.telegram_collection_commands'),
    (r'import src\.services\.unified_collection_service', 'import src.domain.collection.services.unified_collection_service'),
    (r'import src\.services\.telegram_collection_commands', 'import src.domain.collection.services.telegram_collection_commands'),
    
    # Analysis domain
    (r'from src\.core\.analysis', 'from src.domain.analysis.analyzers'),
    (r'from src\.services\.analysis', 'from src.domain.analysis.services'),
    (r'import src\.core\.analysis', 'import src.domain.analysis.analyzers'),
    (r'import src\.services\.analysis', 'import src.domain.analysis.services'),
    
    # Analysis services
    (r'from src\.services\.analysis_runner', 'from src.domain.analysis.services.analysis_runner'),
    (r'from src\.services\.post_analyzer', 'from src.domain.analysis.services.post_analyzer'),
    (r'from src\.services\.analysis_lock', 'from src.domain.analysis.services.analysis_lock'),
    (r'import src\.services\.analysis_runner', 'import src.domain.analysis.services.analysis_runner'),
    (r'import src\.services\.post_analyzer', 'import src.domain.analysis.services.post_analyzer'),
    (r'import src\.services\.analysis_lock', 'import src.domain.analysis.services.analysis_lock'),
    
    # Publishing domain
    (r'from src\.publishing', 'from src.domain.publishing'),
    (r'import src\.publishing', 'import src.domain.publishing'),
    
    # Intelligence domain
    (r'from src\.agents', 'from src.domain.intelligence.agents'),
    (r'from src\.research', 'from src.domain.intelligence.research'),
    (r'from src\.intelligence', 'from src.domain.intelligence'),
    (r'import src\.agents', 'import src.domain.intelligence.agents'),
    (r'import src\.research', 'import src.domain.intelligence.research'),
    (r'import src\.intelligence', 'import src.domain.intelligence'),
    
    # Infrastructure
    (r'from src\.database', 'from src.infrastructure.database'),
    (r'from src\.messaging', 'from src.infrastructure.messaging'),
    (r'from src\.monitoring', 'from src.infrastructure.monitoring'),
    (r'from src\.observability', 'from src.infrastructure.observability'),
    (r'from src\.storage', 'from src.infrastructure.database.storage'),
    (r'import src\.database', 'import src.infrastructure.database'),
    (r'import src\.messaging', 'import src.infrastructure.messaging'),
    (r'import src\.monitoring', 'import src.infrastructure.monitoring'),
    (r'import src\.observability', 'import src.infrastructure.observability'),
    (r'import src\.storage', 'import src.infrastructure.database.storage'),
    
    # Application
    (r'from src\.api', 'from src.application.api'),
    (r'from src\.core\.orchestration', 'from src.application.orchestration'),
    (r'from src\.orchestration', 'from src.application.orchestration'),
    (r'from src\.pipeline', 'from src.application.automation'),
    (r'import src\.api', 'import src.application.api'),
    (r'import src\.core\.orchestration', 'import src.application.orchestration'),
    (r'import src\.orchestration', 'import src.application.orchestration'),
    (r'import src\.pipeline', 'import src.application.automation'),
    
    # Shared
    (r'from src\.utils', 'from src.shared.utils'),
    (r'from src\.core\.schemas', 'from src.shared.schemas'),
    (r'import src\.utils', 'import src.shared.utils'),
    (r'import src\.core\.schemas', 'import src.shared.schemas'),
    
    # Special files
    (r'from src\.main_api', 'from src.application.api.main_api'),
    (r'from src\.scrape_state_manager', 'from src.infrastructure.database.scrape_state_manager'),
    (r'import src\.main_api', 'import src.application.api.main_api'),
    (r'import src\.scrape_state_manager', 'import src.infrastructure.database.scrape_state_manager'),
]


def update_file_imports(file_path: Path) -> bool:
    """Update imports in a single file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Apply all mappings
        for pattern, replacement in IMPORT_MAPPINGS:
            content = re.sub(pattern, replacement, content)
        
        # Only write if changed
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False


def update_all_imports(root_dir: Path):
    """Update imports in all Python files"""
    updated_files = []
    skipped_files = []
    
    for py_file in root_dir.rglob("*.py"):
        # Skip cache and new domain structure
        if "__pycache__" in str(py_file):
            continue
        if "src/domain" in str(py_file) or "src/infrastructure" in str(py_file) or "src/application" in str(py_file) or "src/shared" in str(py_file):
            # Skip files already in new structure
            continue
        
        if update_file_imports(py_file):
            updated_files.append(py_file)
        else:
            skipped_files.append(py_file)
    
    print(f"✅ Updated {len(updated_files)} files")
    print(f"⏭️  Skipped {len(skipped_files)} files (no changes needed)")
    
    return updated_files


def main():
    """Main function"""
    root = Path(__file__).parent.parent
    src_dir = root / "src"
    
    print("🔄 Updating imports across codebase...\n")
    
    updated = update_all_imports(src_dir)
    
    # Also update scripts
    scripts_dir = root / "scripts"
    if scripts_dir.exists():
        print("\n🔄 Updating imports in scripts...")
        update_all_imports(scripts_dir)
    
    # Also update tests
    tests_dir = root / "tests"
    if tests_dir.exists():
        print("\n🔄 Updating imports in tests...")
        update_all_imports(tests_dir)
    
    print("\n✅ Import update complete!")


if __name__ == "__main__":
    main()

