import logging

logger = logging.getLogger(__name__)
"""Main Twitter extractor - clean and modular"""

import json
from pathlib import Path
from typing import List, Optional, Set

from ..social_extractor_base import SocialExtractorBase, SocialPost
from ..twitter_cookies import TwitterCookieStore
from .auth import TwitterAuth
from .bookmarks import TwitterBookmarks


def load_collection_config():
    """Load collection configuration"""
    config_path = Path("config/collection.json")
    if config_path.exists():
        with open(config_path, "r") as f:
            return json.load(f)
    return {"twitter": {"extract_threads": False}}


class TwitterExtractorPlaywright(SocialExtractorBase):
    """Extract saved tweets and bookmarks from Twitter using Playwright"""

    def __init__(
        self,
        username: str,
        password: str = None,
        headless: bool = False,
        cookie_file: str = None,
    ):
        super().__init__()
        self.username = username
        self.password = password
        self.headless = headless
        self.cookie_file = cookie_file or f"cookies/twitter_cookies_{username}.json"
        self._cookie_store = TwitterCookieStore(self.cookie_file)

        # Load config
        config = load_collection_config()
        self.extract_threads = config.get("twitter", {}).get("extract_threads", False)

        # Auth and bookmarks handlers
        self.auth: Optional[TwitterAuth] = None
        self.bookmarks: Optional[TwitterBookmarks] = None

    async def authenticate(self, max_retries: int = 3) -> bool:
        """Authenticate with Twitter"""
        self.auth = TwitterAuth(
            username=self.username,
            password=self.password,
            cookie_store=self._cookie_store,
            headless=self.headless,
        )

        success = await self.auth.authenticate(max_retries)
        if success:
            # Initialize bookmarks handler with authenticated page
            self.bookmarks = TwitterBookmarks(self.auth.page)

        return success

    async def get_saved_posts(
        self,
        limit: int = 50,
        skip_cached_ids: Optional[Set[str]] = None,
        stop_at_post_id: Optional[str] = None,
    ) -> List[SocialPost]:
        """Get bookmarked tweets - SIMPLE: scroll until we see last saved tweet"""
        if not self.auth or not self.auth.is_authenticated:
            if not await self.authenticate():
                return []

        if not self.auth.page or self.auth.page.is_closed():
            logger.warning(
                "⚠️ Page was closed - please keep the browser window open during collection"
            )
            return []

        if not self.bookmarks:
            self.bookmarks = TwitterBookmarks(self.auth.page)

        return await self.bookmarks.get_bookmarks(
            limit=limit, skip_ids=skip_cached_ids, stop_at_post_id=stop_at_post_id
        )

    async def get_liked_posts(self, limit: int = 50) -> List[SocialPost]:
        """Get liked posts - not implemented yet"""
        logger.warning("⚠️ Liked posts extraction not implemented")
        return []

    async def close(self):
        """Clean up resources"""
        if self.auth:
            await self.auth.close()
