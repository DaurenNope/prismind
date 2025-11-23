#!/usr/bin/env python3
"""
Fix truncated tweets by re-fetching them with proper Show more expansion
"""
import asyncio
from playwright.async_api import async_playwright
from src.infrastructure.database.manager import SupabaseManager
import time

async def get_full_content(url: str) -> str:
    """Get full tweet content with Show more expansion"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        try:
            await page.goto(url, timeout=30000)
            await page.wait_for_timeout(3000)
            
            # Try multiple selectors for Show more
            show_more_selectors = [
                '[data-testid="tweet-text-show-more-button"]',
                'div[role="button"]:has-text("Show more")',
                'span:has-text("Show more")',
            ]
            
            for selector in show_more_selectors:
                try:
                    button = await page.query_selector(selector)
                    if button:
                        print(f"   🔽 Clicking Show more...")
                        await button.click()
                        await page.wait_for_timeout(2000)
                        break
                except:
                    continue
            
            # Get content
            tweet_text = await page.query_selector('[data-testid="tweetText"]')
            if tweet_text:
                content = await tweet_text.inner_text()
                return content
            
            return ""
            
        finally:
            await browser.close()

async def main():
    sm = SupabaseManager()
    
    # Get truncated tweets
    result = sm.client.table('posts').select('post_id, author, content, url').eq('platform', 'twitter').execute()
    
    truncated = []
    for post in result.data:
        content = post.get('content', '').strip()
        length = len(content)
        
        # Real truncation: 200-500 chars, ends abruptly
        if 200 < length < 500:
            last_char = content[-1] if content else ''
            if last_char not in '.!?\")' and not content.endswith('...') and not content.endswith('…'):
                truncated.append(post)
    
    print(f'🔧 Found {len(truncated)} truncated tweets to fix')
    print('='*70)
    
    # Ask for confirmation
    response = input(f'\\nFix all {len(truncated)} tweets? (y/n): ')
    if response.lower() != 'y':
        print('Cancelled')
        return
    
    fixed = 0
    failed = 0
    
    for i, post in enumerate(truncated, 1):
        url = post.get('url')
        author = post.get('author', 'Unknown')
        old_content = post.get('content', '')
        
        print(f'\\n[{i}/{len(truncated)}] {author}')
        print(f'   Old: {len(old_content)} chars')
        print(f'   URL: {url}')
        
        try:
            new_content = await get_full_content(url)
            
            if new_content and len(new_content) > len(old_content):
                print(f'   ✅ New: {len(new_content)} chars (+{len(new_content) - len(old_content)})')
                
                # Update in Supabase
                sm.client.table('posts').update({
                    'content': new_content
                }).eq('url', url).execute()
                
                fixed += 1
            else:
                print(f'   ⚠️  No improvement (still {len(new_content)} chars)')
                failed += 1
            
            # Rate limiting
            time.sleep(2)
            
        except Exception as e:
            print(f'   ❌ Error: {e}')
            failed += 1
    
    print(f'\\n📊 Results:')
    print(f'   ✅ Fixed: {fixed}')
    print(f'   ❌ Failed: {failed}')
    print(f'   Total: {len(truncated)}')

if __name__ == '__main__':
    asyncio.run(main())
