#!/usr/bin/env python3
"""
SQLite Database Performance Indexes
====================================
Adds missing indexes for common query patterns in SQLite database
Created: 2025-11-20
Priority: P0 - Critical for query performance

Usage:
    python migrations/2025_11_20_sqlite_indexes.py [--db-path=<path>]
"""

import argparse
import sqlite3
import sys
from pathlib import Path
from typing import List, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


def create_indexes(db_path: str) -> Tuple[int, int]:
    """
    Create missing indexes in SQLite database
    
    Returns:
        Tuple of (created_count, existing_count)
    """
    created = 0
    existing = 0
    
    indexes = [
        # Compound index for platform + created_at queries
        (
            "idx_posts_platform_created_at",
            "CREATE INDEX IF NOT EXISTS idx_posts_platform_created_at ON posts (platform, created_at DESC)"
        ),
        # Single column index for created_at (if not exists)
        (
            "idx_posts_created_at",
            "CREATE INDEX IF NOT EXISTS idx_posts_created_at ON posts (created_at DESC)"
        ),
        # Single column index for value_score
        (
            "idx_posts_value_score",
            "CREATE INDEX IF NOT EXISTS idx_posts_value_score ON posts (value_score DESC)"
        ),
        # Single column index for rewrite_score
        (
            "idx_posts_rewrite_score",
            "CREATE INDEX IF NOT EXISTS idx_posts_rewrite_score ON posts (rewrite_score DESC)"
        ),
        # Compound index for platform + value_score + created_at
        (
            "idx_posts_platform_value_score",
            "CREATE INDEX IF NOT EXISTS idx_posts_platform_value_score ON posts (platform, value_score DESC, created_at DESC)"
        ),
        # Index for rewrite candidates (SQLite doesn't support partial indexes, so we create a regular index)
        (
            "idx_posts_rewrite_candidate_score",
            "CREATE INDEX IF NOT EXISTS idx_posts_rewrite_candidate_score ON posts (is_rewrite_candidate, rewrite_score DESC)"
        ),
    ]
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Check existing indexes
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type = 'index' 
                AND tbl_name = 'posts'
            """)
            existing_indexes = {row[0] for row in cursor.fetchall()}
            
            # Create missing indexes
            for index_name, sql in indexes:
                if index_name in existing_indexes:
                    logger.debug(f"Index {index_name} already exists")
                    existing += 1
                else:
                    try:
                        cursor.execute(sql)
                        logger.info(f"✅ Created index: {index_name}")
                        created += 1
                    except sqlite3.Error as e:
                        logger.warning(f"⚠️ Failed to create index {index_name}: {e}")
            
            conn.commit()
            
            # Verify indexes
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type = 'index' 
                AND tbl_name = 'posts'
                ORDER BY name
            """)
            all_indexes = [row[0] for row in cursor.fetchall()]
            logger.info(f"📊 Total indexes on posts table: {len(all_indexes)}")
            
            return created, existing
            
    except sqlite3.Error as e:
        logger.error(f"❌ Database error: {e}")
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        raise


def verify_indexes(db_path: str) -> List[str]:
    """Verify that indexes exist and return list of index names"""
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type = 'index' 
                AND tbl_name = 'posts'
                ORDER BY name
            """)
            return [row[0] for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logger.error(f"❌ Error verifying indexes: {e}")
        return []


def main():
    parser = argparse.ArgumentParser(description="Create SQLite database indexes")
    parser.add_argument(
        "--db-path",
        type=str,
        default="beyondlines.db",
        help="Path to SQLite database file (default: beyondlines.db)"
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only verify existing indexes, don't create new ones"
    )
    
    args = parser.parse_args()
    
    db_path = args.db_path
    if not Path(db_path).exists():
        logger.error(f"❌ Database file not found: {db_path}")
        sys.exit(1)
    
    logger.info(f"📊 Working with database: {db_path}")
    
    if args.verify_only:
        indexes = verify_indexes(db_path)
        logger.info(f"✅ Found {len(indexes)} indexes:")
        for idx in indexes:
            logger.info(f"  - {idx}")
    else:
        created, existing = create_indexes(db_path)
        logger.info(f"\n📊 Index Creation Summary:")
        logger.info(f"  ✅ Created: {created}")
        logger.info(f"  ℹ️  Existing: {existing}")
        logger.info(f"  📦 Total: {created + existing}")
        
        if created > 0:
            logger.info("\n✅ Index creation complete!")
        else:
            logger.info("\nℹ️  All indexes already exist")


if __name__ == "__main__":
    main()

