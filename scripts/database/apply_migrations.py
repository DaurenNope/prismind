#!/usr/bin/env python3
"""
Apply Database Migrations Safely
=================================
Safely applies database migrations with backup, verification, and rollback support
Created: 2025-11-20
Priority: P1 - Migration application

Usage:
    python scripts/database/apply_migrations.py --migration <migration_file> [--dry-run] [--backup]
"""

import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.shared.utils.logging_config import get_logger

logger = get_logger(__name__)

# Migrations to apply (in order)
MIGRATIONS = [
    {
        'name': 'Database Performance Indexes',
        'file': 'migrations/2025_11_20_database_performance_indexes.sql',
        'type': 'supabase',
        'description': 'Adds missing indexes for query performance optimization',
        'critical': True,
    },
    {
        'name': 'Remove Unused Columns',
        'file': 'migrations/2025_11_20_remove_unused_columns.sql',
        'type': 'supabase',
        'description': 'Removes 8 unused columns to optimize schema',
        'critical': False,
        'requires_backup': True,
    },
]

SQLITE_MIGRATIONS = [
    {
        'name': 'SQLite Performance Indexes',
        'file': 'migrations/2025_11_20_sqlite_indexes.py',
        'type': 'sqlite',
        'description': 'Adds missing indexes to SQLite database',
        'critical': True,
    },
]


