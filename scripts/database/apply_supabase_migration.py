#!/usr/bin/env python3
"""
Apply Supabase Migration via MCP
=================================
Helper script to extract project ID and apply migration via Supabase MCP
Created: 2025-11-20
"""

import os
import re
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.shared.utils.logging_config import get_logger

logger = get_logger(__name__)


def get_project_id_from_url(url: str) -> str:
    """
    Extract project ID/reference from Supabase URL
    
    Supabase URLs are typically: https://<project-ref>.supabase.co
    """
    if not url:
        return ""
    
    # Extract project reference from URL
    match = re.search(r'https://([^.]+)\.supabase\.co', url)
    if match:
        return match.group(1)
    
    return ""


def main():
    """Extract project info for migration application"""
    try:
        from src.shared.utils.secrets_manager import get_secrets_manager
        secrets = get_secrets_manager()
        
        supabase_url = secrets.get("SUPABASE_URL") or os.getenv("SUPABASE_URL", "")
        
        if not supabase_url:
            logger.error("❌ SUPABASE_URL not found")
            logger.info("💡 Set SUPABASE_URL in .env file or environment")
            sys.exit(1)
        
        project_ref = get_project_id_from_url(supabase_url)
        
        if not project_ref:
            logger.error("❌ Could not extract project reference from URL")
            logger.info(f"   URL: {supabase_url}")
            sys.exit(1)
        
        logger.info(f"✅ Found Supabase project reference: {project_ref}")
        logger.info(f"   URL: {supabase_url}")
        print(f"\nProject Reference: {project_ref}")
        print(f"Supabase URL: {supabase_url}")
        print("\n💡 Use this project reference with Supabase MCP tools")
        
        return project_ref
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()






