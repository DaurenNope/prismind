#!/usr/bin/env python3
"""
Apply action_items migration to Supabase

This script applies the migration to add the action_items column to the posts table.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from src.infrastructure.database.manager import SupabaseManager
from src.shared.utils.logging_config import get_logger

logger = get_logger(__name__)


def apply_migration():
    """Apply action_items migration to Supabase"""
    
    logger.info("=" * 70)
    logger.info("🔧 APPLYING ACTION_ITEMS MIGRATION")
    logger.info("=" * 70)
    
    # Read migration SQL
    migration_file = project_root / "migrations" / "2025_11_22_add_action_items_column.sql"
    
    if not migration_file.exists():
        logger.error(f"❌ Migration file not found: {migration_file}")
        return False
    
    with open(migration_file, "r") as f:
        migration_sql = f.read()
    
    logger.info(f"📄 Read migration file: {migration_file.name}")
    
    try:
        # Get Supabase manager
        supabase_manager = SupabaseManager()
        client = supabase_manager.client
        
        logger.info("✅ Connected to Supabase")
        
        # Apply migration
        logger.info("🔄 Applying migration...")
        
        # Execute migration SQL
        # Note: Supabase Python client doesn't have a direct SQL execution method
        # We need to use raw SQL via the REST API or use execute_sql if available
        try:
            # Try using RPC if available, or direct SQL execution
            response = client.rpc("exec_sql", {"sql": migration_sql}).execute()
            logger.info("✅ Migration applied successfully via RPC")
        except Exception as rpc_error:
            # Fallback: Try direct execution if client supports it
            logger.warning(f"RPC method failed: {rpc_error}")
            logger.info("⚠️  Manual migration required:")
            logger.info("")
            logger.info("Please run the following SQL in Supabase SQL Editor:")
            logger.info("=" * 70)
            logger.info(migration_sql)
            logger.info("=" * 70)
            logger.info("")
            logger.info("Migration file location:")
            logger.info(f"  {migration_file}")
            return False
        
        # Verify migration
        logger.info("🔍 Verifying migration...")
        verify_sql = """
        SELECT 
            column_name, 
            data_type,
            udt_name
        FROM information_schema.columns 
        WHERE table_name = 'posts' 
          AND table_schema = 'public'
          AND column_name = 'action_items';
        """
        
        try:
            verify_response = client.rpc("exec_sql", {"sql": verify_sql}).execute()
            logger.info("✅ Verification query executed")
            logger.info(f"Results: {verify_response.data}")
        except Exception as verify_error:
            logger.warning(f"Could not verify migration: {verify_error}")
            logger.info("⚠️  Please verify manually in Supabase dashboard")
        
        logger.info("")
        logger.info("=" * 70)
        logger.info("✅ MIGRATION COMPLETE")
        logger.info("=" * 70)
        logger.info("")
        logger.info("Next steps:")
        logger.info("  1. Verify column exists: Check Supabase dashboard")
        logger.info("  2. Re-analyze posts: python scripts/validation/re_analyze_posts.py --limit 10")
        logger.info("  3. Run validation: python scripts/validation/system_validation.py")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        logger.error("")
        logger.error("Manual migration required:")
        logger.error(f"  File: {migration_file}")
        logger.error("")
        logger.error("Please run the SQL in Supabase SQL Editor:")
        logger.error("  https://supabase.com/dashboard/project/YOUR_PROJECT_ID/sql/new")
        return False


if __name__ == "__main__":
    success = apply_migration()
    sys.exit(0 if success else 1)






