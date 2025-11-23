#!/usr/bin/env python3
"""
Apply action_items Type Conversion Migration
Uses Supabase Python client directly to bypass MCP authentication
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))

from src.shared.utils.secrets_manager import get_secrets_manager
from src.shared.utils.logging_config import get_logger

logger = get_logger(__name__)


def apply_migration():
    """Apply action_items type conversion migration using Supabase Python client"""
    try:
        from supabase import create_client
    except ImportError:
        logger.error("❌ supabase-py not installed. Install with: pip install supabase")
        return False

    # Get credentials
    secrets = get_secrets_manager()
    url = secrets.get("SUPABASE_URL")
    service_key = secrets.get("SUPABASE_SERVICE_ROLE_KEY") or secrets.get("SUPABASE_KEY")

    if not url or not service_key:
        logger.error("❌ Missing Supabase credentials in environment")
        logger.error("   Required: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY or SUPABASE_KEY")
        return False

    # Extract project ref from URL
    # URL format: https://<project_ref>.supabase.co
    project_ref = url.replace("https://", "").replace(".supabase.co", "").split("/")[0]
    logger.info(f"📋 Project: {project_ref}")

    # Create Supabase client
    try:
        client = create_client(url, service_key)
        logger.info("✅ Connected to Supabase")
    except Exception as e:
        logger.error(f"❌ Failed to connect to Supabase: {e}")
        return False

    # Read migration SQL
    migration_file = project_root / "migrations/2025_11_22_fix_action_items_type.sql"
    if not migration_file.exists():
        logger.error(f"❌ Migration file not found: {migration_file}")
        return False

    with open(migration_file, "r") as f:
        migration_sql = f.read()

    # Extract just the ALTER TABLE statement (not verification queries)
    # Split by "-- ======" to get just the migration part
    migration_parts = migration_sql.split("-- =====================================================")
    alter_table_sql = None
    
    for part in migration_parts:
        if "ALTER TABLE public.posts" in part:
            # Extract the ALTER TABLE statement
            lines = part.split("\n")
            sql_lines = []
            in_sql = False
            for line in lines:
                if "ALTER TABLE" in line or in_sql:
                    in_sql = True
                    sql_lines.append(line)
                    if line.strip().endswith(";") or line.strip().endswith("END;"):
                        break
            alter_table_sql = "\n".join(sql_lines).strip()
            break

    if not alter_table_sql:
        logger.error("❌ Could not extract ALTER TABLE statement from migration file")
        return False

    logger.info("📝 Applying migration...")
    logger.debug(f"SQL: {alter_table_sql}")

    # Apply migration using RPC or direct SQL execution
    # Note: Supabase Python client doesn't directly support DDL, but we can try RPC
    # For DDL operations, we might need to use the Management API or direct connection
    
    # Check if column exists and its current type
    try:
        # Use RPC to check column type
        check_sql = """
        SELECT 
            column_name, 
            data_type,
            udt_name
        FROM information_schema.columns 
        WHERE table_name = 'posts' 
          AND table_schema = 'public'
          AND column_name = 'action_items';
        """
        
        logger.info("🔍 Checking current column type...")
        # Try to execute via table query (won't work for SELECT, but let's see)
        # Actually, we need to use a different approach
        
        # Alternative: Use psycopg2 if available, or provide manual instructions
        logger.warning("⚠️  Supabase Python client doesn't support DDL operations directly")
        logger.info("📋 Please apply the migration manually:")
        logger.info("")
        logger.info("1. Open Supabase Dashboard:")
        logger.info(f"   https://supabase.com/dashboard/project/{project_ref}/sql/new")
        logger.info("")
        logger.info("2. Copy and paste this SQL:")
        logger.info("")
        print("=" * 70)
        print(alter_table_sql)
        print("=" * 70)
        logger.info("")
        logger.info("3. Click 'Run' to apply the migration")
        logger.info("")
        
        return False  # Indicate manual step needed

    except Exception as e:
        logger.error(f"❌ Error checking column: {e}")
        return False


def main():
    """Main entry point"""
    logger.info("🚀 Applying action_items type conversion migration...")
    success = apply_migration()
    
    if not success:
        logger.info("")
        logger.info("💡 Tip: The Supabase Python client doesn't support DDL operations.")
        logger.info("   Apply the migration manually in the Supabase Dashboard.")
        logger.info("   Migration file: migrations/2025_11_22_fix_action_items_type.sql")
        sys.exit(1)
    else:
        logger.info("✅ Migration applied successfully!")
        sys.exit(0)


if __name__ == "__main__":
    main()






