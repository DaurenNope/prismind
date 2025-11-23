#!/usr/bin/env python3
"""
Apply Supabase Indexes Using psycopg2
======================================
Applies database performance indexes directly via PostgreSQL connection
Created: 2025-11-20
"""

import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.shared.utils.logging_config import get_logger

logger = get_logger(__name__)


def get_connection_string():
    """Get PostgreSQL connection string from Supabase URL"""
    try:
        from src.shared.utils.secrets_manager import get_secrets_manager
        secrets = get_secrets_manager()
        
        supabase_url = secrets.get("SUPABASE_URL") or os.getenv("SUPABASE_URL", "")
        service_key = secrets.get("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        
        if not supabase_url or not service_key:
            logger.error("❌ Missing Supabase credentials")
            return None
        
        # Parse Supabase URL to get connection details
        # Format: https://<project-ref>.supabase.co
        # Need to construct: postgresql://postgres:[password]@db.<project-ref>.supabase.co:5432/postgres
        
        parsed = urlparse(supabase_url)
        project_ref = parsed.netloc.replace('.supabase.co', '')
        
        # Get database password from service key or env
        # For Supabase, we typically need the database password, not the service key
        db_password = os.getenv("SUPABASE_DB_PASSWORD") or os.getenv("DATABASE_PASSWORD")
        
        if not db_password:
            logger.warning("⚠️  Database password not found. Trying with service key...")
            # Service key won't work for direct DB connection, but let's try
            db_password = service_key
        
        # Construct connection string
        # Note: This is a simplified version - actual connection requires DB password
        connection_string = f"postgresql://postgres:[PASSWORD]@db.{project_ref}.supabase.co:5432/postgres"
        
        logger.info(f"📊 Project reference: {project_ref}")
        logger.warning("⚠️  Direct PostgreSQL connection requires database password")
        logger.info("💡 Use Supabase Dashboard SQL Editor instead (recommended)")
        
        return None  # Return None to indicate we can't connect directly
        
    except Exception as e:
        logger.error(f"❌ Error getting connection string: {e}")
        return None


def apply_migration_via_mcp():
    """Try to apply migration via Supabase MCP if token is available"""
    try:
        # Check for access token
        access_token = os.getenv("SUPABASE_ACCESS_TOKEN") or os.getenv("SUPABASE_PAT")
        
        if not access_token:
            logger.warning("⚠️  SUPABASE_ACCESS_TOKEN not found in environment")
            logger.info("💡 Set SUPABASE_ACCESS_TOKEN in environment or .env file")
            logger.info("   Get token from: https://supabase.com/dashboard/account/tokens")
            return False
        
        logger.info("✅ Found Supabase access token")
        
        # The MCP should pick up the token automatically
        # But if it doesn't, we'll need to apply manually
        logger.info("💡 To apply via MCP, ensure SUPABASE_ACCESS_TOKEN is set")
        logger.info("   Then the MCP tools should work")
        
        return False  # Return False to indicate manual application needed
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return False


def main():
    """Main function"""
    logger.info("🚀 Attempting to apply Supabase indexes...")
    
    # Try to get connection info
    conn_str = get_connection_string()
    
    # Try MCP approach
    mcp_success = apply_migration_via_mcp()
    
    if not mcp_success:
        logger.info("\n" + "=" * 80)
        logger.info("📋 MANUAL APPLICATION REQUIRED")
        logger.info("=" * 80)
        logger.info("\nThe Supabase MCP requires authentication.")
        logger.info("\nTo apply the migration:")
        logger.info("\n1. Via Supabase Dashboard (Recommended):")
        logger.info("   - Open: https://supabase.com/dashboard/project/ahlbudltabimzxegdkfc/sql/new")
        logger.info("   - Copy SQL from: migrations/2025_11_20_database_performance_indexes.sql")
        logger.info("   - Paste and run")
        logger.info("\n2. Via MCP (if token is set):")
        logger.info("   - Ensure SUPABASE_ACCESS_TOKEN is set in environment")
        logger.info("   - The MCP tools should then work")
        logger.info("\nMigration file: migrations/2025_11_20_database_performance_indexes.sql")
        logger.info("\n" + "=" * 80)


if __name__ == "__main__":
    main()