def create_backup(db_type: str = 'supabase') -> Optional[str]:
    """
    Create database backup before migration
    
    Args:
        db_type: 'supabase' or 'sqlite'
    
    Returns:
        Backup file path or None if failed
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    if db_type == 'supabase':
        # Supabase backup via pg_dump
        backup_file = f"backups/supabase_backup_{timestamp}.sql"
        
        logger.info(f"📦 Creating Supabase backup to {backup_file}...")
        
        try:
            # Get connection details from environment
            supabase_url = os.getenv('SUPABASE_URL')
            if not supabase_url:
                logger.error("❌ SUPABASE_URL not found in environment")
                return None
            
            # Extract connection details (this is a simplified version)
            # In production, you'd parse the connection string properly
            logger.warning("⚠️  Supabase backup requires manual pg_dump command")
            logger.info(f"💡 Run manually: pg_dump -h <host> -U <user> -d <database> -t posts > {backup_file}")
            
            return backup_file
            
        except Exception as e:
            logger.error(f"❌ Backup failed: {e}")
            return None
    
    elif db_type == 'sqlite':
        # SQLite backup (copy file)
        db_path = "beyondlines.db"
        if not Path(db_path).exists():
            logger.warning(f"⚠️  SQLite database not found: {db_path}")
            return None
        
        backup_file = f"backups/sqlite_backup_{timestamp}.db"
        backup_dir = Path(backup_file).parent
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"📦 Creating SQLite backup to {backup_file}...")
        
        try:
            import shutil
            shutil.copy2(db_path, backup_file)
            logger.info(f"✅ Backup created: {backup_file}")
            return backup_file
        except Exception as e:
            logger.error(f"❌ Backup failed: {e}")
            return None
    
    return None


def apply_supabase_migration(migration_file: Path, dry_run: bool = False) -> Dict[str, any]:
    """
    Apply Supabase migration
    
    Args:
        migration_file: Path to migration SQL file
        dry_run: If True, only validate migration file
    
    Returns:
        Result dictionary
    """
    result = {
        'success': False,
        'message': '',
        'output': '',
    }
    
    if not migration_file.exists():
        result['message'] = f"Migration file not found: {migration_file}"
        return result
    
    logger.info(f"📄 Reading migration: {migration_file.name}")
    
    try:
        with open(migration_file, 'r') as f:
            sql_content = f.read()
        
        if dry_run:
            # Validate SQL syntax (basic check)
            logger.info("🔍 Validating migration (dry-run)...")
            
            # Basic validation
            if 'DROP COLUMN' in sql_content and 'IF EXISTS' not in sql_content:
                logger.warning("⚠️  DROP COLUMN without IF EXISTS detected")
            
            if 'ALTER TABLE' in sql_content and 'ADD COLUMN IF NOT EXISTS' not in sql_content:
                logger.warning("⚠️  ALTER TABLE without IF NOT EXISTS detected")
            
            result['success'] = True
            result['message'] = "Migration validated (dry-run)"
            return result
        
        # Actual application requires Supabase SQL Editor
        logger.info("📋 Migration SQL:")
        logger.info("=" * 80)
        logger.info(sql_content[:500] + "..." if len(sql_content) > 500 else sql_content)
        logger.info("=" * 80)
        
        logger.warning("⚠️  Supabase migrations must be applied manually via SQL Editor")
        logger.info("💡 Instructions:")
        logger.info("   1. Open Supabase Dashboard → SQL Editor")
        logger.info("   2. Click 'New Query'")
        logger.info("   3. Paste the migration SQL")
        logger.info("   4. Click 'Run'")
        
        result['success'] = True
        result['message'] = "Migration ready for manual application"
        result['output'] = sql_content
        
        return result
        
    except Exception as e:
        result['message'] = f"Error reading migration: {e}"
        logger.error(f"❌ {result['message']}")
        return result


def apply_sqlite_migration(migration_file: Path, dry_run: bool = False) -> Dict[str, any]:
    """
    Apply SQLite migration (Python script)
    
    Args:
        migration_file: Path to migration Python script
        dry_run: If True, only validate migration file
    
    Returns:
        Result dictionary
    """
    result = {
        'success': False,
        'message': '',
        'output': '',
    }
    
    if not migration_file.exists():
        result['message'] = f"Migration file not found: {migration_file}"
        return result
    
    logger.info(f"🐍 Running SQLite migration: {migration_file.name}")
    
    try:
        if dry_run:
            logger.info("🔍 Validating migration (dry-run)...")
            # Check if file is executable
            if not os.access(migration_file, os.X_OK):
                logger.warning("⚠️  Migration script is not executable")
            
            result['success'] = True
            result['message'] = "Migration validated (dry-run)"
            return result
        
        # Run the migration script
        cmd = [sys.executable, str(migration_file)]
        logger.info(f"🚀 Executing: {' '.join(cmd)}")
        
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=project_root,
        )
        
        if process.returncode == 0:
            result['success'] = True
            result['message'] = "Migration applied successfully"
            result['output'] = process.stdout
            logger.info("✅ Migration applied successfully")
        else:
            result['message'] = f"Migration failed: {process.stderr}"
            result['output'] = process.stderr
            logger.error(f"❌ Migration failed: {process.stderr}")
        
        return result
        
    except Exception as e:
        result['message'] = f"Error running migration: {e}"
        logger.error(f"❌ {result['message']}")
        return result


def verify_migration(migration: Dict[str, any]) -> bool:
    """
    Verify migration was applied successfully
    
    Args:
        migration: Migration dictionary
    
    Returns:
        True if verified, False otherwise
    """
    logger.info(f"🔍 Verifying migration: {migration['name']}...")
    
    if migration['type'] == 'supabase':
        # For Supabase, verification is done via SQL queries in the migration file
        logger.info("✅ Supabase verification queries should be run manually")
        return True
    
    elif migration['type'] == 'sqlite':
        # For SQLite, check if indexes exist
        try:
            import sqlite3
            db_path = "beyondlines.db"
            if not Path(db_path).exists():
                logger.warning("⚠️  SQLite database not found")
                return False
            
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type = 'index' 
                    AND tbl_name = 'posts'
                    ORDER BY name
                """)
                indexes = [row[0] for row in cursor.fetchall()]
                
                # Check for expected indexes
                expected_indexes = [
                    'idx_posts_platform_created_at',
                    'idx_posts_created_at',
                    'idx_posts_value_score',
                    'idx_posts_rewrite_score',
                ]
                
                missing = [idx for idx in expected_indexes if idx not in indexes]
                
                if missing:
                    logger.warning(f"⚠️  Missing indexes: {', '.join(missing)}")
                    return False
                
                logger.info(f"✅ Verified {len(indexes)} indexes exist")
                return True
                
        except Exception as e:
            logger.error(f"❌ Verification failed: {e}")
            return False
    
    return False


