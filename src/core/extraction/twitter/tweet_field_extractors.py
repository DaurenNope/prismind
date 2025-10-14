"""
Tweet Field Extractors for PrisMind
Handles extraction of individual tweet fields
"""

import re
from datetime import datetime, timezone
from typing import Dict, List, Optional

from playwright.async_api import ElementHandle


class TweetFieldExtractors:
    """Handles extraction of individual tweet fields"""
    
    def __init__(self):
        pass
    
    async def extract_content(self, tweet_element: ElementHandle) -> str:
        """Extract tweet content text"""
        try:
            # Try different selectors for tweet content
            content_selectors = [
                '[data-testid="tweetText"]',
                '[data-testid="tweet"] [lang]',
                'div[data-testid="tweetText"]',
                'span[lang]'
            ]
            
            for selector in content_selectors:
                content_element = await tweet_element.query_selector(selector)
                if content_element:
                    content = await content_element.inner_text()
                    if content.strip():
                        return content.strip()
            
            return ""
        except Exception as e:
            print(f"⚠️ Error extracting content: {e}")
            return ""
    
    async def extract_author(self, tweet_element: ElementHandle) -> str:
        """Extract tweet author name"""
        try:
            author_selectors = [
                '[data-testid="User-Name"] span',
                '[data-testid="User-Names"] span',
                'a[role="link"] span'
            ]
            
            for selector in author_selectors:
                author_element = await tweet_element.query_selector(selector)
                if author_element:
                    author = await author_element.inner_text()
                    if author.strip() and not author.startswith('@'):
                        return author.strip()
            
            return "Unknown"
        except Exception as e:
            print(f"⚠️ Error extracting author: {e}")
            return "Unknown"
    
    async def extract_author_handle(self, tweet_element: ElementHandle) -> str:
        """Extract tweet author handle"""
        try:
            handle_selectors = [
                '[data-testid="User-Name"] a[href*="/"]',
                '[data-testid="User-Names"] a[href*="/"]',
                'a[href*="/"][role="link"]'
            ]
            
            for selector in handle_selectors:
                handle_element = await tweet_element.query_selector(selector)
                if handle_element:
                    href = await handle_element.get_attribute('href')
                    if href and '/' in href:
                        handle = href.split('/')[-1]
                        if handle and not handle.startswith('@'):
                            return f"@{handle}"
            
            return "@unknown"
        except Exception as e:
            print(f"⚠️ Error extracting author handle: {e}")
            return "@unknown"
    
    async def extract_timestamp(self, tweet_element: ElementHandle) -> datetime:
        """Extract tweet timestamp"""
        try:
            time_selectors = [
                'time',
                '[data-testid="Time"]',
                'a[href*="/status/"] time'
            ]
            
            for selector in time_selectors:
                time_element = await tweet_element.query_selector(selector)
                if time_element:
                    datetime_attr = await time_element.get_attribute('datetime')
                    if datetime_attr:
                        try:
                            return datetime.fromisoformat(datetime_attr.replace('Z', '+00:00'))
                        except:
                            pass
            
            return datetime.now(timezone.utc)
        except Exception as e:
            print(f"⚠️ Error extracting timestamp: {e}")
            return datetime.now(timezone.utc)
    
    async def extract_url(self, tweet_element: ElementHandle) -> str:
        """Extract tweet URL"""
        try:
            url_selectors = [
                'a[href*="/status/"]',
                '[data-testid="Time"]',
                'time'
            ]
            
            for selector in url_selectors:
                url_element = await tweet_element.query_selector(selector)
                if url_element:
                    href = await url_element.get_attribute('href')
                    if href and '/status/' in href:
                        if href.startswith('/'):
                            return f"https://x.com{href}"
                        return href
            
            return ""
        except Exception as e:
            print(f"⚠️ Error extracting URL: {e}")
            return ""
    
    async def extract_post_id(self, tweet_element: ElementHandle) -> str:
        """Extract tweet ID"""
        try:
            url = await self.extract_url(tweet_element)
            if url and '/status/' in url:
                return url.split('/status/')[-1].split('?')[0]
            return ""
        except Exception as e:
            print(f"⚠️ Error extracting post ID: {e}")
            return ""
    
    async def extract_media_urls(self, tweet_element: ElementHandle) -> List[str]:
        """Extract media URLs from tweet"""
        media_urls = []
        try:
            # Extract images
            img_elements = await tweet_element.query_selector_all('img[src*="media"]')
            for img in img_elements:
                src = await img.get_attribute('src')
                if src and 'media' in src:
                    media_urls.append(src)
            
            # Extract videos
            video_elements = await tweet_element.query_selector_all('video')
            for video in video_elements:
                src = await video.get_attribute('src')
                if src:
                    media_urls.append(src)
            
            return media_urls
        except Exception as e:
            print(f"⚠️ Error extracting media URLs: {e}")
            return []
    
    async def determine_post_type(self, tweet_element: ElementHandle, content: str) -> str:
        """Determine the type of post (tweet, retweet, reply, etc.)"""
        try:
            # Check for retweet indicators
            retweet_indicators = await tweet_element.query_selector_all('[data-testid="socialContext"]')
            for indicator in retweet_indicators:
                text = await indicator.inner_text()
                if 'retweeted' in text.lower():
                    return 'retweet'
            
            # Check for reply indicators
            if content.startswith('@') or 'Replying to' in content:
                return 'reply'
            
            # Check for quote tweet
            quoted_tweet = await tweet_element.query_selector('[data-testid="quoteTweet"]')
            if quoted_tweet:
                return 'quote_tweet'
            
            return 'tweet'
        except:
            return 'tweet'





