#!/usr/bin/env python3
"""
Supabase Cleanup and Resync Script
Cleans up messed up data and resyncs from local database
"""

import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Force reload environment variables
load_dotenv(override=True)

from src.supabase_manager import SupabaseManager
from src.services.new_database_manager import get_database_manager
from datetime import datetime


def clean_post_data(post):
    """Clean and validate post data before syncing"""
    
    # Required fields
    required = ['platform', 'post_id']
    for field in required:
        if not post.get(field):
            print(f"⚠️ Skipping post - missing {field}")
            return None
    
    # Clean data - remove None values and empty strings from critical fields
    cleaned = {}
    
    # Critical fields - must have value
    critical_fields = {
        'post_id': post.get('post_id'),
        'platform': post.get('platform'),
        'content': post.get('content') or post.get('title') or 'No content',
        'author': post.get('author') or 'Unknown',
        'created_at': post.get('created_at') or datetime.now().isoformat(),
    }
    
    # Optional fields - only include if not empty
    optional_fields = [
        'url', 'title', 'author_handle', 'post_type',
        'subreddit', 'category', 'value_score', 'sentiment',
        'ai_summary', 'key_concepts', 'smart_tags',
        'intelligence_analysis', 'actionable_insights',
        'quality_score', 'topic', 'content_type',
        'media_urls', 'hashtags', 'mentions', 'engagement'
    ]
    
    # Add critical fields
    cleaned.update(critical_fields)
    
    # Add optional fields if they have values
    for field in optional_fields:
        value = post.get(field)
        if value is not None and value != '':
            cleaned[field] = value
    
    return cleaned


async def main():
    """Main cleanup function"""
    
    print("╔═══════════════════════════════════╗")
    print("║  SUPABASE CLEANUP & RESYNC        ║")
    print("╚═══════════════════════════════════╝\n")
    
    # Step 1: Connect to Supabase
    print("1️⃣ Connecting to Supabase...")
    try:
        supabase = SupabaseManager()
        print("✅ Connected to Supabase\n")
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        print("\n💡 Fix your .env file:")
        print("   SUPABASE_URL=your_url")
        print("   SUPABASE_SERVICE_ROLE_KEY=your_full_key")
        return
    
    # Step 2: Get choice from user
    print("2️⃣ Choose action:")
    print("   1. View latest posts (diagnostic)")
    print("   2. Delete all posts (clean slate)")
    print("   3. Delete posts from last 24 hours")
    print("   4. Resync from local database")
    print("   5. Full cleanup and resync\n")
    
    choice = input("Enter choice (1-5): ").strip()
    
    if choice == "1":
        # View latest posts
        print("\n📊 Latest 20 posts in Supabase:")
        result = supabase.client.table('posts').select('*').order('created_at', desc=True).limit(20).execute()
        
        for i, post in enumerate(result.data, 1):
            print(f"\n{i}. ID: {post.get('id')}")
            print(f"   Platform: {post.get('platform')}")
            print(f"   Post ID: {post.get('post_id')}")
            print(f"   Author: {post.get('author')}")
            print(f"   Content: {(post.get('content') or '')[:60]}...")
            
            # Count blank fields
            blank = sum(1 for k, v in post.items() if v is None or v == '')
            total = len(post)
            print(f"   Data quality: {total - blank}/{total} fields filled")
    
    elif choice == "2":
        # Delete all
        confirm = input("\n⚠️ Delete ALL posts? Type 'DELETE ALL' to confirm: ")
        if confirm == "DELETE ALL":
            print("🗑️ Deleting all posts...")
            result = supabase.client.table('posts').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
            print(f"✅ Deleted all posts")
        else:
            print("❌ Cancelled")
    
    elif choice == "3":
        # Delete recent
        from datetime import datetime, timedelta
        cutoff = (datetime.now() - timedelta(days=1)).isoformat()
        
        confirm = input(f"\n⚠️ Delete posts after {cutoff}? (y/n): ")
        if confirm.lower() == 'y':
            print("🗑️ Deleting recent posts...")
            result = supabase.client.table('posts').delete().gte('created_at', cutoff).execute()
            print(f"✅ Deleted recent posts")
        else:
            print("❌ Cancelled")
    
    elif choice == "4" or choice == "5":
        # Resync
        if choice == "5":
            confirm = input("\n⚠️ This will DELETE ALL and resync. Continue? (y/n): ")
            if confirm.lower() == 'y':
                print("🗑️ Cleaning Supabase...")
                supabase.client.table('posts').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
                print("✅ Cleaned\n")
            else:
                print("❌ Cancelled")
                return
        
        print("3️⃣ Loading local database...")
        db = get_database_manager()
        posts = db.get_all_posts(include_deleted=False)
        print(f"✅ Found {len(posts)} posts in local DB\n")
        
        print("4️⃣ Syncing to Supabase...")
        synced = 0
        skipped = 0
        errors = 0
        
        for i, post in enumerate(posts, 1):
            try:
                # Clean the data
                clean_data = clean_post_data(post)
                
                if not clean_data:
                    skipped += 1
                    continue
                
                # Try to insert
                result = supabase.insert_post(clean_data)
                
                if result:
                    synced += 1
                    if synced % 10 == 0:
                        print(f"   Synced {synced}/{len(posts)}...")
                else:
                    skipped += 1
                    
            except Exception as e:
                errors += 1
                if errors < 5:  # Only show first 5 errors
                    print(f"   ⚠️ Error on post {i}: {e}")
        
        print(f"\n✅ Sync complete!")
        print(f"   Synced: {synced}")
        print(f"   Skipped: {skipped} (duplicates)")
        print(f"   Errors: {errors}")
    
    else:
        print("❌ Invalid choice")
    
    print("\n╔═══════════════════════════════════╗")
    print("║  CLEANUP COMPLETE                 ║")
    print("╚═══════════════════════════════════╝")


if __name__ == "__main__":
    asyncio.run(main())
