#!/usr/bin/env python3
"""
Rescrape Single Post - Re-extract a specific post with fresh data
"""

import sys
import os
import asyncio
from pathlib import Path

# Setup paths
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

from core.extraction.twitter_extractor_playwright import TwitterExtractorPlaywright
from scripts.database_manager import DatabaseManager

async def rescrape_post(post_url: str):
    """Rescrape a specific post by URL"""
    print(f"🔄 Rescaping post: {post_url}")
    
    # Initialize systems
    db_manager = DatabaseManager(db_path=str(project_root / "data" / "prismind.db"))
    
    # Try to get username from environment or config
    twitter_username = os.getenv('TWITTER_USERNAME')
    if not twitter_username:
        # Try to find existing cookie files to get username
        config_dir = project_root / "config"
        if config_dir.exists():
            cookie_files = list(config_dir.glob("twitter_cookies_*.json"))
            if cookie_files:
                # Extract username from cookie filename
                cookie_file = cookie_files[0]
                twitter_username = cookie_file.stem.replace("twitter_cookies_", "")
                print(f"🔍 Found existing session for: {twitter_username}")
    
    if not twitter_username:
        print("❌ No Twitter username found. Please set TWITTER_USERNAME environment variable.")
        return False
    
    try:
        # Initialize extractor
        extractor = TwitterExtractorPlaywright(
            username=twitter_username,
            headless=True,
            cookie_file=str(project_root / "config" / f"twitter_cookies_{twitter_username}.json")
        )
        
        print("🔍 Extracting fresh data from URL...")
        
        # Initialize the browser and navigate to the specific URL
        await extractor.authenticate()
        await extractor.page.goto(post_url, wait_until='networkidle')
        
        # Wait for tweet to load
        await extractor.page.wait_for_timeout(3000)
        
        # Find the main tweet element
        tweet_elements = await extractor.page.query_selector_all('[data-testid="tweet"]')
        
        fresh_post = None
        if tweet_elements:
            # Extract data from the first tweet (main tweet)
            fresh_post = await extractor._extract_tweet_data(tweet_elements[0], is_saved=True)
        
        if fresh_post:
            # Update the database with fresh data
            post_dict = fresh_post.__dict__ if hasattr(fresh_post, '__dict__') else fresh_post
            db_manager.add_post(post_dict)  # This will update existing post due to INSERT OR REPLACE
            
            print(f"✅ Successfully updated post: {post_dict.get('post_id', 'unknown')}")
            print(f"   📝 Title: {post_dict.get('smart_title', post_dict.get('content', '')[:50])}")
            print(f"   👤 Author: {post_dict.get('author', 'Unknown')}")
            return True
        else:
            print("❌ No data returned from URL")
            return False
    
    except Exception as e:
        print(f"❌ Error during rescrape: {str(e)}")
        return False
    
    finally:
        try:
            if 'extractor' in locals():
                extractor.close()
        except:
            pass

async def main():
    if len(sys.argv) != 2:
        print("Usage: python rescrape_single_post.py <post_url>")
        sys.exit(1)
    
    post_url = sys.argv[1]
    success = await rescrape_post(post_url)
    
    if success:
        print("🎉 Post rescrape completed!")
        sys.exit(0)
    else:
        print("❌ Post rescrape failed!")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())