#!/usr/bin/env python3
"""
Run the Reddit collector with proper database and state management initialization.
"""
import asyncio
import os
import sys
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from src.services.new_database_manager import SQLiteManager
from src.scrape_state_manager import ScrapeStateManager
from src.services.collector_runner import collect_reddit_bookmarks

async def main():
    # Initialize database manager
    db_manager = SQLiteManager()
    
    # Initialize state manager
    state_manager = ScrapeStateManager()
    
    # Get existing post IDs to avoid duplicates
    existing_ids = set()
    try:
        existing_posts = db_manager.get_all_posts()
        if not existing_posts.empty and 'post_id' in existing_posts.columns:
            existing_ids.update(existing_posts['post_id'].dropna().astype(str).tolist())
        print(f"🔍 Found {len(existing_ids)} existing posts in database")
    except Exception as e:
        print(f"⚠️ Could not fetch existing posts: {e}")
    
    # Run the Reddit collector
    print("🚀 Starting Reddit collection...")
    try:
        await collect_reddit_bookmarks(db_manager, existing_ids)
        print("✅ Reddit collection completed successfully")
    except Exception as e:
        print(f"❌ Error during Reddit collection: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Clean up
        if hasattr(db_manager, 'close'):
            db_manager.close()

if __name__ == "__main__":
    asyncio.run(main())
