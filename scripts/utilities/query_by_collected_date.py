#!/usr/bin/env python3
"""
Example of how to correctly query posts by collected_at date
"""

import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.manager import SupabaseManager

def show_correct_queries():
    """Show correct ways to query by collected_at"""
    
    supabase = SupabaseManager()
    client = supabase.client
    
    print("=" * 60)
    print("Correct Ways to Query by collected_at")
    print("=" * 60)
    
    # Method 1: Sort by collected_at DESC (newest first)
    print("\n1. Sort by collected_at DESC (newest collected first):")
    result = (
        client.table("posts")
        .select("post_id, collected_at, author")
        .eq("platform", "twitter")
        .order("collected_at", desc=True)
        .limit(10)
        .execute()
    )
    
    print("   Top 10 posts (newest collected_at first):")
    for i, post in enumerate(result.data, 1):
        collected = post.get('collected_at', 'NULL')
        print(f"   {i}. {post.get('post_id')} | {collected}")
    
    # Method 2: Filter by date range
    print("\n2. Filter posts from today (last 24 hours):")
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    result = (
        client.table("posts")
        .select("post_id, collected_at, author")
        .eq("platform", "twitter")
        .gte("collected_at", yesterday)  # Greater than or equal to yesterday
        .order("collected_at", desc=True)
        .execute()
    )
    
    print(f"   Found {len(result.data)} posts from last 24 hours")
    for i, post in enumerate(result.data[:10], 1):
        collected = post.get('collected_at', 'NULL')
        print(f"   {i}. {post.get('post_id')} | {collected}")
    
    # Method 3: Filter by specific date
    print("\n3. Filter posts from a specific date (2025-11-22):")
    start_date = datetime(2025, 11, 22, 0, 0, 0, tzinfo=timezone.utc).isoformat()
    end_date = datetime(2025, 11, 23, 0, 0, 0, tzinfo=timezone.utc).isoformat()
    
    result = (
        client.table("posts")
        .select("post_id, collected_at, author")
        .eq("platform", "twitter")
        .gte("collected_at", start_date)
        .lt("collected_at", end_date)
        .order("collected_at", desc=True)
        .execute()
    )
    
    print(f"   Found {len(result.data)} posts from 2025-11-22")
    for i, post in enumerate(result.data[:10], 1):
        collected = post.get('collected_at', 'NULL')
        print(f"   {i}. {post.get('post_id')} | {collected}")
    
    # Method 4: Find your specific posts
    print("\n4. Finding your specific posts:")
    target_ids = [
        "twitter_1991901617994743848",  # zksync
        "twitter_1991728344124256441",  # Warren Buffett
    ]
    
    for post_id in target_ids:
        result = (
            client.table("posts")
            .select("post_id, collected_at, created_at")
            .eq("post_id", post_id)
            .execute()
        )
        
        if result.data:
            post = result.data[0]
            collected = post.get('collected_at')
            created = post.get('created_at')
            
            # Show where it ranks
            result_rank = (
                client.table("posts")
                .select("post_id")
                .eq("platform", "twitter")
                .gte("collected_at", collected)
                .order("collected_at", desc=True)
                .execute()
            )
            
            rank = len(result_rank.data) if result_rank.data else "?"
            print(f"\n   {post_id}:")
            print(f"   - Rank by collected_at: #{rank} (out of all Twitter posts)")
            print(f"   - collected_at: {collected}")
            print(f"   - created_at: {created}")
    
    print("\n" + "=" * 60)
    print("Key Points:")
    print("=" * 60)
    print("1. Use .order('collected_at', desc=True) for newest first")
    print("2. Use .gte('collected_at', date) to filter by date range")
    print("3. Your posts are sorted correctly - they were collected at 15:11")
    print("4. Posts collected at 15:12 will appear before yours")
    print("5. If you want to see YOUR posts first, query them by ID or filter by author")

if __name__ == "__main__":
    show_correct_queries()

