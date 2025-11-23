#!/usr/bin/env python3
"""
Safe Supabase Cleanup - Deletes only bad posts, not all
"""

import sys
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

load_dotenv(override=True)

from src.infrastructure.database.manager import SupabaseManager
from src.services.new_database_manager import get_database_manager


def main():
    print("╔═══════════════════════════════════╗")
    print("║  SAFE SUPABASE CLEANUP            ║")
    print("╚═══════════════════════════════════╝\n")
    
    # Connect
    print("1️⃣ Connecting to Supabase...")
    try:
        supabase = SupabaseManager()
        print("✅ Connected\n")
    except Exception as e:
        print(f"❌ Failed: {e}")
        return
    
    # Get bad posts (missing post_id or other critical fields)
    print("2️⃣ Finding bad posts...")
    result = supabase.client.table('posts').select('*').execute()
    
    all_posts = result.data
    print(f"Total posts: {len(all_posts)}")
    
    bad_posts = []
    for post in all_posts:
        # Check if post is bad
        if not post.get('post_id') or not post.get('post_id').strip():
            bad_posts.append(post)
        elif not post.get('platform'):
            bad_posts.append(post)
        elif not post.get('content') or len(post.get('content', '')) < 10:
            bad_posts.append(post)
    
    print(f"Bad posts found: {len(bad_posts)}\n")
    
    if not bad_posts:
        print("✅ No bad posts found! Your data is clean.")
        return
    
    # Show sample
    print("📋 Sample bad posts:")
    for i, post in enumerate(bad_posts[:5], 1):
        print(f"{i}. ID: {post.get('id')}")
        print(f"   Post ID: {post.get('post_id', 'MISSING')}")
        print(f"   Platform: {post.get('platform', 'MISSING')}")
        print(f"   Content: {(post.get('content') or 'MISSING')[:50]}...")
        print()
    
    # Confirm deletion
    print(f"⚠️ About to delete {len(bad_posts)} bad posts.")
    confirm = input("Continue? (y/n): ")
    
    if confirm.lower() != 'y':
        print("❌ Cancelled")
        return
    
    # Delete bad posts
    print("\n3️⃣ Deleting bad posts...")
    deleted = 0
    errors = 0
    
    for post in bad_posts:
        try:
            supabase.client.table('posts').delete().eq('id', post['id']).execute()
            deleted += 1
            if deleted % 10 == 0:
                print(f"   Deleted {deleted}/{len(bad_posts)}...")
        except Exception as e:
            errors += 1
            if errors < 3:
                print(f"   ⚠️ Error deleting {post.get('id')}: {e}")
    
    print(f"\n✅ Cleanup complete!")
    print(f"   Deleted: {deleted}")
    print(f"   Errors: {errors}")
    print(f"   Remaining: {len(all_posts) - deleted}")
    
    # Now optionally sync missing good posts from local
    print("\n4️⃣ Would you like to sync missing posts from local DB? (y/n): ", end='')
    sync = input()
    
    if sync.lower() == 'y':
        print("\nSyncing from local database...")
        db = get_database_manager()
        local_posts = db.get_all_posts(include_deleted=False)
        
        # Get post_ids already in Supabase
        current_result = supabase.client.table('posts').select('post_id').execute()
        existing_ids = {p['post_id'] for p in current_result.data if p.get('post_id')}
        
        print(f"Local DB: {len(local_posts)} posts")
        print(f"Supabase: {len(existing_ids)} post_ids")
        
        # Find missing
        synced = 0
        skipped = 0
        
        for post in local_posts:
            post_id = post.get('post_id')
            
            if not post_id or post_id in existing_ids:
                skipped += 1
                continue
            
            # Clean and insert
            try:
                result = supabase.insert_post(post)
                if result:
                    synced += 1
                    if synced % 10 == 0:
                        print(f"   Synced {synced}...")
            except Exception as e:
                if synced + skipped < 3:
                    print(f"   ⚠️ Error: {e}")
        
        print(f"\n✅ Sync complete!")
        print(f"   Synced: {synced} new posts")
        print(f"   Skipped: {skipped} (already exist)")
    
    print("\n╔═══════════════════════════════════╗")
    print("║  CLEANUP COMPLETE                 ║")
    print("╚═══════════════════════════════════╝")


if __name__ == "__main__":
    main()
