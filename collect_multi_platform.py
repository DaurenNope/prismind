#!/usr/bin/env python3
"""
Multi-Platform Bookmark Collection - Extract from Twitter, Reddit, and Threads
"""

import sys
import os
import asyncio
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup paths
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

from core.extraction.twitter_extractor_playwright import TwitterExtractorPlaywright
from core.extraction.reddit_extractor import RedditExtractor
from core.extraction.threads_extractor import ThreadsExtractor
from scripts.database_manager import DatabaseManager

async def collect_twitter_bookmarks(db_manager, existing_ids):
    """Collect Twitter bookmarks"""
    print("\n🐦 TWITTER COLLECTION")
    print("-" * 30)
    
    # Get Twitter credentials
    twitter_username = os.getenv('TWITTER_USERNAME')
    if not twitter_username:
        config_dir = project_root / "config"
        if config_dir.exists():
            cookie_files = list(config_dir.glob("twitter_cookies_*.json"))
            if cookie_files:
                cookie_file = cookie_files[0]
                twitter_username = cookie_file.stem.replace("twitter_cookies_", "")
                print(f"🔍 Found existing session for: {twitter_username}")
    
    if not twitter_username:
        print("❌ No Twitter username found. Please set TWITTER_USERNAME environment variable.")
        return 0
    
    try:
        extractor = TwitterExtractorPlaywright(
            username=twitter_username,
            headless=True,
            cookie_file=str(project_root / "config" / f"twitter_cookies_{twitter_username}.json")
        )
        
        print("🔍 Extracting Twitter SAVED posts (bookmarks only)...")
        saved_posts = await extractor.get_saved_posts()
        
        if saved_posts:
            print(f"🔍 Found {len(saved_posts)} Twitter posts")
            new_posts = []
            for post in saved_posts:
                post_dict = post.__dict__ if hasattr(post, '__dict__') else post
                post_id = post_dict.get('post_id')
                
                print(f"   📝 Checking post: {post_id} - {'NEW' if post_id not in existing_ids else 'EXISTS'}")
                
                if post_id not in existing_ids:
                    new_posts.append(post_dict)
                    existing_ids.add(post_id)
            
            # Add new posts to database
            for post_dict in new_posts:
                db_manager.add_post(post_dict)
            
            print(f"✅ Twitter: {len(new_posts)} new bookmarks added")
            return len(new_posts)
        else:
            print("📭 No Twitter bookmarks found")
            return 0
            
    except Exception as e:
        print(f"❌ Twitter collection error: {e}")
        return 0
    finally:
        try:
            await extractor.close()
        except:
            pass

def collect_reddit_bookmarks(db_manager, existing_ids):
    """Collect Reddit saved posts"""
    print("\n🤖 REDDIT COLLECTION")
    print("-" * 30)
    
    # Check for Reddit credentials
    reddit_client_id = os.getenv('REDDIT_CLIENT_ID')
    reddit_client_secret = os.getenv('REDDIT_CLIENT_SECRET')
    reddit_username = os.getenv('REDDIT_USERNAME')
    reddit_password = os.getenv('REDDIT_PASSWORD')
    reddit_user_agent = os.getenv('REDDIT_USER_AGENT', 'PrisMind:1.0 (by /u/YourUsername)')
    
    if not (reddit_client_id and reddit_client_secret and reddit_username and reddit_password):
        print("❌ Reddit credentials not found. Please set:")
        print("   REDDIT_CLIENT_ID")
        print("   REDDIT_CLIENT_SECRET") 
        print("   REDDIT_USERNAME")
        print("   REDDIT_PASSWORD")
        print("   REDDIT_USER_AGENT (optional)")
        return 0
    
    try:
        extractor = RedditExtractor(
            client_id=reddit_client_id,
            client_secret=reddit_client_secret,
            user_agent=reddit_user_agent,
            username=reddit_username,
            password=reddit_password
        )
        
        print("🔍 Extracting Reddit saved posts...")
        saved_posts = extractor.get_saved_posts()
        
        if saved_posts:
            new_posts = []
            for post in saved_posts:
                post_dict = post.__dict__ if hasattr(post, '__dict__') else post
                post_id = post_dict.get('post_id')
                
                if post_id not in existing_ids:
                    new_posts.append(post_dict)
                    existing_ids.add(post_id)
            
            # Add new posts to database
            for post_dict in new_posts:
                db_manager.add_post(post_dict)
            
            print(f"✅ Reddit: {len(new_posts)} new bookmarks added")
            return len(new_posts)
        else:
            print("📭 No Reddit bookmarks found")
            return 0
            
    except Exception as e:
        print(f"❌ Reddit collection error: {e}")
        return 0

