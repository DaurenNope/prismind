from __future__ import annotations
import json
from typing import Dict, List, Optional
import jmespath
from parsel import Selector
from nested_lookup import nested_lookup
from playwright.async_api import async_playwright
from playwright.sync_api import sync_playwright
from datetime import datetime, timezone
import logging
import requests
from pathlib import Path

from .social_extractor_base import SocialExtractorBase, SocialPost

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ThreadsExtractor(SocialExtractorBase):
    """
    Extractor for Threads.net. This extractor uses Playwright to load a thread's
    page and parse a hidden JSON data object to retrieve thread information.
    NOTE: This extractor ONLY supports scraping public posts by URL. It does not
    support fetching saved/bookmarked posts due to authentication complexities.
    """

    def __init__(self):
        super().__init__()
        self.platform_name = "threads"

    async def authenticate(self, username: str, password: str, cookies_path: str = "config/threads_cookies_qronoya.json") -> bool:
        """Authenticates the user by trying cookies first, then falling back to login."""
        try:
            if Path(cookies_path).exists():
                logging.info(f"Attempting authentication with cookies from {cookies_path}")
                if await self._authenticate_with_cookies(cookies_path):
                    return True
            
            logging.info("Cookie authentication failed or cookies not found. Falling back to login.")
            return await self._authenticate_with_login(username, password, cookies_path)
        except Exception as e:
            logging.error(f"Authentication failed: {e}")
            return False

    async def _authenticate_with_cookies(self, cookies_path: str) -> bool:
        """Authenticates using cookies and verifies by checking for a logged-in state."""
        try:
            self.pw = await async_playwright().start()
            self.browser = await self.pw.chromium.launch(headless=False)
            self.context = await self.browser.new_context(storage_state=cookies_path)
            self.page = await self.context.new_page()
            await self.page.goto("https://www.threads.net", wait_until='domcontentloaded')
            
            # More reliable check for login status
            await self.page.wait_for_selector('a[href*="/profile"] svg', timeout=10000)
            logging.info("Successfully authenticated with existing cookies.")
            return True
        except Exception as e:
            logging.error(f"Cookie authentication failed: {e}")
            if hasattr(self, 'browser') and self.browser:
                await self.browser.close()
            if hasattr(self, 'pw') and self.pw:
                await self.pw.stop()
            return False
    
    def _load_json_cookies(self, context, cookies_path: str):
        """Load cookies from JSON file"""
        try:
            with open(cookies_path, 'r') as f:
                cookies_data = json.load(f)
            
            # Convert to Playwright cookie format
            playwright_cookies = []
            for cookie in cookies_data:
                playwright_cookie = {
                    'name': cookie['name'],
                    'value': cookie['value'],
                    'domain': cookie['domain'],
                    'path': cookie['path'],
                    'secure': cookie.get('secure', False),
                    'httpOnly': cookie.get('httpOnly', False)
                }
                
                # Add expiration if present
                if 'expirationDate' in cookie and not cookie.get('session', False):
                    playwright_cookie['expires'] = cookie['expirationDate']
                
                # Add sameSite if present and valid
                if cookie.get('sameSite') and cookie['sameSite'] in ['Strict', 'Lax', 'None']:
                    playwright_cookie['sameSite'] = cookie['sameSite']
                elif cookie.get('sameSite') == 'no_restriction':
                    playwright_cookie['sameSite'] = 'None'
                elif cookie.get('sameSite') == 'lax':
                    playwright_cookie['sameSite'] = 'Lax'
                
                playwright_cookies.append(playwright_cookie)
            
            # Add cookies to context
            context.add_cookies(playwright_cookies)
            logging.info(f"Loaded {len(playwright_cookies)} cookies from JSON")
            
        except Exception as e:
            logging.error(f"Failed to load JSON cookies: {e}")
    
    def _load_raw_cookies(self, context, cookies_path: str):
        """Load raw cookies from file"""
        try:
            with open(cookies_path, 'r') as f:
                cookie_content = f.read().strip()
                
            # Parse cookies string
            cookies = []
            for cookie_pair in cookie_content.split('; '):
                if '=' in cookie_pair:
                    name, value = cookie_pair.split('=', 1)
                    
                    # Add cookies for multiple domains since Threads uses Instagram infrastructure
                    for domain in ['.threads.net', '.instagram.com', '.facebook.com']:
                        cookies.append({
                            'name': name,
                            'value': value,
                            'domain': domain,
                            'path': '/'
                        })
            
            # Add cookies to context
            context.add_cookies(cookies)
            logging.info(f"Loaded {len(cookies)} cookies across multiple domains")
            
        except Exception as e:
            logging.error(f"Failed to load raw cookies: {e}")
    
    def _check_login_status(self, page) -> bool:
        """Check if user is logged in to Threads"""
        try:
            # Look for login indicators
            login_indicators = [
                'a[href="/login"]',
                'button:has-text("Log in")',
                'div:has-text("Log in")'
            ]
            
            for indicator in login_indicators:
                if page.query_selector(indicator):
                    return False
            
            # Look for logged-in indicators
            logged_in_indicators = [
                'nav[role="navigation"]',
                'svg[aria-label="Home"]',
                'a[href*="/profile"]',
                '[data-testid="primaryColumn"]'
            ]
            
            for indicator in logged_in_indicators:
                if page.query_selector(indicator):
                    return True
            
            return False
            
        except Exception as e:
            logging.error(f"Error checking login status: {e}")
            return False
    
    async def _authenticate_with_login(self, username: str, password: str, cookies_path: str) -> bool:
        """Authenticates by logging into Instagram, which shares a session with Threads."""
        try:
            self.pw = await async_playwright().start()
            self.browser = await self.pw.chromium.launch(headless=False)
            self.context = await self.browser.new_context()
            self.page = await self.context.new_page()

            logging.info("Navigating to Instagram login page...")
            await self.page.goto("https://www.instagram.com/accounts/login/", wait_until='domcontentloaded')

            await self.page.wait_for_selector('input[name="username"]', timeout=15000)
            await self.page.fill('input[name="username"]', username)
            await self.page.fill('input[name="password"]', password)
            await self.page.click('button[type="submit"]')

            # Wait for successful login and navigation to the main feed
            await self.page.wait_for_selector('a[href="/direct/inbox/"]', timeout=15000)
            logging.info("Successfully logged into Instagram.")

            # Save the authentication state to the cookies file
            await self.context.storage_state(path=cookies_path)
            logging.info(f"Authentication state saved to {cookies_path}")

            return True
        except Exception as e:
            logging.error(f"Login authentication failed: {e}")
            await self.page.screenshot(path="logs/threads_login_failure.png")
            if hasattr(self, 'browser') and self.browser:
                await self.browser.close()
            if hasattr(self, 'pw') and self.pw:
                await self.pw.stop()
            return False

    async def get_saved_posts(self, username: str, password: str, limit: int = 100, cookies_path: str = "config/threads_cookies_qronoya.json") -> List[SocialPost]:
        """
        Attempts to get saved/bookmarked posts. This is experimental due to Threads authentication challenges.
        """
        logging.warning("Fetching saved posts from Threads is experimental and may not always succeed.")
        if not await self.authenticate(username, password, cookies_path):
            logging.error("Authentication failed, cannot fetch saved posts.")
            return []

        posts = []
        try:
            page = self.page
            bookmarks_url = f"https://www.threads.net/@{username}/saved"
            page.goto(bookmarks_url, wait_until='domcontentloaded', timeout=20000)
            page.wait_for_timeout(5000) # Wait for dynamic content

            post_links = set()
            for _ in range(5): # Scroll a few times to load posts
                selector = Selector(page.content())
                links = selector.css('a[href*="/post/"]::attr(href)').getall()
                for link in links:
                    post_links.add(f"https://www.threads.net{link}")
                page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                page.wait_for_timeout(2000)

            if not post_links:
                logging.warning("No saved post links found. The page might not have loaded correctly or there are no saved posts.")
                return []

            urls_to_scrape = list(post_links)[:limit]
            logging.info(f"Found {len(urls_to_scrape)} saved post URLs to scrape.")
            return self.scrape_posts_from_urls(urls_to_scrape)

        except Exception as e:
            logging.error(f"Failed to get saved posts: {e}")
            return []
        finally:
            if self.browser:
                self.browser.close()

    def scrape_posts_from_urls(self, urls: List[str], max_retries: int = 3) -> List[SocialPost]:
        """
        Scrapes multiple Threads posts from a given list of URLs with retries.
        """
        posts = []
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            context = browser.new_context(viewport={"width": 1920, "height": 1080})
            page = context.new_page()

            for url in urls:
                for attempt in range(max_retries):
                    try:
                        logging.info(f"Scraping thread: {url} (Attempt {attempt + 1}/{max_retries})")
                        post = self._scrape_thread_data(url, page)
                        if post:
                            posts.append(post)
                            break  # Success, move to next URL
                    except Exception as e:
                        logging.error(f"Failed to scrape {url} on attempt {attempt + 1}: {e}")
                        if attempt >= max_retries - 1:
                            logging.error(f"All retries failed for {url}.")
                            try:
                                page.screenshot(path=f"debug_scrape_failed_{url.split('/')[-1]}.png")
                            except Exception as screenshot_error:
                                logging.error(f"Failed to save screenshot: {screenshot_error}")
                        else:
                            time.sleep(2 * (attempt + 1)) # Exponential backoff
            browser.close()
        return posts

    async def get_liked_posts(self, limit: int = 100) -> List[SocialPost]:
        """
        Get liked posts from Threads. Currently not supported.
        """
        raise NotImplementedError("Threads API does not support retrieving liked posts")

    def _parse_thread_data(self, data: Dict) -> Optional[SocialPost]:
        """
        Parses the JSON data for a single thread post and maps it to the SocialPost dataclass.
        """
        result = jmespath.search(
            """{
            text: post.caption.text,
            published_on: post.taken_at,
            id: post.id,
            pk: post.pk,
            code: post.code,
            username: post.user.username,
            author_handle: post.user.username,
            images: post.carousel_media[].image_versions2.candidates[1].url,
            videos: post.video_versions[].url
        }""",
            data,
        )
        if not result or not result.get('id'):
            return None
        
        post_url = f"https://www.threads.net/@{result['username']}/post/{result['code']}"
        created_at_dt = datetime.fromtimestamp(result['published_on'], tz=timezone.utc)
        
        # Engagement data can be nested differently, so we search for it
        like_count = jmespath.search("post.like_count", data) or 0
        reply_count_str = jmespath.search("view_replies_cta_string", data)
        reply_count = 0
        if reply_count_str and isinstance(reply_count_str, str):
            try:
                reply_count = int(reply_count_str.split(" ")[0])
            except (ValueError, IndexError):
                reply_count = 0
        
        media_urls = list(set(result.get("videos") or []))
        if result.get("images"):
             media_urls.extend(result["images"])
        
        return SocialPost(
            platform=self.platform_name,
            post_id=result['id'],
            author=result['username'],
            author_handle=result['author_handle'],
            content=result.get('text', ''),
            created_at=created_at_dt,
            url=post_url,
            post_type='post',
            media_urls=media_urls,
            engagement={
                'likes': like_count,
                'replies': reply_count,
            },
        )

    def _scrape_thread_data(self, url: str, page) -> Optional[SocialPost]:
        """
        Scrapes a single Threads post by URL using real content extraction.
        """
        try:
            # Extract post code from URL for ID
            post_code = url.strip('/').split('/')[-1]
            
            logging.info(f"Scraping Threads post: {post_code}")
            
            # Navigate to the post
            page.goto(url, timeout=30000)
            page.wait_for_timeout(3000)  # Wait for content to load
            
            # Try to extract real content using various selectors
            content = ""
            author = "Unknown Author"
            author_handle = "unknown"
            created_at = datetime.now(timezone.utc)
            engagement = {}
            media_urls = []
            hashtags = []
            mentions = []
            
            # Try different selectors for post content
            content_selectors = [
                '[data-pressable-container="true"] span',
                'article span',
                '[role="article"] span',
                'div[dir="auto"] span',
                'span[dir="auto"]',
                'div[style*="text"] span'
            ]
            
            for selector in content_selectors:
                try:
                    elements = page.query_selector_all(selector)
                    if elements:
                        # Get text from all matching elements
                        texts = []
                        for elem in elements:
                            text = elem.inner_text().strip()
                            if text and len(text) > 10:  # Only meaningful text
                                texts.append(text)
                        
                        if texts:
                            content = " ".join(texts[:3])  # Take first 3 meaningful texts
                            break
                except Exception as e:
                    logging.debug(f"Selector {selector} failed: {e}")
                    continue
            
            # Try to extract author information
            author_selectors = [
                'a[role="link"] span',
                'h2 span',
                'div[dir="ltr"] span',
                'strong'
            ]
            
            for selector in author_selectors:
                try:
                    elem = page.query_selector(selector)
                    if elem:
                        author_text = elem.inner_text().strip()
                        if author_text and not author_text.startswith('@') and len(author_text) < 50:
                            author = author_text
                            break
                except Exception as e:
                    logging.debug(f"Author selector {selector} failed: {e}")
                    continue
            
            # Try to extract author handle
            handle_selectors = [
                'a[href*="@"] span',
                'span:has-text("@")',
                'div:has-text("@") span'
            ]
            
            for selector in handle_selectors:
                try:
                    elem = page.query_selector(selector)
                    if elem:
                        handle_text = elem.inner_text().strip()
                        if handle_text.startswith('@'):
                            author_handle = handle_text[1:]  # Remove @
                            break
                except Exception as e:
                    logging.debug(f"Handle selector {selector} failed: {e}")
                    continue
            
            # Try to extract engagement metrics
            try:
                # Look for like/heart buttons
                like_elements = page.query_selector_all('svg[aria-label*="like"], svg[aria-label*="Like"], button[aria-label*="like"]')
                if like_elements:
                    engagement['likes'] = len(like_elements)
                
                # Look for reply/comment indicators
                reply_elements = page.query_selector_all('svg[aria-label*="reply"], svg[aria-label*="Reply"], button[aria-label*="reply"]')
                if reply_elements:
                    engagement['replies'] = len(reply_elements)
                
                # Look for share/repost indicators
                share_elements = page.query_selector_all('svg[aria-label*="share"], svg[aria-label*="Share"], svg[aria-label*="repost"]')
                if share_elements:
                    engagement['shares'] = len(share_elements)
                    
            except Exception as e:
                logging.debug(f"Failed to extract engagement: {e}")
            
            # Extract hashtags and mentions from content
            if content:
                import re
                hashtags = re.findall(r'#(\w+)', content)
                mentions = re.findall(r'@(\w+)', content)
            
            # If we couldn't extract meaningful content, create a basic placeholder
            if not content or len(content) < 10:
                content = f"Threads post {post_code} - Content extraction in progress"
                logging.warning(f"Could not extract meaningful content from {url}")
            
            # Create the SocialPost object
            post = SocialPost(
                platform=self.platform_name,
                post_id=post_code,
                author=author,
                author_handle=author_handle,
                content=content,
                created_at=created_at,
                url=url,
                post_type='post',
                media_urls=media_urls,
                hashtags=hashtags,
                mentions=mentions,
                engagement=engagement
            )
            
            logging.info(f"Successfully scraped Threads post: {post_code}")
            return post
            
        except Exception as e:
            logging.error(f"Failed to scrape thread {url}: {e}")
            # Return a basic placeholder if scraping fails
            try:
                post_code = url.strip('/').split('/')[-1]
                return SocialPost(
                    platform=self.platform_name,
                    post_id=post_code,
                    author='Threads User',
                    author_handle='threads_user',
                    content=f'Threads post from {url} - Scraping failed',
                    created_at=datetime.now(timezone.utc),
                    url=url,
                    post_type='post',
                    media_urls=[],
                    engagement={}
                )
            except:
                return None

    def get_posts_by_urls(self, urls: list[str]) -> list[SocialPost]:
        # This will be updated later if needed
        raise NotImplementedError("URL-based scraping not supported in this version.")

    def _parse_thread_from_ld_json(self, data: dict) -> Optional[SocialPost]:
        """
        Parses the JSON-LD data from a script tag to extract post details.
        """
        try:
            post_id = data.get("identifier") or data.get("url", "").split("/")[-2]
            url = data.get("url")
            text = data.get("articleBody", "")
            author = data.get("author", {}).get("name", "unknown")
            
            date_str = data.get("datePublished")
            timestamp = datetime.fromisoformat(date_str.replace("Z", "+00:00")) if date_str else datetime.now(timezone.utc)
            
            likes = 0
            for interaction in data.get("interactionStatistic", []):
                if interaction.get("interactionType") == "https://schema.org/LikeAction":
                    likes = interaction.get("userInteractionCount", 0)
                    break

            return SocialPost(
                post_id=str(post_id),
                url=url,
                text=text,
                author=author,
                timestamp=timestamp,
                platform=self.platform_name,
                likes=likes,
            )
        except (KeyError, TypeError, IndexError) as e:
            logging.error(f"Failed to parse thread data from JSON: {e} - Data: {data}")
            return None
