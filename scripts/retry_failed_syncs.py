#!/usr/bin/env python3
"""
Retry syncing failed posts from SQLite to Supabase.

This script:
1. Gets all unsynced posts from SQLite
2. Attempts to sync them to Supabase
3. Updates sync status in SQLite
4. Reports results
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.database_agent import DatabaseAgent

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Retry syncing failed posts to Supabase')
    parser.add_argument('--limit', type=int, default=100, help='Maximum number of posts to retry (default: 100)')
    args = parser.parse_args()
    
    print("🔄 Retrying failed syncs from SQLite to Supabase...")
    print("=" * 60)
    
    try:
        db_agent = DatabaseAgent()
        
        # Get initial status
        initial_status = db_agent.get_sync_status_report()
        print(f"\n📊 Initial Status:")
        print(f"   Total posts: {initial_status.get('total', 0)}")
        print(f"   Synced: {initial_status.get('synced', 0)}")
        print(f"   Unsynced: {initial_status.get('unsynced', 0)}")
        
        # Retry syncs
        print(f"\n🔄 Retrying sync for up to {args.limit} posts...")
        results = db_agent.retry_failed_syncs(limit=args.limit)
        
        print(f"\n📊 Results:")
        print(f"   Attempted: {results.get('attempted', 0)}")
        print(f"   ✅ Succeeded: {results.get('succeeded', 0)}")
        print(f"   ❌ Failed: {results.get('failed', 0)}")
        
        if results.get('errors'):
            print(f"\n❌ Errors:")
            for error in results['errors'][:10]:  # Show first 10 errors
                print(f"   - {error}")
            if len(results['errors']) > 10:
                print(f"   ... and {len(results['errors']) - 10} more errors")
        
        # Get final status
        final_status = db_agent.get_sync_status_report()
        print(f"\n📊 Final Status:")
        print(f"   Total posts: {final_status.get('total', 0)}")
        print(f"   Synced: {final_status.get('synced', 0)}")
        print(f"   Unsynced: {final_status.get('unsynced', 0)}")
        print(f"   Sync percentage: {final_status.get('sync_percentage', 0.0):.1f}%")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()


