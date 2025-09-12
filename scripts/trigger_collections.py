#!/usr/bin/env python3
"""
Trigger both Twitter and Reddit collections manually
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(project_root))

# Import after setting up paths
from dotenv import load_dotenv
from src.services.database import DatabaseManager
from src.services.collector_runner import collect_twitter_bookmarks_sync, collect_reddit_bookmarks

# Load environment variables
load_dotenv()

def main():
    """Run both Twitter and Reddit collections"""
    print("🚀 Starting manual collection for Twitter and Reddit...")
    print("=" * 60)
    
    # Initialize database manager
    db_path = str(project_root / "data" / "prismind.db")
    print(f"📁 Using database: {db_path}")
    db_manager = DatabaseManager(db_path=db_path)
    
    # Get existing post IDs to avoid duplicates
    existing_posts = db_manager.get_all_posts(include_deleted=False)
    existing_ids = set(existing_posts['post_id'].tolist()) if not existing_posts.empty else set()
    
    # Also get URLs for additional duplicate checking
    existing_urls = set()
    if not existing_posts.empty and 'url' in existing_posts.columns:
        existing_urls = set(existing_posts['url'].dropna().tolist())
    
    print(f"📊 Database contains {len(existing_ids)} existing posts")
    
    total_new = 0
    
    # Run Twitter collection
    print("\n🐦 Running Twitter collection...")
    twitter_count = collect_twitter_bookmarks_sync(db_manager, existing_ids, existing_urls)
    twitter_count = twitter_count or 0  # Handle None return value
    print(f"✅ Twitter collection complete: {twitter_count} new posts")
    total_new += twitter_count
    
    # Run Reddit collection
    print("\n📱 Running Reddit collection...")
    reddit_count = collect_reddit_bookmarks(db_manager, existing_ids, existing_urls)
    reddit_count = reddit_count or 0  # Handle None return value
    print(f"✅ Reddit collection complete: {reddit_count} new posts")
    total_new += reddit_count
    
    print("\n" + "=" * 60)
    print(f"🎉 Collection completed! Total new posts: {total_new}")

if __name__ == "__main__":
    main()