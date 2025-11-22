#!/usr/bin/env python3
"""
Re-collect the latest 150 posts to get the latest data
"""

import os
import sys
import asyncio
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.manager import SupabaseManager
from src.storage.db import StorageFacade
from src.pipeline.orchestrator import Orchestrator

async def recollect_latest_posts():
    """Re-collect the latest 150 posts"""
    
    print("=" * 60)
    print("Re-collecting Latest 150 Posts")
    print("=" * 60)
    
    supabase = SupabaseManager()
    client = supabase.client
    storage = StorageFacade()
    
    # Get latest 150 posts from all platforms
    print("\n1. Fetching latest 150 posts from Supabase...")
    
    result = (
        client.table("posts")
        .select("post_id, platform, url, collected_at")
        .order("collected_at", desc=True)
        .limit(150)
        .execute()
    )
    
    posts = result.data or []
    
    if not posts:
        print("⚠️  No posts found in Supabase")
        return
    
    print(f"   Found {len(posts)} posts to re-collect")
    
    # Group by platform
    by_platform = {}
    for post in posts:
        platform = post.get("platform", "unknown")
        if platform not in by_platform:
            by_platform[platform] = []
        by_platform[platform].append(post)
    
    print(f"\n   Posts by platform:")
    for platform, platform_posts in by_platform.items():
        print(f"   - {platform}: {len(platform_posts)} posts")
    
    # Strategy: Instead of trying to re-collect individual posts,
    # we'll trigger a fresh collection which will automatically
    # detect and update truncated posts
    
    print("\n2. Triggering fresh collection for all platforms...")
    print("   (This will automatically detect and update truncated posts)")
    
    orchestrator = Orchestrator()
    
    # Collect from all platforms
    platforms = list(by_platform.keys())
    
    print(f"\n   Collecting from: {', '.join(platforms)}")
    
    results = await orchestrator.collect_all(platforms=platforms)
    
    print("\n" + "=" * 60)
    print("Collection Results:")
    print("=" * 60)
    
    for platform, result in results.items():
        # Handle both dict and int results
        if isinstance(result, dict):
            count = result.get("count", 0) if isinstance(result.get("count"), int) else 0
        elif isinstance(result, (int, float)):
            count = int(result)
        else:
            count = 0
        
        status = "✅" if count > 0 else "⚠️"
        print(f"{status} {platform}: {count} posts collected/updated")
    
    # Verify the latest posts were updated
    print("\n3. Verifying latest posts were updated...")
    
    result = (
        client.table("posts")
        .select("post_id, platform, collected_at, updated_at")
        .order("collected_at", desc=True)
        .limit(10)
        .execute()
    )
    
    if result.data:
        print("\n   Most recently collected posts:")
        for post in result.data:
            post_id = post.get("post_id", "N/A")
            platform = post.get("platform", "N/A")
            collected = post.get("collected_at", "N/A")
            updated = post.get("updated_at", "N/A")
            print(f"   - {post_id} ({platform}) | collected: {collected} | updated: {updated}")
    
    print("\n" + "=" * 60)
    print("✅ Re-collection complete!")
    print("=" * 60)
    print("\nNote: The collector automatically detects truncated posts")
    print("and re-collects them to get full content. Posts that are")
    print("already complete will be skipped.")

if __name__ == "__main__":
    asyncio.run(recollect_latest_posts())

