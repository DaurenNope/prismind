"""
Threads.com Forum Platform Client
For the actual threads.com discussion forum platform
"""

import asyncio
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

import aiohttp
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class ThreadsComPost:
    """Represents a threads.com forum post"""

    id: str
    title: str
    content: str
    author_username: str
    author_display_name: str
    url: str
    created_at: datetime
    replies_count: int
    mentions_beyondlines: bool = False


class ThreadsComClient:
    """Client for threads.com forum platform"""

    def __init__(self):
        self.base_url = "https://threads.com"
        self.session: Optional[aiohttp.ClientSession] = None
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
        }

    async def initialize(self):
        """Initialize HTTP session"""
        self.session = aiohttp.ClientSession(
            headers=self.headers, timeout=aiohttp.ClientTimeout(total=30)
        )
        logger.info("Threads.com client initialized")

    async def close(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()

    async def search_beyondlines_mentions(
        self, query: str = "beyondlines"
    ) -> List[ThreadsComPost]:
        """Search for posts mentioning beyondlines on threads.com"""
        if not self.session:
            raise RuntimeError("Client not initialized")

        try:
            # Search for beyondlines mentions
            search_url = f"{self.base_url}/search?q={query}"

            logger.info(f"Searching threads.com for: {query}")

            async with self.session.get(search_url) as response:
                if response.status != 200:
                    logger.error(f"Search failed: {response.status}")
                    return []

                html = await response.text()

            # Parse search results
            posts = self._parse_threads_com_posts(html, query)

            logger.info(f"Found {len(posts)} posts mentioning beyondlines")
            return posts

        except Exception as e:
            logger.error(f"Error searching threads.com: {e}")
            return []

    def _parse_threads_com_posts(
        self, html: str, search_query: str
    ) -> List[ThreadsComPost]:
        """Parse posts from threads.com HTML"""
        posts = []

        try:
            soup = BeautifulSoup(html, "html.parser")

            # Look for post/thread elements
            # Note: This would need adjustment based on actual threads.com HTML structure
            post_elements = soup.find_all(
                "div", class_=re.compile(r"post|thread|discussion")
            )

            for element in post_elements:
                try:
                    # Extract title
                    title_element = (
                        element.find("h2") or element.find("h3") or element.find("a")
                    )
                    title = title_element.get_text(strip=True) if title_element else ""

                    # Extract content
                    content_element = element.find(
                        "div", class_=re.compile(r"content|body|text")
                    )
                    content = (
                        content_element.get_text(strip=True) if content_element else ""
                    )

                    # Extract author
                    author_element = element.find(
                        "span", class_=re.compile(r"author|user")
                    )
                    author = (
                        author_element.get_text(strip=True)
                        if author_element
                        else "Unknown"
                    )

                    # Extract URL
                    link_element = element.find("a")
                    url = link_element.get("href") if link_element else ""
                    if url and not url.startswith("http"):
                        url = self.base_url + url

                    # Check if mentions beyondlines
                    text_to_check = (title + " " + content).lower()
                    mentions_beyondlines = "beyondlines" in text_to_check

                    if mentions_beyondlines:
                        post = ThreadsComPost(
                            id=url.split("/")[-1]
                            if url
                            else str(hash(title + content)),
                            title=title,
                            content=content,
                            author_username=author.lower().replace(" ", ""),
                            author_display_name=author,
                            url=url,
                            created_at=datetime.now(timezone.utc),
                            replies_count=0,
                            mentions_beyondlines=True,
                        )
                        posts.append(post)

                except Exception as e:
                    logger.debug(f"Error parsing post element: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error parsing HTML: {e}")

        return posts

    async def create_reply(self, post_id: str, content: str) -> bool:
        """Create a reply to a threads.com post"""
        # This would require login/authentication to threads.com
        # For now, return simulation
        logger.info(f"Would reply to threads.com post {post_id}: {content[:100]}...")
        return True


async def test_threads_com_client():
    """Test the threads.com client"""
    logger.info("🧵 Testing Threads.com Forum Platform...")
    logger.info("Note: This is threads.com (forum), NOT Instagram Threads")

    try:
        client = ThreadsComClient()
        await client.initialize()

        # Search for beyondlines mentions
        posts = await client.search_beyondlines_mentions("beyondlines")

        if posts:
            logger.info(f"✅ Found {len(posts)} posts mentioning beyondlines:")
            for i, post in enumerate(posts[:5], 1):
                logger.info(f"\n--- Post {i} ---")
                logger.info(f"   Title: {post.title}")
                logger.info(f"   Author: {post.author_display_name}")
                logger.info(f"   URL: {post.url}")
                logger.info(f"   Content: {post.content[:100]}...")
        else:
            logger.warning("⚠️  No posts found mentioning beyondlines on threads.com")
            logger.info(
                "   This might be normal - threads.com might have limited beyondlines discussion"
            )

        await client.close()
        return len(posts) > 0

    except Exception as e:
        logger.error(f"❌ Threads.com test failed: {e}")
        return False


if __name__ == "__main__":
    asyncio.run(test_threads_com_client())
