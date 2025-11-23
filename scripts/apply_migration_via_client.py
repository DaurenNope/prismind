#!/usr/bin/env python3
"""
Apply action_items migration via Supabase Python client

Uses the Supabase client from the codebase to apply the migration.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.infrastructure.database.manager import SupabaseManager
from src.shared.utils.logging_config import get_logger

logger = get_logger(__name__)


def apply_migration():
    """Apply action_items migration using Supabase client"""
    
    logger.info("=" * 70)
    logger.info("🔧 APPLYING ACTION_ITEMS MIGRATION VIA SUPABASE CLIENT")
    logger.info("=" * 70)
    
    # Read migration SQL
    migration_file = project_root / "migrations" / "2025_11_22_add_action_items_column.sql"
    
    if not migration_file.exists():
        logger.error(f"❌ Migration file not found: {migration_file}")
        return False
    
    with open(migration_file, "r") as f:
        migration_sql = f.read()
    
    # Extract just the DDL statements (remove comments and verification queries)
    lines = migration_sql.split('\n')
    sql_lines = []
    in_sql = False
    
    for line in lines:
        stripped = line.strip()
        # Skip comment lines and empty lines before SQL
        if stripped.startswith('--') or stripped.startswith('/*') or stripped.startswith('*/'):
            continue
        if not stripped:
            continue
        # Start collecting SQL
        if 'ALTER TABLE' in stripped.upper() or stripped.upper().startswith('DO'):
            in_sql = True
        if in_sql:
            sql_lines.append(line)
        # Stop at verification queries
        if in_sql and stripped.upper().startswith('SELECT') and 'VERIFICATION' in migration_sql[:migration_sql.find(stripped)].upper():
            break
    
    migration_sql_clean = '\n'.join(sql_lines).strip()
    
    logger.info(f"📄 Read migration file: {migration_file.name}")
    logger.info(f"📝 Migration SQL prepared ({len(migration_sql_clean)} chars)")
    
    try:
        # Get Supabase manager
        manager = SupabaseManager()
        client = manager.client
        
        logger.info("✅ Connected to Supabase")
        logger.info(f"   URL: {manager.supabase_url}")
        
        # Try to execute via RPC if available
        logger.info("🔄 Attempting to apply migration...")
        
        try:
            # Supabase Python client doesn't have direct SQL execution
            # We need to use the REST API directly or check for exec_sql RPC
            import requests
            import os
            
            url = manager.supabase_url
            key = manager.supabase_key
            
            # Try using the REST API to execute SQL
            # Supabase has a SQL endpoint: /rest/v1/rpc/exec_sql (if enabled)
            # Or we can use the project API: /rest/v1/rpc/exec_sql
            
            # Alternative: Use PostgREST directly if we have the service role key
            headers = {
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json"
            }
            
            # Try calling exec_sql RPC function (if it exists)
            rpc_url = f"{url}/rest/v1/rpc/exec_sql"
            payload = {"sql": migration_sql_clean}
            
            logger.info("📤 Sending migration SQL via REST API...")
            response = requests.post(rpc_url, json=payload, headers=headers, timeout=30)
            
            if response.status_code == 200 or response.status_code == 201:
                logger.info("✅ Migration applied successfully!")
                logger.info(f"   Response: {response.text[:200]}")
                return True
            elif response.status_code == 404:
                logger.warning("⚠️  exec_sql RPC function not found")
                logger.info("   Trying alternative method...")
                # Fall through to manual instructions
            else:
                logger.warning(f"⚠️  API returned status {response.status_code}: {response.text[:200]}")
                logger.info("   Falling back to manual instructions...")
                
        except ImportError:
            logger.warning("⚠️  requests library not available")
        except Exception as e:
            logger.warning(f"⚠️  REST API call failed: {e}")
            logger.info("   Falling back to manual instructions...")
        
        # If REST API doesn't work, provide manual instructions
        logger.info("")
        logger.info("=" * 70)
        logger.info("⚠️  AUTOMATIC MIGRATION NOT AVAILABLE")
        logger.info("=" * 70)
        logger.info("")
        logger.info("The Supabase Python client doesn't support direct SQL execution.")
        logger.info("Please apply the migration manually:")
        logger.info("")
        logger.info("1. Open Supabase Dashboard:")
        logger.info(f"   {url.replace('/rest/v1', '')}/sql/new")
        logger.info("")
        logger.info("2. Copy and paste this SQL:")
        logger.info("")
        logger.info("-" * 70)
        print(migration_sql_clean)
        logger.info("-" * 70)
        logger.info("")
        logger.info("3. Run the query")
        logger.info("")
        
        return False
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}", exc_info=True)
        logger.error("")
        logger.error("Please apply the migration manually via Supabase dashboard")
        return False


if __name__ == "__main__":
    success = apply_migration()
    sys.exit(0 if success else 1)





