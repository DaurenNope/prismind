#!/usr/bin/env python3
"""
Example script showing how to query Twitter posts from Supabase correctly
"""

import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.manager import SupabaseManager

def query_twitter_posts():
    """Show different ways to query Twitter posts from Supabase"""
    
    supabase = SupabaseManager()
    client = supabase.client
    
    print("=" * 60)
    print("How to Query Twitter Posts from Supabase")
    print("=" * 60)
    
    # Method 1: All Twitter posts, ordered by collected_at (most recent first)
    print("\n1. All Twitter posts (most recent first):")
    result = (
        client.table("posts")
        .select("*")
        .eq("platform", "twitter")
        .order("collected_at", desc=True)
        .limit(10)
        .execute()
    )
    print(f"   Found {len(result.data)} posts")
    for post in result.data[:5]:
        print(f"   - {post.get('post_id')} | {post.get('author')} | {post.get('collected_at')}")
    
    # Method 2: Twitter posts from last 24 hours
    print("\n2. Twitter posts from last 24 hours:")
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    result = (
        client.table("posts")
        .select("*")
        .eq("platform", "twitter")
        .gte("collected_at", yesterday)
        .order("collected_at", desc=True)
        .execute()
    )
    print(f"   Found {len(result.data)} posts")
    
    # Method 3: Twitter posts by post_id
    print("\n3. Query specific post by ID:")
    test_id = "twitter_1989057614555017588"
    result = (
        client.table("posts")
        .select("*")
        .eq("platform", "twitter")
        .eq("post_id", test_id)
        .execute()
    )
    if result.data:
        print(f"   ✅ Found post: {result.data[0].get('post_id')}")
    else:
        print(f"   ❌ Post not found: {test_id}")
    
    # Method 4: Count all Twitter posts
    print("\n4. Total Twitter posts count:")
    result = (
        client.table("posts")
        .select("post_id", count="exact")
        .eq("platform", "twitter")
        .execute()
    )
    print(f"   Total: {result.count} Twitter posts")
    
    # Method 5: Check what columns are available
    print("\n5. Sample post structure (columns):")
    result = (
        client.table("posts")
        .select("*")
        .eq("platform", "twitter")
        .limit(1)
        .execute()
    )
    if result.data:
        sample = result.data[0]
        print(f"   Available columns: {', '.join(sorted(sample.keys()))}")
    
    print("\n" + "=" * 60)
    print("Query Tips:")
    print("=" * 60)
    print("1. Always filter by platform: .eq('platform', 'twitter')")
    print("2. Use collected_at for sorting (not created_at)")
    print("3. Check both collected_at and created_at fields")
    print("4. Make sure you're querying the 'posts' table")
    print("5. Use .order('collected_at', desc=True) for newest first")

if __name__ == "__main__":
    query_twitter_posts()

