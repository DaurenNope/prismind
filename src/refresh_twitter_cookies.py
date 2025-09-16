#!/usr/bin/env python3
"""
Script to refresh Twitter cookies using environment credentials.
This will authenticate with Twitter and save fresh cookies for the collector.
"""

import asyncio
import os

from src.core.extraction.twitter_extractor_playwright import TwitterExtractorPlaywright


async def refresh_cookies():
    """Refresh Twitter cookies using environment credentials"""
    
    # Get credentials from environment
    username = os.getenv('TWITTER_USERNAME')
    password = os.getenv('TWITTER_PASSWORD')
    
    if not username:
        print("❌ TWITTER_USERNAME not found in environment")
        return False
    
    if not password:
        print("❌ TWITTER_PASSWORD not found in environment")
        return False
    
    print(f"🔄 Refreshing cookies for Twitter user: {username}")
    
    # Create extractor with headless=False to see the process
    extractor = TwitterExtractorPlaywright(
        username=username,
        password=password,
        headless=False,  # Set to True if you want it to run in background
        cookie_file=f"config/twitter_cookies_{username}.json"
    )
    
    try:
        # Authenticate and save fresh cookies
        success = await extractor.authenticate()
        
        if success:
            print("✅ Successfully refreshed Twitter cookies!")
            print(f"🍪 Cookies saved to: config/twitter_cookies_{username}.json")
            return True
        else:
            print("❌ Failed to authenticate and refresh cookies")
            return False
            
    except Exception as e:
        print(f"❌ Error refreshing cookies: {e}")
        return False
    finally:
        # Clean up
        if extractor.browser:
            await extractor.browser.close()
        if extractor.playwright:
            await extractor.playwright.stop()

if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Run the cookie refresh
    success = asyncio.run(refresh_cookies())
    
    if success:
        print("\n🎉 Cookie refresh completed successfully!")
        print("You can now run the collector to fetch new bookmarks.")
    else:
        print("\n💥 Cookie refresh failed. Check your credentials and try again.")
