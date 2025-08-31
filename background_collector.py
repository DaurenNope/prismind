#!/usr/bin/env python3
"""
Background Collection System
Runs collection continuously in the background
"""

import os
import time
import asyncio
import threading
from datetime import datetime, timedelta
from dotenv import load_dotenv
import sqlite3
import json
from scrape_state_manager import state_manager

# Load environment variables
load_dotenv()

class BackgroundCollector:
    def __init__(self):
        self.running = False
        self.collection_interval = int(os.getenv('COLLECTION_INTERVAL_MINUTES', '60'))  # Default 1 hour
        self.max_posts_per_run = int(os.getenv('MAX_POSTS_PER_RUN', '100'))  # Max posts per collection run
        self.db_path = "prismind.db"
        
    def start(self):
        """Start background collection"""
        self.running = True
        print(f"🚀 Starting background collection...")
        print(f"📊 Collection interval: {self.collection_interval} minutes")
        print(f"📊 Max posts per run: {self.max_posts_per_run}")
        
        # Start collection loop
        while self.running:
            try:
                            print(f"\n🔄 Starting collection run at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Show current stats
                stats = state_manager.get_scraping_stats()
                print(f"📊 Current stats: {stats['total_posts']} total posts tracked")
                
                # Run collection
                self.run_collection()
                
                # Wait for next interval
                print(f"⏰ Next collection in {self.collection_interval} minutes...")
                time.sleep(self.collection_interval * 60)
                
            except KeyboardInterrupt:
                print("\n🛑 Background collection stopped by user")
                self.running = False
                break
            except Exception as e:
                print(f"❌ Collection error: {e}")
                print("⏰ Retrying in 5 minutes...")
                time.sleep(300)
    
    def run_collection(self):
        """Run a single collection cycle"""
        try:
            # Import collection functions
            from collect_multi_platform import collect_twitter_bookmarks, collect_reddit_bookmarks, collect_threads_bookmarks
            
            # Get existing posts to avoid duplicates
            existing_ids = self.get_existing_post_ids()
            existing_urls = self.get_existing_urls()
            
            # Run collections with limits
            total_new_posts = 0
            
            # Twitter collection
            try:
                print("🐦 Collecting Twitter posts...")
                twitter_count = asyncio.run(collect_twitter_bookmarks_with_limit(existing_ids, existing_urls))
                total_new_posts += twitter_count
                print(f"✅ Twitter: {twitter_count} new posts")
            except Exception as e:
                print(f"❌ Twitter collection failed: {e}")
            
            # Reddit collection
            try:
                print("🤖 Collecting Reddit posts...")
                reddit_count = collect_reddit_bookmarks_with_limit(existing_ids, existing_urls)
                total_new_posts += reddit_count
                print(f"✅ Reddit: {reddit_count} new posts")
            except Exception as e:
                print(f"❌ Reddit collection failed: {e}")
            
            # Threads collection - SKIPPED (authentication not working)
            print("🧵 Skipping Threads collection (authentication not configured)")
            print("   💡 To enable Threads, fix authentication in config/threads_cookies_qronoya.json")
            
            print(f"🎉 Collection complete: {total_new_posts} total new posts")
            
        except Exception as e:
            print(f"❌ Collection run failed: {e}")
    
    def get_existing_post_ids(self):
        """Get existing post IDs from database"""
        try:
            # Try Supabase first
            from scripts.supabase_manager import SupabaseManager
            supabase = SupabaseManager()
            existing_posts = supabase.get_all_posts()
            if not existing_posts.empty:
                existing_ids = set(existing_posts['post_id'].tolist()) if 'post_id' in existing_posts.columns else set()
                print(f"📊 Found {len(existing_ids)} existing posts in Supabase")
                return existing_ids
        except Exception as e:
            print(f"⚠️ Could not get existing posts from Supabase: {e}")
        
        # Fallback to SQLite
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT post_id FROM posts WHERE post_id IS NOT NULL")
            existing_ids = {row[0] for row in cursor.fetchall()}
            conn.close()
            print(f"📊 Found {len(existing_ids)} existing posts in SQLite")
            return existing_ids
        except Exception as e:
            print(f"⚠️ Could not get existing posts from SQLite: {e}")
            return set()
    
    def get_existing_urls(self):
        """Get existing URLs from database"""
        try:
            # Try Supabase first
            from scripts.supabase_manager import SupabaseManager
            supabase = SupabaseManager()
            existing_posts = supabase.get_all_posts()
            if not existing_posts.empty and 'url' in existing_posts.columns:
                existing_urls = set(existing_posts['url'].dropna().tolist())
                print(f"🔗 Found {len(existing_urls)} existing URLs in Supabase")
                return existing_urls
        except Exception as e:
            print(f"⚠️ Could not get existing URLs from Supabase: {e}")
        
        # Fallback to SQLite
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT url FROM posts WHERE url IS NOT NULL")
            existing_urls = {row[0] for row in cursor.fetchall()}
            conn.close()
            print(f"🔗 Found {len(existing_urls)} existing URLs in SQLite")
            return existing_urls
        except Exception as e:
            print(f"⚠️ Could not get existing URLs from SQLite: {e}")
            return set()
    
    def stop(self):
        """Stop background collection"""
        self.running = False
        print("🛑 Background collection stopped")

async def collect_twitter_bookmarks_with_limit(existing_ids, existing_urls=None):
    """Collect Twitter bookmarks with limit"""
    from collect_multi_platform import collect_twitter_bookmarks
    
    # Override the limit for background collection
    original_limit = os.getenv('TWITTER_LIMIT', '200')
    os.environ['TWITTER_LIMIT'] = str(min(int(original_limit), 50))  # Max 50 for background
    
    return await collect_twitter_bookmarks(None, existing_ids, existing_urls)

def collect_reddit_bookmarks_with_limit(existing_ids, existing_urls=None):
    """Collect Reddit bookmarks with limit"""
    from collect_multi_platform import collect_reddit_bookmarks
    
    # Override the limit for background collection
    original_limit = os.getenv('REDDIT_LIMIT', '100')
    os.environ['REDDIT_LIMIT'] = str(min(int(original_limit), 25))  # Max 25 for background
    
    return collect_reddit_bookmarks(None, existing_ids, existing_urls)

async def collect_threads_bookmarks_with_limit(existing_ids):
    """Collect Threads bookmarks with limit"""
    from collect_multi_platform import collect_threads_bookmarks
    
    # Override the limit for background collection
    original_limit = os.getenv('THREADS_LIMIT', '100')
    os.environ['THREADS_LIMIT'] = str(min(int(original_limit), 25))  # Max 25 for background
    
    return await collect_threads_bookmarks(None, existing_ids)

def start_background_collection():
    """Start background collection in a separate thread"""
    collector = BackgroundCollector()
    thread = threading.Thread(target=collector.start, daemon=True)
    thread.start()
    return collector

if __name__ == "__main__":
    print("🚀 PrisMind Background Collector")
    print("=" * 40)
    
    # Environment variables for configuration
    print("📋 Configuration:")
    print(f"   Collection interval: {os.getenv('COLLECTION_INTERVAL_MINUTES', '60')} minutes")
    print(f"   Max posts per run: {os.getenv('MAX_POSTS_PER_RUN', '100')}")
    print(f"   Twitter limit: {os.getenv('TWITTER_LIMIT', '200')}")
    print(f"   Reddit limit: {os.getenv('REDDIT_LIMIT', '100')}")
    print(f"   Threads: DISABLED (authentication issues)")
    
    # Start background collection
    collector = BackgroundCollector()
    
    try:
        collector.start()
    except KeyboardInterrupt:
        collector.stop()