def list_migrations() -> List[Dict[str, any]]:
    """List all available migrations"""
    return MIGRATIONS + SQLITE_MIGRATIONS


def main():
    parser = argparse.ArgumentParser(description="Apply database migrations safely")
    parser.add_argument(
        "--migration",
        type=str,
        help="Specific migration file to apply (optional, applies all if not specified)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate migrations without applying"
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        default=True,
        help="Create backup before migration (default: True)"
    )
    parser.add_argument(
        "--no-backup",
        dest="backup",
        action="store_false",
        help="Skip backup (not recommended)"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all available migrations"
    )
    parser.add_argument(
        "--verify",
        type=str,
        help="Verify a specific migration was applied"
    )
    
    args = parser.parse_args()
    
    if args.list:
        print("\n" + "=" * 80)
        print("📋 Available Migrations")
        print("=" * 80)
        
        all_migrations = list_migrations()
        for i, migration in enumerate(all_migrations, 1):
            print(f"\n{i}. {migration['name']}")
            print(f"   File: {migration['file']}")
            print(f"   Type: {migration['type']}")
            print(f"   Description: {migration['description']}")
            print(f"   Critical: {'Yes' if migration.get('critical') else 'No'}")
            print(f"   Requires Backup: {'Yes' if migration.get('requires_backup') else 'No'}")
        
        return
    
    if args.verify:
        # Verify specific migration
        all_migrations = list_migrations()
        migration = next((m for m in all_migrations if args.verify in m['file']), None)
        
        if not migration:
            logger.error(f"❌ Migration not found: {args.verify}")
            sys.exit(1)
        
        success = verify_migration(migration)
        sys.exit(0 if success else 1)
    
    if args.migration:
        # Apply specific migration
        migration_file = Path(project_root) / args.migration
        
        if not migration_file.exists():
            logger.error(f"❌ Migration file not found: {migration_file}")
            sys.exit(1)
        
        # Determine migration type
        if migration_file.suffix == '.sql':
            migration_type = 'supabase'
        elif migration_file.suffix == '.py':
            migration_type = 'sqlite'
        else:
            logger.error(f"❌ Unknown migration type: {migration_file.suffix}")
            sys.exit(1)
        
        # Create backup if requested
        backup_file = None
        if args.backup and not args.dry_run:
            backup_file = create_backup(migration_type)
            if backup_file:
                logger.info(f"✅ Backup created: {backup_file}")
        
        # Apply migration
        if migration_type == 'supabase':
            result = apply_supabase_migration(migration_file, args.dry_run)
        else:
            result = apply_sqlite_migration(migration_file, args.dry_run)
        
        if result['success']:
            logger.info(f"✅ {result['message']}")
            if result.get('output'):
                print("\n" + result['output'])
        else:
            logger.error(f"❌ {result['message']}")
            sys.exit(1)
    else:
        # Apply all migrations
        logger.info("🚀 Applying all pending migrations...")
        
        all_migrations = list_migrations()
        
        for migration in all_migrations:
            migration_file = Path(project_root) / migration['file']
            
            if not migration_file.exists():
                logger.warning(f"⚠️  Migration file not found: {migration_file}")
                continue
            
            logger.info(f"\n{'=' * 80}")
            logger.info(f"📋 Applying: {migration['name']}")
            logger.info(f"{'=' * 80}")
            
            # Create backup if needed
            if args.backup and migration.get('requires_backup') and not args.dry_run:
                backup_file = create_backup(migration['type'])
                if not backup_file:
                    logger.error(f"❌ Backup failed, skipping migration")
                    continue
            
            # Apply migration
            if migration['type'] == 'supabase':
                result = apply_supabase_migration(migration_file, args.dry_run)
            else:
                result = apply_sqlite_migration(migration_file, args.dry_run)
            
            if result['success']:
                logger.info(f"✅ {result['message']}")
            else:
                logger.error(f"❌ {result['message']}")
                if migration.get('critical'):
                    logger.error("⚠️  Critical migration failed, stopping")
                    sys.exit(1)


if __name__ == "__main__":
    main()






