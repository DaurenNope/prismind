#!/usr/bin/env python3
"""
Diagnostic script to check why Twitter posts aren't appearing in Supabase
"""

import os
import sys
from datetime import datetime, timedelta, timezone

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.manager import SupabaseManager
from src.storage.db import StorageFacade
from src.utils.post_validator import validate_post

def main():
    print("=" * 60)
    print("Twitter Posts Supabase Diagnostic")
    print("=" * 60)
    
    # Initialize managers
    try:
        supabase_manager = SupabaseManager()
        storage = StorageFacade()
        print("✅ Managers initialized\n")
    except Exception as e:
        print(f"❌ Failed to initialize managers: {e}")
        return
    
    # Check recent Twitter posts in Supabase
    print("1. Checking recent Twitter posts in Supabase...")
    try:
        result = (
            supabase_manager.client.table("posts")
            .select("post_id, platform, url, author, content, collected_at, created_at")
            .eq("platform", "twitter")
            .order("collected_at", desc=True)
            .limit(20)
            .execute()
        )
        
        posts = result.data or []
        print(f"   Found {len(posts)} recent Twitter posts in Supabase")
        
        if posts:
            print("\n   Most recent posts:")
            for i, post in enumerate(posts[:5], 1):
                post_id = post.get("post_id", "N/A")
                collected_at = post.get("collected_at") or post.get("created_at", "N/A")
                author = post.get("author", "N/A")
                content_preview = (post.get("content", "")[:60] + "...") if len(post.get("content", "")) > 60 else post.get("content", "")
                print(f"   {i}. {post_id} | {author} | {collected_at}")
                print(f"      Content: {content_preview}")
        else:
            print("   ⚠️ No Twitter posts found in Supabase!")
        
        print()
    except Exception as e:
        print(f"   ❌ Error querying Supabase: {e}\n")
    
    # Check posts from last 24 hours
    print("2. Checking Twitter posts from last 24 hours...")
    try:
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        result = (
            supabase_manager.client.table("posts")
            .select("post_id, platform, collected_at")
            .eq("platform", "twitter")
            .gte("collected_at", yesterday)
            .order("collected_at", desc=True)
            .execute()
        )
        
        recent_posts = result.data or []
        print(f"   Found {len(recent_posts)} Twitter posts from last 24 hours")
        
        if recent_posts:
            print("\n   Recent post IDs:")
            for post in recent_posts[:10]:
                print(f"   - {post.get('post_id')} (collected: {post.get('collected_at')})")
        else:
            print("   ⚠️ No Twitter posts from last 24 hours!")
        
        print()
    except Exception as e:
        print(f"   ❌ Error querying recent posts: {e}\n")
    
    # Check SQLite for comparison
    print("3. Checking SQLite for Twitter posts...")
    try:
        sqlite_posts = storage.get_posts(limit=100)
        twitter_sqlite = [p for p in sqlite_posts if p.get("platform", "").lower() == "twitter"]
        print(f"   Found {len(twitter_sqlite)} Twitter posts in SQLite (last 100 posts)")
        
        if twitter_sqlite:
            recent_sqlite = [p for p in twitter_sqlite if p.get("collected_at")]
            if recent_sqlite:
                # Sort by collected_at
                recent_sqlite.sort(key=lambda x: x.get("collected_at", ""), reverse=True)
                print(f"\n   Most recent SQLite posts (last 5):")
                for i, post in enumerate(recent_sqlite[:5], 1):
                    post_id = post.get("post_id", "N/A")
                    collected_at = post.get("collected_at", "N/A")
                    author = post.get("author", "N/A")
                    print(f"   {i}. {post_id} | {author} | {collected_at}")
        print()
    except Exception as e:
        print(f"   ❌ Error querying SQLite: {e}\n")
    
    # Test validation on a sample post structure
    print("4. Testing post validation...")
    sample_post = {
        "post_id": "twitter_1234567890",
        "platform": "twitter",
        "url": "https://twitter.com/user/status/1234567890",
        "author": "test_user",
        "content": "This is a test tweet with enough content to pass validation",
        "collected_at": datetime.now(timezone.utc).isoformat(),
    }
    
    validation = validate_post(sample_post, strict=True)
    if validation.is_valid:
        print("   ✅ Sample post passes validation")
    else:
        print(f"   ❌ Sample post fails validation: {', '.join(validation.errors)}")
    print()
    
    # Check Supabase connection
    print("5. Testing Supabase connection...")
    try:
        # Try a simple query
        test_result = (
            supabase_manager.client.table("posts")
            .select("count")
            .execute()
        )
        print("   ✅ Supabase connection working")
    except Exception as e:
        print(f"   ❌ Supabase connection issue: {e}")
    print()
    
    print("=" * 60)
    print("Diagnostic complete")
    print("=" * 60)
    
    # Recommendations
    print("\nRecommendations:")
    if not posts:
        print("  - No Twitter posts found in Supabase")
        print("  - Check collection logs for validation errors")
        print("  - Verify posts are being saved via StorageFacade.save_post()")
    elif len(recent_posts) == 0:
        print("  - No recent Twitter posts (last 24 hours)")
        print("  - Check if collection is running successfully")
        print("  - Verify posts are passing validation")
    else:
        print("  - Twitter posts are in Supabase")
        print("  - Check your query filters (platform, date range, etc.)")

if __name__ == "__main__":
    main()

