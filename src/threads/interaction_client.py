"""
Threads Interaction Client - Browser Automation Reply Guy
Detects and replies to @beyondlines mentions on Instagram Threads
"""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from playwright.async_api import BrowserContext, Page, async_playwright

from ..core.analysis.ai_service_manager import ai_service_manager
from ..utils.exceptions import TwitterInteractionError, TwitterScrapingError

logger = logging.getLogger(__name__)


class ThreadsInteractionType(Enum):
    """Types of Threads interactions"""

    MENTION = "mention"
    REPLY = "reply"
    QUOTE = "quote"


@dataclass
class ThreadsInteraction:
    """Represents a Threads interaction"""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    post_id: str = ""
    author_username: str = ""
    author_display_name: str = ""
    content: str = ""
    interaction_type: ThreadsInteractionType = ThreadsInteractionType.MENTION
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    reply_content: Optional[str] = None
    url: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class ThreadsInteractionClient:
    """
    Browser-based Threads interaction client for Reply Guy functionality
    Detects and replies to @beyondlines mentions on Threads
    """

    def __init__(self, cookies_file: Optional[str] = None):
        self.browser = None
        self.context = None
        self.page = None
        self.cookies_file = cookies_file or "cookies/threads_cookies.json"
        self.last_check: Optional[datetime] = None
        self.processed_posts: set = set()

        # Stealth settings
        self.stealth_settings = {
            "viewport": {"width": 1280, "height": 720},
            "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "locale": "en-US",
            "timezone_id": "America/New_York",
        }

    async def initialize(self):
        """Initialize browser and login to Threads"""
        try:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(
                headless=False,  # Show browser for debugging
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-infobars",
                    "--window-position=0,0",
                    "--window-size=1280,720",
                ],
            )

            self.context = await self.browser.new_context(
                **self.stealth_settings,
                permissions=["geolocation", "notifications"],
                extra_http_headers={
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                },
            )

            # Add stealth script
            await self.context.add_init_script(
                """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });

                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });

                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en'],
                });
            """
            )

            self.page = await self.context.new_page()

            # Try to load existing cookies
            await self._load_cookies()

            # Go to Threads
            await self.page.goto("https://www.threads.net", wait_until="networkidle")
            await asyncio.sleep(2)

            # Check if we're logged in
            if await self._is_logged_in():
                logger.info("Already logged into Threads")
            else:
                logger.warning("Not logged into Threads - manual login required")
                await self._manual_login()

            logger.info("Threads client initialized")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Threads client: {e}")
            raise TwitterScrapingError(f"Threads initialization failed: {e}")

    async def _is_logged_in(self) -> bool:
        """Check if we're logged into Threads"""
        try:
            # Look for login indicators
            await self.page.wait_for_timeout(3000)

            # Check for login buttons (means not logged in)
            login_buttons = await self.page.query_selector_all(
                'button:has-text("Log in"), a:has-text("Log in")'
            )
            if login_buttons:
                return False

            # Check for logged-in indicators
            compose_button = await self.page.query_selector(
                '[aria-label*="Create"], [data-testid*="compose"]'
            )
            profile_link = await self.page.query_selector('a[href*="/@"]')

            return bool(compose_button or profile_link)

        except Exception as e:
            logger.debug(f"Error checking login status: {e}")
            return False

    async def _manual_login(self):
        """Guide user through manual login"""
        logger.info("\n🔐 MANUAL LOGIN REQUIRED FOR THREADS")
        logger.info("=" * 50)
        logger.info("1. A browser window will open")
        logger.info("2. Please log into Threads manually")
        logger.info("3. The script will continue automatically")
        logger.info("=" * 50)

        input("Press Enter after logging into Threads...")

        # Save cookies after login
        await self._save_cookies()

    async def _load_cookies(self):
        """Load cookies from file"""
        try:
            import json

            with open(self.cookies_file, "r") as f:
                cookies = json.load(f)
                await self.context.add_cookies(cookies)
                logger.info(f"Loaded {len(cookies)} cookies")
        except FileNotFoundError:
            logger.info("No cookies file found - will need to log in")
        except Exception as e:
            logger.warning(f"Failed to load cookies: {e}")

    async def _save_cookies(self):
        """Save cookies to file"""
        try:
            import json

            cookies = await self.context.cookies()
            os.makedirs(os.path.dirname(self.cookies_file), exist_ok=True)
            with open(self.cookies_file, "w") as f:
                json.dump(cookies, f)
                logger.info(f"Saved {len(cookies)} cookies")
        except Exception as e:
            logger.warning(f"Failed to save cookies: {e}")

    async def search_mentions(self, max_results: int = 20) -> List[ThreadsInteraction]:
        """
        Search for @beyondlines mentions on Threads
        Uses browser automation to find mentions
        """
        if not self.page:
            raise TwitterScrapingError("Client not initialized")

        try:
            logger.info("Searching for @beyondlines mentions on Threads")

            # Go to search page or use search functionality
            search_url = "https://www.threads.net/search?q=%40beyondlines"
            await self.page.goto(search_url, wait_until="networkidle")
            await asyncio.sleep(3)

            # Look for posts that mention @beyondlines
            mentions = []

            # Find post elements
            post_selectors = [
                'div[data-pressable-container="true"]',
                'article[role="article"]',
                'div[class*="post"]',
                'div[class*="thread"]',
            ]

            posts = []
            for selector in post_selectors:
                elements = await self.page.query_selector_all(selector)
                if elements:
                    posts = elements
                    break

            logger.info(f"Found {len(posts)} potential posts")

            for post_element in posts[:max_results]:
                try:
                    mention = await self._extract_mention_from_element(post_element)
                    if mention and mention.post_id not in self.processed_posts:
                        mentions.append(mention)
                        self.processed_posts.add(mention.post_id)
                except Exception as e:
                    logger.debug(f"Error extracting mention from post: {e}")
                    continue

            # Sort by created time (newest first)
            mentions.sort(key=lambda x: x.created_at, reverse=True)

            logger.info(f"Found {len(mentions)} new mentions")
            return mentions

        except Exception as e:
            logger.error(f"Error searching mentions: {e}")
            raise TwitterScrapingError(f"Failed to search Threads mentions: {e}")

    async def _extract_mention_from_element(
        self, post_element
    ) -> Optional[ThreadsInteraction]:
        """Extract mention data from Threads post element"""
        try:
            # Get post text
            text_element = await post_element.query_selector(
                'div[data-slice-uid] span, span[class*="text"]'
            )
            post_text = await text_element.inner_text() if text_element else ""

            # Check if it mentions @beyondlines
            if "@beyondlines" not in post_text.lower():
                return None

            # Get author info
            author_element = await post_element.query_selector('a[href*="/@"] span')
            author_text = (
                await author_element.inner_text() if author_element else "Unknown"
            )

            # Try to extract username from author text
            author_username = (
                author_text.replace("@", "").strip()
                if author_text.startswith("@")
                else author_text
            )

            # Get post URL
            link_element = await post_element.query_selector('a[href*="/@"]')
            post_url = await link_element.get_attribute("href") if link_element else ""

            # Generate post ID from URL (since Threads doesn't expose IDs easily)
            post_id = post_url.split("/")[-1] if post_url else str(uuid.uuid4())

            return ThreadsInteraction(
                post_id=post_id,
                author_username=author_username,
                author_display_name=author_text,
                content=post_text,
                interaction_type=ThreadsInteractionType.MENTION,
                url=f"https://www.threads.net{post_url}" if post_url else "",
                metadata={
                    "extracted_at": datetime.now(timezone.utc).isoformat(),
                    "platform": "threads",
                },
            )

        except Exception as e:
            logger.debug(f"Error extracting mention: {e}")
            return None

    async def generate_reply(self, interaction: ThreadsInteraction) -> str:
        """Generate AI reply for a Threads interaction"""
        try:
            prompt = f"""
            You are @Beyondlines on Instagram Threads. Reply to this mention:

            From: @{interaction.author_username}
            Content: {interaction.content}

            Guidelines:
            - Be conversational and helpful
            - Keep under 500 characters (Threads limit)
            - Add value to the conversation
            - Use 1-2 relevant emojis
            - Don't repeat original content
            - Sound authentic and engaging
            """

            reply = await ai_service_manager.generate_text(
                prompt=prompt,
                max_tokens=200,
                temperature=0.7,
                persona_id="threads_reply_assistant",
            )

            # Clean and format reply
            if not reply.startswith(f"@{interaction.author_username}"):
                reply = f"@{interaction.author_username} {reply}"

            # Ensure Threads character limit
            if len(reply) > 500:
                reply = reply[:497] + "..."

            return reply.strip()

        except Exception as e:
            logger.error(f"Error generating reply: {e}")
            raise TwitterInteractionError(f"Failed to generate reply: {e}")

    async def post_reply(self, interaction: ThreadsInteraction) -> bool:
        """Post reply to Threads post"""
        if not self.page or not interaction.reply_content:
            return False

        try:
            # Navigate to the post
            if interaction.url:
                await self.page.goto(interaction.url, wait_until="networkidle")
                await asyncio.sleep(2)

            # Find and click reply button
            reply_button_selectors = [
                '[aria-label*="Reply"]',
                '[data-testid*="reply"]',
                'button:has-text("Reply")',
                'div[class*="reply"] button',
            ]

            reply_button = None
            for selector in reply_button_selectors:
                try:
                    reply_button = await self.page.wait_for_selector(
                        selector, timeout=5000
                    )
                    if reply_button:
                        break
                except Exception as e:
                    logger.error(f"Error: {e}")
                    continue

            if not reply_button:
                logger.error("Could not find reply button")
                return False

            await reply_button.click()
            await asyncio.sleep(2)

            # Find reply text area and type our reply
            reply_textarea_selectors = [
                'textarea[placeholder*="Reply"]',
                'textarea[aria-label*="Reply"]',
                'div[contenteditable="true"]',
                "textarea",
            ]

            textarea = None
            for selector in reply_textarea_selectors:
                try:
                    textarea = await self.page.wait_for_selector(selector, timeout=5000)
                    if textarea:
                        break
                except Exception as e:
                    logger.error(f"Error: {e}")
                    continue

            if not textarea:
                logger.error("Could not find reply text area")
                return False

            await textarea.clear()
            await textarea.type(interaction.reply_content, delay=50)
            await asyncio.sleep(1)

            # Find and click post button
            post_button_selectors = [
                'button:has-text("Post")',
                'button:has-text("Reply")',
                '[data-testid*="post"]',
                'div[class*="post"] button',
            ]

            post_button = None
            for selector in post_button_selectors:
                try:
                    post_button = await self.page.wait_for_selector(
                        selector, timeout=5000
                    )
                    if post_button and await post_button.is_enabled():
                        break
                except Exception as e:
                    logger.error(f"Error: {e}")
                    continue

            if not post_button:
                logger.error("Could not find post button")
                return False

            await post_button.click()
            await asyncio.sleep(3)  # Wait for post to complete

            logger.info(f"Successfully posted reply to {interaction.url}")
            return True

        except Exception as e:
            logger.error(f"Error posting reply: {e}")
            return False

    async def start_monitoring(self, check_interval: int = 300):
        """Start continuous monitoring for Threads mentions"""
        logger.info(f"Starting Threads monitoring with {check_interval}s interval")

        while True:
            try:
                mentions = await self.search_mentions()

                for mention in mentions:
                    try:
                        # Generate reply
                        reply = await self.generate_reply(mention)
                        mention.reply_content = reply

                        logger.info(
                            f"Generated reply for {mention.author_username}: {reply[:50]}..."
                        )

                        # Post reply
                        success = await self.post_reply(mention)
                        if success:
                            logger.info(
                                f"Successfully replied to {mention.author_username} on Threads"
                            )
                        else:
                            logger.error(
                                f"Failed to reply to {mention.author_username}"
                            )

                        # Delay between posts to avoid rate limiting
                        await asyncio.sleep(30)

                    except Exception as e:
                        logger.error(f"Error processing mention {mention.post_id}: {e}")
                        continue

                # Wait before next check
                await asyncio.sleep(check_interval)

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying

    async def close(self):
        """Close browser and cleanup"""
        try:
            if self.context:
                await self._save_cookies()
            if self.browser:
                await self.browser.close()
            logger.info("Threads client closed")
        except Exception as e:
            logger.error(f"Error closing Threads client: {e}")


# Global client instance
threads_client: Optional[ThreadsInteractionClient] = None


async def get_threads_client() -> ThreadsInteractionClient:
    """Get global Threads client instance"""
    global threads_client
    if not threads_client:
        threads_client = ThreadsInteractionClient()
        await threads_client.initialize()
    return threads_client
