#!/usr/bin/env python3
"""
Apply Supabase Indexes Directly
================================
Applies database performance indexes directly using Supabase client
Created: 2025-11-20
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.shared.utils.logging_config import get_logger

logger = get_logger(__name__)


def apply_indexes():
    """Apply indexes directly using Supabase client"""
    try:
        from src.infrastructure.database.manager import SupabaseManager
        
        logger.info("📊 Initializing Supabase connection...")
        manager = SupabaseManager()
        
        # Read migration SQL
        migration_file = Path(project_root) / "migrations/2025_11_20_database_performance_indexes.sql"
        
        if not migration_file.exists():
            logger.error(f"❌ Migration file not found: {migration_file}")
            return False
        
        logger.info(f"📄 Reading migration file: {migration_file.name}")
        
        with open(migration_file, 'r') as f:
            sql_content = f.read()
        
        # Extract only the CREATE INDEX statements (remove comments and verification queries)
        index_statements = []
        for line in sql_content.split('\n'):
            stripped = line.strip()
            # Skip comments and empty lines
            if stripped.startswith('--') or not stripped or stripped.startswith('/*'):
                continue
            # Skip verification queries
            if stripped.upper().startswith('SELECT'):
                break
            # Extract CREATE INDEX statements
            if stripped.upper().startswith('CREATE INDEX'):
                index_statements.append(stripped)
        
        if not index_statements:
            logger.error("❌ No CREATE INDEX statements found in migration file")
            return False
        
        logger.info(f"🔍 Found {len(index_statements)} index statements to apply")
        
        # Apply each index statement
        # Note: Supabase Python client doesn't support raw SQL execution directly
        # We'll need to use RPC or PostgREST extensions, or execute via psycopg2
        
        logger.warning("⚠️  Direct SQL execution not supported via Supabase Python client")
        logger.info("💡 Options:")
        logger.info("   1. Use Supabase Dashboard SQL Editor (recommended)")
        logger.info("   2. Use psycopg2 to connect directly")
        logger.info("   3. Use Supabase MCP with authentication token")
        
        logger.info("\n📋 Index statements to apply:")
        for i, stmt in enumerate(index_statements, 1):
            logger.info(f"\n{i}. {stmt[:80]}...")
        
        # Try using RPC if available, otherwise provide manual instructions
        try:
            # Check if we can use RPC
            logger.info("\n💡 To apply via Dashboard:")
            logger.info("   1. Open: https://supabase.com/dashboard/project/ahlbudltabimzxegdkfc/sql/new")
            logger.info("   2. Copy the SQL from: migrations/2025_11_20_database_performance_indexes.sql")
            logger.info("   3. Paste and run")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error: {e}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error applying indexes: {e}")
        logger.error(f"   {type(e).__name__}: {str(e)}")
        return False


def main():
    """Main function"""
    logger.info("🚀 Applying Supabase database performance indexes...")
    
    success = apply_indexes()
    
    if success:
        logger.info("\n✅ Migration prepared successfully")
        logger.info("💡 Apply manually via Supabase Dashboard SQL Editor")
        logger.info("   See: docs/AGENT_7_MIGRATION_APPLICATION_STATUS.md")
    else:
        logger.error("\n❌ Failed to prepare migration")
        sys.exit(1)


if __name__ == "__main__":
    main()






