"""
Twitter API v2 Client with Rate Limiting

Uses official Twitter API v2 for posting tweets, with intelligent rate limiting
inspired by elizaOS's RequestQueue pattern.

Key features:
- Official API authentication (OAuth 1.0a)
- Request queue with exponential backoff
- Random delays to avoid rate limits
- Automatic retry on rate limit errors
"""

import asyncio
import logging
import random
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import tweepy
from tweepy import API, OAuth1UserHandler

logger = logging.getLogger(__name__)


@dataclass
class TwitterAPIConfig:
    """Twitter API v2 credentials"""

    api_key: str
    api_secret: str
    access_token: str
    access_token_secret: str
    bearer_token: Optional[str] = None  # Optional, for v2 endpoints


class RequestQueue:
    """
    Request queue with exponential backoff and random delays.

    Inspired by elizaOS's RequestQueue implementation.
    """

    def __init__(self):
        self.queue: List[callable] = []
        self.processing = False

    async def add(self, request: callable) -> Any:
        """
        Add a request to the queue and process it.

        Args:
            request: Async function that makes the API call

        Returns:
            Result from the request
        """
        result_future = asyncio.Future()

        async def queued_request():
            try:
                result = await request()
                result_future.set_result(result)
            except Exception as e:
                logger.error(f"Error: {e}")
                result_future.set_exception(e)

        self.queue.append(queued_request)
        await self._process_queue()

        return await result_future

    async def _process_queue(self):
        """Process queued requests with rate limiting"""
        if self.processing or len(self.queue) == 0:
            return

        self.processing = True

        while len(self.queue) > 0:
            request = self.queue.pop(0)

            try:
                await request()
            except tweepy.TooManyRequests as e:
                # Rate limit hit - exponential backoff
                retry_count = len(self.queue)
                logger.warning(
                    f"Rate limit hit, backing off (queue: {retry_count} requests)"
                )
                self.queue.insert(0, request)  # Put it back at front
                await self._exponential_backoff(retry_count)
                continue
            except Exception as e:
                logger.error(f"Request failed: {e}")
                # Don't retry on other errors
                continue

            # Random delay between requests (1.5-3.5 seconds)
            await self._random_delay()

        self.processing = False

    async def _exponential_backoff(self, retry_count: int):
        """Exponential backoff: 2^retry_count seconds"""
        delay = (2**retry_count) * 1000  # milliseconds
        logger.info(f"Exponential backoff: waiting {delay}ms")
        await asyncio.sleep(delay / 1000)

    async def _random_delay(self):
        """Random delay between 1.5-3.5 seconds"""
        delay = random.uniform(1.5, 3.5)
        await asyncio.sleep(delay)


class TwitterAPIClient:
    """
    Twitter API v2 client with rate limiting.

    Uses official Twitter API for posting, with intelligent queue management.
    """

    def __init__(self, config: TwitterAPIConfig):
        """
        Initialize Twitter API client.

        Args:
            config: Twitter API credentials
        """
        self.config = config
        self.request_queue = RequestQueue()

        # Initialize Tweepy OAuth handler
        self.auth = OAuth1UserHandler(
            config.api_key,
            config.api_secret,
            config.access_token,
            config.access_token_secret,
        )

        # Initialize Tweepy API client
        self.api = API(
            self.auth,
            wait_on_rate_limit=True,  # Auto-wait on rate limits
            wait_on_rate_limit_notify=True,
        )

        # For v2 endpoints, we'd use tweepy.Client if needed
        # For now, using v1.1 API which is more stable

        logger.info("Twitter API client initialized")

    async def post_tweet(
        self,
        text: str,
        in_reply_to_id: Optional[str] = None,
        media_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Post a tweet using Twitter API.

        Args:
            text: Tweet text (max 280 chars)
            in_reply_to_id: Optional tweet ID to reply to
            media_ids: Optional list of media IDs to attach

        Returns:
            Dict with tweet data including ID and URL
        """
        if len(text) > 280:
            raise ValueError("Tweet text exceeds 280 characters")

        async def _post():
            try:
                # Use Tweepy API to post
                # Note: Tweepy v4+ has better v2 support, but v1.1 is more stable
                result = self.api.update_status(
                    status=text,
                    in_reply_to_status_id=in_reply_to_id,
                    media_ids=media_ids,
                )

                # Extract tweet data
                tweet_id = result.id_str
                username = result.user.screen_name
                tweet_url = f"https://twitter.com/{username}/status/{tweet_id}"

                logger.info(f"✅ Posted tweet: {tweet_url}")

                return {
                    "ok": True,
                    "tweet_id": tweet_id,
                    "url": tweet_url,
                    "text": text,
                    "created_at": result.created_at.isoformat()
                    if hasattr(result, "created_at")
                    else None,
                }

            except tweepy.TooManyRequests as e:
                logger.warning(f"Rate limit hit: {e}")
                raise  # Let queue handle retry
            except tweepy.TweepyException as e:
                logger.error(f"Twitter API error: {e}")
                raise

        return await self.request_queue.add(_post)

    async def verify_credentials(self) -> bool:
        """Verify API credentials are valid"""

        async def _verify():
            try:
                user = self.api.verify_credentials()
                logger.info(f"✅ Authenticated as @{user.screen_name}")
                return True
            except Exception as e:
                logger.error(f"❌ Authentication failed: {e}")
                return False

        return await self.request_queue.add(_verify)

    def get_rate_limit_status(self) -> Dict[str, Any]:
        """Get current rate limit status"""
        try:
            limits = self.api.get_rate_limit_status()
            return {
                "statuses": limits["resources"]["statuses"]["/statuses/update"],
                "remaining": limits["resources"]["statuses"]["/statuses/update"][
                    "remaining"
                ],
            }
        except Exception as e:
            logger.error(f"Error getting rate limits: {e}")
            return {}


# Factory function for easy initialization
def create_twitter_client(
    api_key: str, api_secret: str, access_token: str, access_token_secret: str
) -> TwitterAPIClient:
    """
    Create a Twitter API client from credentials.

    Args:
        api_key: Twitter API key
        api_secret: Twitter API secret
        access_token: Twitter access token
        access_token_secret: Twitter access token secret

    Returns:
        Initialized TwitterAPIClient
    """
    config = TwitterAPIConfig(
        api_key=api_key,
        api_secret=api_secret,
        access_token=access_token,
        access_token_secret=access_token_secret,
    )
    return TwitterAPIClient(config)
