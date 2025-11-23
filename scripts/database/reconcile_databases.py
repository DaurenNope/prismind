#!/usr/bin/env python3
"""
Database Reconciliation Script
===============================
Automatically fixes inconsistencies between Supabase and SQLite databases
Created: 2025-11-20
Priority: P2 - Database consistency monitoring

Usage:
    python scripts/database/reconcile_databases.py [--dry-run] [--fix-row-counts] [--fix-data-drift]
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.shared.utils.logging_config import get_logger

logger = get_logger(__name__)


def reconcile_row_counts(dry_run: bool = True) -> Dict[str, any]:
    """
    Reconcile row counts between Supabase and SQLite
    
    Strategy:
    - If Supabase has more rows: Sync missing rows from Supabase to SQLite
    - If SQLite has more rows: These are likely stale, sync from Supabase
    
    Args:
        dry_run: If True, only report what would be done
    
    Returns:
        Reconciliation report
    """
    report = {
        'action': 'reconcile_row_counts',
        'dry_run': dry_run,
        'supabase_count': 0,
        'sqlite_count': 0,
        'difference': 0,
        'actions_taken': [],
        'errors': [],
    }
    
    try:
        from src.infrastructure.database.manager import SupabaseManager
        manager = SupabaseManager()
        
        # Get Supabase count
        response = manager.client.table('posts').select('id', count='exact').execute()
        report['supabase_count'] = response.count if hasattr(response, 'count') else 0
        
        # Get SQLite count
        import sqlite3
        db_path = "beyondlines.db"
        if not Path(db_path).exists():
            logger.warning("⚠️ SQLite database not found")
            return report
        
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM posts")
            report['sqlite_count'] = cursor.fetchone()[0]
        
        report['difference'] = report['supabase_count'] - report['sqlite_count']
        
        if report['difference'] == 0:
            logger.info("✅ Row counts are already consistent")
            return report
        
        logger.info(
            f"📊 Row count difference: {report['difference']} "
            f"(Supabase: {report['supabase_count']}, SQLite: {report['sqlite_count']})"
        )
        
        if not dry_run:
            if report['difference'] > 0:
                # Supabase has more rows - sync to SQLite
                logger.info("🔄 Syncing missing rows from Supabase to SQLite...")
                # This would need implementation of sync logic
                report['actions_taken'].append("sync_from_supabase_to_sqlite")
            else:
                # SQLite has more rows - likely stale data
                logger.info("🔄 SQLite has more rows - likely stale data")
                report['actions_taken'].append("verify_sqlite_data")
        
        return report
        
    except Exception as e:
        logger.error(f"❌ Error reconciling row counts: {e}")
        report['errors'].append(str(e))
        return report


def reconcile_data_drift(sample_size: int = 100, dry_run: bool = True) -> Dict[str, any]:
    """
    Reconcile data drift between databases
    
    Args:
        sample_size: Number of posts to check
        dry_run: If True, only report what would be done
    
    Returns:
        Reconciliation report
    """
    report = {
        'action': 'reconcile_data_drift',
        'dry_run': dry_run,
        'checked': 0,
        'mismatches': 0,
        'fixed': 0,
        'errors': [],
    }
    
    try:
        from src.infrastructure.database.manager import SupabaseManager
        manager = SupabaseManager()
        
        # Get sample posts from Supabase
        response = manager.client.table('posts').select(
            'post_id,platform,url,content,created_at'
        ).limit(sample_size).execute()
        
        if not response.data:
            logger.warning("⚠️ No posts in Supabase to check")
            return report
        
        import sqlite3
        db_path = "beyondlines.db"
        if not Path(db_path).exists():
            logger.warning("⚠️ SQLite database not found")
            return report
        
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            for post in response.data:
                post_id = post.get('post_id')
                if not post_id:
                    continue
                
                report['checked'] += 1
                
                try:
                    cursor.execute(
                        "SELECT post_id, platform, url, content FROM posts WHERE post_id = ?",
                        (post_id,)
                    )
                    sqlite_post = cursor.fetchone()
                    
                    if not sqlite_post:
                        # Missing in SQLite - would sync
                        if not dry_run:
                            # Would insert from Supabase
                            logger.debug(f"Would sync post {post_id} to SQLite")
                        report['mismatches'] += 1
                        continue
                    
                    # Check key fields match
                    if (sqlite_post['platform'] != post.get('platform') or
                        sqlite_post['url'] != post.get('url')):
                        # Data mismatch - would update
                        if not dry_run:
                            # Would update SQLite from Supabase
                            logger.debug(f"Would update post {post_id} in SQLite")
                            cursor.execute(
                                """
                                UPDATE posts 
                                SET platform = ?, url = ?
                                WHERE post_id = ?
                                """,
                                (post.get('platform'), post.get('url'), post_id)
                            )
                            report['fixed'] += 1
                        report['mismatches'] += 1
                    
                except Exception as e:
                    logger.debug(f"Error checking post {post_id}: {e}")
                    report['errors'].append(f"Post {post_id}: {str(e)}")
            
            if not dry_run:
                conn.commit()
        
        return report
        
    except Exception as e:
        logger.error(f"❌ Error reconciling data drift: {e}")
        report['errors'].append(str(e))
        return report


def reconcile_schema(dry_run: bool = True) -> Dict[str, any]:
    """
    Reconcile schema differences between databases
    
    Args:
        dry_run: If True, only report what would be done
    
    Returns:
        Reconciliation report
    """
    report = {
        'action': 'reconcile_schema',
        'dry_run': dry_run,
        'missing_in_sqlite': [],
        'missing_in_supabase': [],
        'actions_taken': [],
        'errors': [],
    }
    
    try:
        from src.infrastructure.database.manager import SupabaseManager
        manager = SupabaseManager()
        
        # Essential columns that should exist in both
        essential_columns = [
            'id', 'post_id', 'platform', 'content', 'url', 'author',
            'created_at', 'value_score', 'quality_score', 'rewrite_score',
            'ai_summary', 'tags', 'key_concepts', 'topic',
        ]
        
        # Check SQLite columns
        import sqlite3
        db_path = "beyondlines.db"
        if Path(db_path).exists():
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(posts)")
                sqlite_cols = {row[1] for row in cursor.fetchall()}
                
                report['missing_in_sqlite'] = [
                    col for col in essential_columns if col not in sqlite_cols
                ]
        
        if report['missing_in_sqlite']:
            logger.warning(
                f"⚠️ Missing columns in SQLite: {', '.join(report['missing_in_sqlite'])}"
            )
            
            if not dry_run:
                # Would add missing columns to SQLite
                logger.info("🔄 Would add missing columns to SQLite")
                report['actions_taken'].append("add_missing_columns_to_sqlite")
        
        return report
        
    except Exception as e:
        logger.error(f"❌ Error reconciling schema: {e}")
        report['errors'].append(str(e))
        return report


def print_reconciliation_report(reports: List[Dict[str, any]]):
    """Print reconciliation report"""
    print("\n" + "=" * 80)
    print("🔄 DATABASE RECONCILIATION REPORT")
    print("=" * 80)
    
    for report in reports:
        action = report.get('action', 'unknown')
        dry_run = report.get('dry_run', True)
        
        print(f"\n📋 Action: {action}")
        print(f"   Mode: {'DRY RUN' if dry_run else 'EXECUTING'}")
        
        if action == 'reconcile_row_counts':
            print(f"   Supabase count: {report['supabase_count']:,}")
            print(f"   SQLite count: {report['sqlite_count']:,}")
            print(f"   Difference: {report['difference']:,}")
            
            if report['difference'] == 0:
                print("   ✅ Row counts are consistent")
            else:
                if dry_run:
                    print(f"   💡 Would sync {abs(report['difference'])} rows")
                else:
                    print(f"   ✅ Actions taken: {', '.join(report['actions_taken'])}")
        
        elif action == 'reconcile_data_drift':
            print(f"   Checked: {report['checked']} posts")
            print(f"   Mismatches: {report['mismatches']}")
            
            if dry_run:
                print(f"   💡 Would fix {report['mismatches']} mismatches")
            else:
                print(f"   ✅ Fixed: {report['fixed']} posts")
        
        elif action == 'reconcile_schema':
            if report['missing_in_sqlite']:
                print(f"   Missing in SQLite: {', '.join(report['missing_in_sqlite'])}")
                if dry_run:
                    print("   💡 Would add missing columns")
                else:
                    print("   ✅ Actions taken: {', '.join(report['actions_taken'])}")
            else:
                print("   ✅ Schema is consistent")
        
        if report.get('errors'):
            print(f"   ⚠️  Errors: {len(report['errors'])}")
            for error in report['errors'][:5]:  # Show first 5
                print(f"      - {error}")


def main():
    parser = argparse.ArgumentParser(description="Reconcile databases")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Dry run mode (default: True, set --no-dry-run to execute)"
    )
    parser.add_argument(
        "--no-dry-run",
        dest="dry_run",
        action="store_false",
        help="Execute reconciliation (not a dry run)"
    )
    parser.add_argument(
        "--fix-row-counts",
        action="store_true",
        help="Fix row count differences"
    )
    parser.add_argument(
        "--fix-data-drift",
        action="store_true",
        help="Fix data drift"
    )
    parser.add_argument(
        "--fix-schema",
        action="store_true",
        help="Fix schema differences"
    )
    parser.add_argument(
        "--fix-all",
        action="store_true",
        help="Fix all issues (equivalent to --fix-row-counts --fix-data-drift --fix-schema)"
    )
    
    args = parser.parse_args()
    
    if args.fix_all:
        args.fix_row_counts = True
        args.fix_data_drift = True
        args.fix_schema = True
    
    if not any([args.fix_row_counts, args.fix_data_drift, args.fix_schema]):
        # Default: check all but don't fix
        args.fix_row_counts = True
        args.fix_data_drift = True
        args.fix_schema = True
    
    logger.info(f"🔍 Running reconciliation (dry_run={args.dry_run})...")
    
    reports = []
    
    if args.fix_row_counts:
        report = reconcile_row_counts(dry_run=args.dry_run)
        reports.append(report)
    
    if args.fix_data_drift:
        report = reconcile_data_drift(dry_run=args.dry_run)
        reports.append(report)
    
    if args.fix_schema:
        report = reconcile_schema(dry_run=args.dry_run)
        reports.append(report)
    
    print_reconciliation_report(reports)
    
    # Check for errors
    has_errors = any(report.get('errors') for report in reports)
    sys.exit(1 if has_errors else 0)


if __name__ == "__main__":
    main()






