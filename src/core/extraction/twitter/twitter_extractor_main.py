"""
Main Twitter extractor orchestrator for Playwright-based extraction
"""

import asyncio
import random
from datetime import datetime, timezone
from typing import Dict, List, Optional

from playwright.async_api import Browser, Page, async_playwright

from src.core.extraction.social_extractor_base import SocialExtractorBase, SocialPost
from .twitter_auth import TwitterAuth
from .twitter_data_extractor import TwitterDataExtractor


class TwitterExtractorMain(SocialExtractorBase):
    """Main Twitter extractor orchestrator"""
    
    def __init__(self, username: str, password: str = None, headless: bool = True, cookie_file: str = None):
        super().__init__()
        self.username = username
        self.password = password
        self.headless = headless
        self.cookie_file = cookie_file or f"config/twitter_cookies_{username}.json"
        
        # Initialize components
        self.auth = TwitterAuth(username, password, cookie_file)
        self.data_extractor = TwitterDataExtractor()
        
        # Browser components
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context = None
        self.page: Optional[Page] = None
        self.is_authenticated = False
    
    async def authenticate(self, max_retries: int = 3) -> bool:
        """Authenticate with Twitter"""
        try:
            # Initialize browser
            if not self.playwright:
                self.playwright = await async_playwright().start()
            
            if not self.browser:
                self.browser = await self.playwright.chromium.launch(
                    headless=self.headless,
                    args=['--no-sandbox', '--disable-dev-shm-usage']
                )
            
            if not self.context:
                self.context = await self.browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                )
            
            if not self.page:
                self.page = await self.context.new_page()
            
            # Authenticate
            success = await self.auth.authenticate(self.page, max_retries)
            if success:
                self.is_authenticated = True
                print("✅ Twitter authentication successful")
            else:
                print("❌ Twitter authentication failed")
            
            return success
            
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return False
    
    async def get_saved_posts(self, limit: int = 50, skip_cached_ids: set = None) -> List[SocialPost]:
        """Get bookmarked tweets from Twitter with improved scrolling and thread handling"""
        if not self.is_authenticated:
            if not await self.authenticate():
                return []
        
        posts = []
        processed_tweet_ids = set(skip_cached_ids) if skip_cached_ids else set()
        print(f"🚫 Will skip {len(processed_tweet_ids)} already cached tweets")
        
        try:
            # Navigate to bookmarks
            await self.page.goto('https://x.com/i/bookmarks', wait_until='domcontentloaded', timeout=15000)
            await self.page.wait_for_timeout(3000)
            
            # Check if bookmarks page loaded
            try:
                await self.page.wait_for_selector('[data-testid="primaryColumn"]', timeout=5000)
            except:
                print("❌ Could not access bookmarks page - check if account has bookmarks enabled")
                return []
            
            print(f"📥 Starting to extract Twitter bookmarks (target: {limit})...")
            
            # Improved scrolling mechanism
            scroll_attempts = 0
            max_scroll_attempts = 50
            no_new_content_count = 0
            last_tweet_count = 0
            
            while len(posts) < limit and scroll_attempts < max_scroll_attempts:
                try:
                    # Get all tweet articles on the page with fresh query
                    tweet_elements = await self.page.query_selector_all('article[data-testid="tweet"]')
                    current_tweet_count = len(tweet_elements)
                    
                    print(f"📊 Scroll attempt {scroll_attempts + 1}: Found {current_tweet_count} tweet elements on page")
                    
                    # Process all tweets but check for duplicates properly
                    new_tweets_found = 0
                    processed_this_scroll = set()
                    
                    for i, tweet_element in enumerate(tweet_elements):
                        if len(posts) >= limit:
                            break
                            
                        try:
                            # Validate element is still attached to DOM
                            try:
                                await tweet_element.bounding_box()
                            except:
                                print(f"⚠️ Tweet element {i} no longer valid, skipping")
                                continue
                            
                            # Extract tweet data with thread handling
                            tweet_data = await self._extract_tweet_data_with_threads(tweet_element)
                            if tweet_data:
                                # Check if we already processed this tweet
                                if tweet_data.post_id in processed_tweet_ids:
                                    print(f"⏭️ Skipped already processed tweet: {tweet_data.post_id}")
                                    continue
                                
                                # Check if we processed this tweet in this scroll
                                if tweet_data.post_id in processed_this_scroll:
                                    print(f"⏭️ Skipped duplicate in this scroll: {tweet_data.post_id}")
                                    continue
                                
                                # Double-check for duplicates by content/URL
                                is_duplicate = False
                                for existing_post in posts:
                                    if (existing_post.post_id == tweet_data.post_id or 
                                        existing_post.url == tweet_data.url or
                                        (existing_post.content == tweet_data.content and len(tweet_data.content) > 10)):
                                        is_duplicate = True
                                        break
                                
                                if not is_duplicate:
                                    posts.append(tweet_data)
                                    processed_this_scroll.add(tweet_data.post_id)
                                    new_tweets_found += 1
                                    print(f"✅ Added tweet {len(posts)}: {tweet_data.post_id}")
                                else:
                                    print(f"⏭️ Skipped duplicate tweet: {tweet_data.post_id}")
                            
                        except Exception as e:
                            print(f"⚠️ Error processing tweet {i}: {e}")
                            continue
                    
                    print(f"📈 Found {new_tweets_found} new tweets in this scroll")
                    
                    # Check if we found new content
                    if new_tweets_found == 0:
                        no_new_content_count += 1
                        if no_new_content_count >= 3:
                            print("🛑 No new content found in 3 consecutive scrolls, stopping")
                            break
                    else:
                        no_new_content_count = 0
                    
                    # Check if we have enough tweets
                    if len(posts) >= limit:
                        print(f"🎯 Reached target limit of {limit} tweets")
                        break
                    
                    # Scroll down for more tweets
                    await self.page.evaluate('window.scrollBy(0, 1000)')
                    await asyncio.sleep(random.uniform(2, 4))
                    scroll_attempts += 1
                    
                    # Check if we're stuck (same number of tweets)
                    if current_tweet_count == last_tweet_count:
                        print("🛑 No new tweets loaded, stopping scroll")
                        break
                    last_tweet_count = current_tweet_count
                    
                except Exception as e:
                    print(f"⚠️ Error in scroll attempt {scroll_attempts + 1}: {e}")
                    scroll_attempts += 1
                    continue
            
            print(f"✅ Collected {len(posts)} Twitter bookmarks")
            return posts
            
        except Exception as e:
            print(f"❌ Error in get_saved_posts: {e}")
            import traceback
            traceback.print_exc()
        
        return posts
    
    async def get_liked_posts(self, limit: int = 50) -> List[SocialPost]:
        """Get liked tweets from Twitter - DISABLED: We only collect bookmarks"""
        print("⚠️ get_liked_posts is disabled - we only collect bookmarks")
        return []
    
    async def _extract_tweet_data_with_threads(self, tweet_element, is_saved: bool = True) -> Optional[SocialPost]:
        """Extract tweet data with improved thread handling - avoids navigation to prevent DOM issues"""
        try:
            # First extract the main tweet
            main_tweet = await self.data_extractor._extract_tweet_data(tweet_element, is_saved)
            if not main_tweet:
                return None
            
            # Check for thread indicators without navigation
            has_thread_indicator = False
            try:
                # Look for "Show this thread" link or thread indicators
                thread_elements = await tweet_element.query_selector_all('a[role="link"]')
                for element in thread_elements:
                    try:
                        text = await element.inner_text()
                        if any(indicator in text.lower() for indicator in ["show this thread", "thread", "show more"]):
                            has_thread_indicator = True
                            break
                    except Exception as e:
                        print(f"⚠️ Error reading thread element: {e}")
                        continue
                
                # Also check for reply indicators (tweets that look like they continue)
                if not has_thread_indicator:
                    content = main_tweet.content.strip()
                    if (content.endswith('...') or 
                        content.endswith('/1') or 
                        content.endswith('1/') or
                        'thread' in content.lower() or
                        content.count('\n') > 3):  # Long tweets often indicate threads
                        has_thread_indicator = True
                        
            except Exception as e:
                print(f"⚠️ Error checking thread indicators: {e}")
            
            # Extract full thread if detected and enabled
            if has_thread_indicator:
                main_tweet.post_type = 'thread'
                
                # Check if thread extraction is enabled (default: True)
                import os
                enable_threads = os.getenv('TWITTER_EXTRACT_THREADS', 'true').lower() == 'true'
                
                if enable_threads and main_tweet.url and main_tweet.author:
                    print(f"🧵 Thread detected - attempting to extract full thread")
                    try:
                        # Import ThreadHandler
                        from src.core.extraction.handlers.thread_handler import ThreadHandler
                        
                        # Extract full thread
                        thread_handler = ThreadHandler()
                        thread_posts = await thread_handler.extract_full_thread(
                            self.page, 
                            main_tweet.url, 
                            main_tweet.author
                        )
                        
                        if thread_posts and len(thread_posts) > 1:
                            # Combine thread content into main tweet
                            thread_content = []
                            for i, post in enumerate(thread_posts, 1):
                                thread_content.append(f"[{i}/{len(thread_posts)}] {post.content}")
                            
                            main_tweet.content = "\n\n".join(thread_content)
                            main_tweet.metadata = main_tweet.metadata or {}
                            main_tweet.metadata['thread_length'] = len(thread_posts)
                            main_tweet.metadata['is_full_thread'] = True
                            print(f"✅ Extracted full thread with {len(thread_posts)} posts")
                        else:
                            print(f"⚠️ Thread extraction returned {len(thread_posts) if thread_posts else 0} posts - using main tweet only")
                            
                    except Exception as thread_error:
                        print(f"⚠️ Thread extraction failed: {thread_error}")
                        print(f"   Continuing with main tweet only")
                        # Continue with main tweet - don't fail the entire extraction
                else:
                    if not enable_threads:
                        print("🧵 Thread detected but extraction disabled via TWITTER_EXTRACT_THREADS=false")
                    else:
                        print("🧵 Thread detected but missing URL or author - skipping extraction")
            
            return main_tweet
            
        except Exception as e:
            print(f"❌ Error extracting tweet with threads: {e}")
            return await self.data_extractor._extract_tweet_data(tweet_element, is_saved)
    
    async def extract_single_tweet(self, tweet_url: str) -> Optional[SocialPost]:
        """Extract a single tweet from its URL"""
        try:
            # Navigate to the tweet URL
            await self.page.goto(tweet_url, wait_until='domcontentloaded', timeout=15000)
            await self.page.wait_for_timeout(3000)
            
            # Find the tweet element
            tweet_element = await self.page.query_selector('article[data-testid="tweet"]')
            if tweet_element:
                return await self.data_extractor._extract_tweet_data(tweet_element, is_saved=False)
            else:
                print("❌ Could not find tweet element")
                return None
                
        except Exception as e:
            print(f"❌ Error extracting single tweet: {e}")
            return None
    
    async def close(self):
        """Clean up browser resources"""
        try:
            if self.page and not self.page.is_closed():
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except Exception as e:
            print(f"⚠️ Error during cleanup: {e}")
    
    def __del__(self):
        """Destructor - note that async cleanup should be called explicitly"""
        # Note: Cannot run async cleanup in destructor
        # Cleanup should be called explicitly via close() method
        pass





