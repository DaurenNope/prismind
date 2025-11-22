#!/usr/bin/env python3
"""
Verify that Show More button expansion is working properly.
Compare collected content with actual tweet URL.
"""
import asyncio
from playwright.async_api import async_playwright

async def get_actual_tweet_content(tweet_url: str) -> str:
    """Get the actual full content from a tweet URL manually"""
    print(f"🔍 Fetching actual content from: {tweet_url}")
    print("="*70)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        try:
            # Navigate to tweet
            await page.goto(tweet_url, timeout=30000)
            await page.wait_for_timeout(3000)
            
            # Find and click Show more if present
            try:
                show_more = await page.query_selector('[data-testid="tweet-text-show-more-button"]')
                if show_more:
                    print("🔽 Found 'Show more' button, clicking...")
                    await show_more.click()
                    await page.wait_for_timeout(2000)
                    print("✅ Clicked")
            except:
                print("ℹ️  No 'Show more' button (tweet not truncated)")
            
            # Get full content
            tweet_text_element = await page.query_selector('[data-testid="tweetText"]')
            if tweet_text_element:
                content = await tweet_text_element.inner_text()
                print(f"\n📝 Actual tweet content ({len(content)} chars):")
                print("-"*70)
                print(content)
                print("-"*70)
                return content
            else:
                print("❌ Could not find tweet text")
                return ""
                
        finally:
            await browser.close()

async def main():
    # Test with one of the long tweets we collected
    test_url = "https://x.com/Innerdevcrypto/status/1975318135176564758"
    
    actual_content = await get_actual_tweet_content(test_url)
    
    # Compare with what we have in DB
    from src.supabase_manager import SupabaseManager
    sm = SupabaseManager()
    
    result = sm.client.table('posts').select('content').eq('url', test_url).execute()
    
    if result.data:
        db_content = result.data[0].get('content', '')
        
        print(f"\n📊 Comparison:")
        print("="*70)
        print(f"Actual length:     {len(actual_content)} chars")
        print(f"Database length:   {len(db_content)} chars")
        print(f"Match:             {actual_content == db_content}")
        
        if actual_content == db_content:
            print("\n✅ PERFECT MATCH - Show more is working correctly!")
        else:
            print(f"\n⚠️  Content differs!")
            print(f"Missing: {len(actual_content) - len(db_content)} chars")
            
            # Show difference
            if len(db_content) < len(actual_content):
                print(f"\nMissing content:")
                print(actual_content[len(db_content):])
    else:
        print("\n❌ Tweet not found in database")

if __name__ == '__main__':
    asyncio.run(main())
