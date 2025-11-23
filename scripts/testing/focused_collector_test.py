#!/usr/bin/env python3
"""
Focused test to show collector functionality
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.domain.collection.extractors.twitter_extractor_playwright import TwitterExtractorPlaywright
from src.domain.collection.extractors.reddit_extractor import RedditExtractor
from src.domain.collection.extractors.threads_extractor import ThreadsExtractor

async def test_twitter_extractor():
    """Test Twitter extractor directly"""
    print("=== Testing Twitter Extractor ===")
    
    import os
    username = os.getenv("TWITTER_USERNAME")
    password = os.getenv("TWITTER_PASSWORD")
    cookie_file = f"config/twitter_cookies_{username}.json"
    
    if not username:
        print("❌ Twitter username not found in environment variables")
        return False
        
    extractor = TwitterExtractorPlaywright(
        username=username,
        password=password,
        cookie_file=cookie_file
    )
    
    try:
        # Test authentication
        print("🔐 Authenticating...")
        auth_success = await extractor.authenticate()
        if not auth_success:
            print("❌ Authentication failed")
            return False
            
        print("✅ Authentication successful")
        
        # Test getting bookmarks
        print("📥 Fetching bookmarks...")
        bookmarks = await extractor.get_saved_posts(limit=5)
        
        print(f"✅ Found {len(bookmarks)} bookmarks")
        
        # Show some details
        for i, bookmark in enumerate(bookmarks[:3]):
            print(f"  Tweet {i+1}: {bookmark.post_id} - {bookmark.author}")
            
        return True
        
    except Exception as e:
        print(f"❌ Twitter extractor failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        try:
            await extractor.close()
        except:
            pass

async def test_reddit_extractor():
    """Test Reddit extractor directly"""
    print("\n=== Testing Reddit Extractor ===")
    
    try:
        extractor = RedditExtractor()
        print("✅ Reddit extractor initialized")
        
        # Test getting saved posts
        print("📥 Fetching saved posts...")
        posts = extractor.get_saved_posts(limit=5)
        
        print(f"✅ Found {len(posts)} saved posts")
        
        # Show some details
        for i, post in enumerate(posts[:3]):
            print(f"  Post {i+1}: {post.post_id} - {post.title[:50]}...")
            
        return True
        
    except Exception as e:
        print(f"❌ Reddit extractor failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_threads_extractor():
    """Test Threads extractor directly"""
    print("\n=== Testing Threads Extractor ===")
    
    try:
        extractor = ThreadsExtractor()
        print("✅ Threads extractor initialized")
        
        # Test getting bookmarks
        print("📥 Fetching bookmarks...")
        bookmarks = extractor.get_bookmarks(limit=5)
        
        print(f"✅ Found {len(bookmarks)} bookmarks")
        
        # Show some details
        for i, bookmark in enumerate(bookmarks[:3]):
            print(f"  Bookmark {i+1}: {bookmark.post_id} - {bookmark.author}")
            
        return True
        
    except Exception as e:
        print(f"❌ Threads extractor failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all tests"""
    print("Testing collectors directly...")
    
    results = []
    results.append(await test_twitter_extractor())
    results.append(await test_reddit_extractor())
    results.append(await test_threads_extractor())
    
    print(f"\n=== SUMMARY ===")
    print(f"Twitter: {'✅ PASS' if results[0] else '❌ FAIL'}")
    print(f"Reddit: {'✅ PASS' if results[1] else '❌ FAIL'}")
    print(f"Threads: {'✅ PASS' if results[2] else '❌ FAIL'}")
    
    return all(results)

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)