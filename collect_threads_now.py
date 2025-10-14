#!/usr/bin/env python3
"""
Quick Threads collection using working cookie method
"""

import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright
from parsel import Selector

sys.path.insert(0, str(Path(__file__).parent))

from src.services.new_database_manager import NewDatabaseManager
from src.core.extraction.threads_extractor import ThreadsExtractor

async def collect_threads_simple():
    """Collect Threads posts using simplified approach"""
    
    print("=" * 70)
    print("QUICK THREADS COLLECTION")
    print("=" * 70)
    
    db = NewDatabaseManager()
    extractor = ThreadsExtractor()
    
    # Get existing
    existing = db.get_all_posts()
    existing_urls = {p.get('url') for p in existing if p.get('url')}
    print(f"\n1. Existing posts in DB: {len(existing_urls)}")
    
    # Use working cookie method
    cookie_file = Path("config/threads_cookies.json")
    print(f"2. Using cookie file: {cookie_file}")
    
    async with async_playwright() as p:
        print("3. Launching browser...")
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            storage_state=str(cookie_file),
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        page = await context.new_page()
        
        print("4. Navigating to saved posts...")
        await page.goto("https://www.threads.com/saved", wait_until='domcontentloaded')
        await asyncio.sleep(3)
        
        if 'login' in page.url:
            print("❌ Not logged in!")
            await browser.close()
            return 0
        
        print("✅ Logged in! Collecting post URLs...")
        
        # Scroll and collect URLs
        post_urls = set()
        for i in range(5):
            content = await page.content()
            selector = Selector(content)
            links = selector.css('a[href*="/post/"]::attr(href)').getall()
            
            for link in links:
                if not link.startswith('http'):
                    link = f"https://www.threads.net{link}"
                post_urls.add(link)
            
            print(f"   Scroll {i+1}: {len(post_urls)} URLs found")
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await asyncio.sleep(2)
        
        await browser.close()
        
        print(f"\n5. Found {len(post_urls)} total post URLs")
        
        # Filter out existing
        new_urls = [url for url in post_urls if url not in existing_urls]
        print(f"   New posts to scrape: {len(new_urls)}")
        
        if not new_urls:
            print("\n✅ No new posts to collect")
            return 0
        
        # Scrape posts
        print(f"\n6. Scraping {len(new_urls)} posts...")
        posts = await extractor.scrape_posts_from_urls_async(list(new_urls)[:10])  # Limit to 10 for now
        
        print(f"   Scraped {len(posts)} posts successfully")
        
        # Save to database with language detection
        def detect_language(text: str) -> str:
            if not text:
                return 'en'
            russian_chars = sum(1 for c in text if '\u0400' <= c <= '\u04FF')
            total_chars = len(text.replace(' ', ''))
            if total_chars > 0 and russian_chars / total_chars > 0.3:
                return 'ru'
            return 'en'
        
        saved_count = 0
        print(f"\n7. Saving to database...")
        
        for post in posts:
            try:
                content = post.content or ""
                
                post_dict = {
                    "post_id": post.post_id,
                    "title": "",  # Threads doesn't have titles
                    "content": content,
                    "url": post.url,
                    "platform": "threads",
                    "author": post.author,
                    "author_handle": getattr(post, 'author_handle', ''),
                    "language": detect_language(content),
                    "created_at": post.created_at or datetime.now().isoformat(),
                    "media_urls": json.dumps(post.media_urls) if post.media_urls else "[]",
                }
                
                if db.add_post(post_dict):
                    lang = post_dict['language']
                    print(f"   ✅ [{lang}] {post.author}: {content[:50]}...")
                    saved_count += 1
                else:
                    print(f"   ⚠️  Failed to save: {post.url}")
                    
            except Exception as e:
                print(f"   ❌ Error saving post: {e}")
        
        print(f"\n✅ Saved {saved_count} posts to database")
        
        # Verify
        threads_posts = db.get_posts_by_platform('threads')
        print(f"\n📊 Total Threads posts in DB: {len(threads_posts)}")
        
        return saved_count

if __name__ == "__main__":
    print("\n" + "=" * 70)
    count = asyncio.run(collect_threads_simple())
    print("\n" + "=" * 70)
    print(f"🎉 Collection complete! Saved {count} new Threads posts")
    print("=" * 70 + "\n")