async def collect_threads_bookmarks(db_manager, existing_ids):
    """Collect Threads saved posts"""
    print("\n🧵 THREADS COLLECTION")
    print("-" * 30)
    
    # Check for Threads cookies
    threads_cookie = project_root / "config" / "threads_cookies_qronoya.json"
    
    if not threads_cookie.exists():
        print("❌ Threads cookie file not found")
        print("   Expected: config/threads_cookies_qronoya.json")
        return 0
    
    try:
        extractor = ThreadsExtractor()
        
        # Try to authenticate with existing cookies
        auth_success = await extractor.authenticate(
            username="qronoya",  # Default username from cookie file name
            password="",  # Empty password when using cookies
            cookies_path=str(threads_cookie)
        )
        
        if not auth_success:
            print("❌ Threads authentication failed")
            return 0
        
        print("🔍 Extracting Threads saved posts...")
        saved_posts = await extractor.get_saved_posts()
        
        if saved_posts:
            new_posts = []
            for post in saved_posts:
                post_dict = post.__dict__ if hasattr(post, '__dict__') else post
                post_id = post_dict.get('post_id')
                
                if post_id not in existing_ids:
                    new_posts.append(post_dict)
                    existing_ids.add(post_id)
            
            # Add new posts to database
            for post_dict in new_posts:
                db_manager.add_post(post_dict)
            
            print(f"✅ Threads: {len(new_posts)} new bookmarks added")
            return len(new_posts)
        else:
            print("📭 No Threads bookmarks found")
            return 0
            
    except Exception as e:
        print(f"❌ Threads collection error: {e}")
        return 0
    finally:
        try:
            if hasattr(extractor, 'close'):
                await extractor.close()
        except:
            pass

async def main():
    """Main collection function"""
    print("📥 Starting MULTI-PLATFORM bookmark collection...")
    print("=" * 60)
    
    # Initialize systems
    db_manager = DatabaseManager(db_path=str(project_root / "data" / "prismind.db"))
    
    # Get existing post IDs to avoid duplicates
    existing_posts = db_manager.get_all_posts(include_deleted=False)
    existing_ids = set(existing_posts['post_id'].tolist()) if not existing_posts.empty else set()
    
    print(f"📊 Database contains {len(existing_ids)} existing posts")
    print(f"🔍 Existing post IDs: {list(existing_ids)[:5]}...")  # Show first 5 IDs
    
    total_new = 0
    
    # Collect from all platforms
    try:
        # Twitter
        twitter_count = await collect_twitter_bookmarks(db_manager, existing_ids)
        total_new += twitter_count
        
        # Reddit  
        reddit_count = collect_reddit_bookmarks(db_manager, existing_ids)
        total_new += reddit_count
        
        # Threads
        threads_count = await collect_threads_bookmarks(db_manager, existing_ids)
        total_new += threads_count
        
    except KeyboardInterrupt:
        print("\n⚠️ Collection interrupted by user")
        return
    
    print("\n" + "=" * 60)
    print("🎉 MULTI-PLATFORM collection completed!")
    print(f"📊 Total new bookmarks collected: {total_new}")
    if total_new > 0:
        print("💡 Tip: Use the dashboard's AI enhancement to analyze new content")
    else:
        print("💡 No new bookmarks found - you're up to date!")

if __name__ == "__main__":
    asyncio.run(main())