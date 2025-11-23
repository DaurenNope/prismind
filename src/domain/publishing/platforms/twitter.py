"""
Twitter Posting Service using Tweepy (Twitter API v2)
Simplified version for beyondlines publishing system

Now includes rate limiting inspired by elizaOS's RequestQueue pattern.
"""

import time
from datetime import datetime
from typing import Dict, List, Optional

import tweepy

from src.utils.secrets_manager import get_secrets_manager

secrets = get_secrets_manager()


class TwitterPoster:
    """Post tweets and threads to Twitter using API v2 with rate limiting."""

    def __init__(self):
        """Initialize Twitter client with rate limiting."""
        self.api_key = secrets.get("TWITTER_API_KEY")
        self.api_secret = secrets.get("TWITTER_API_SECRET")
        self.access_token = secrets.get("TWITTER_ACCESS_TOKEN")
        self.access_secret = secrets.get("TWITTER_ACCESS_TOKEN_SECRET")

        if not all(
            [self.api_key, self.api_secret, self.access_token, self.access_secret]
        ):
            raise ValueError("Twitter credentials missing in .env")

        # Initialize Tweepy client with auto rate limiting
        self.client = tweepy.Client(
            consumer_key=self.api_key,
            consumer_secret=self.api_secret,
            access_token=self.access_token,
            access_token_secret=self.access_secret,
            wait_on_rate_limit=True,  # Auto-wait on rate limits
        )

        # Get authenticated user
        try:
            self.me = self.client.get_me().data
            self.username = self.me.username
        except Exception as e:
            logger.error(f"Error: {e}")
            self.me = None
            self.username = "Unknown"

    def post_tweet(self, content: str) -> Dict:
        """
        Post a single tweet.

        Returns:
            Dict with success, tweet_id, url, error keys
        """
        try:
            # Validate length
            if len(content) > 280:
                return {
                    "success": False,
                    "error": f"Tweet too long: {len(content)} chars (max 280)",
                }

            # Post
            response = self.client.create_tweet(text=content)
            tweet_id = response.data["id"]

            return {
                "success": True,
                "tweet_id": str(tweet_id),
                "url": f"https://twitter.com/{self.username}/status/{tweet_id}",
                "posted_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error: {e}")
            return {"success": False, "error": str(e)}

    def post_thread(self, tweets: List[str], delay_seconds: int = 3) -> Dict:
        """
        Post a thread of tweets.

        Args:
            tweets: List of tweet texts
            delay_seconds: Delay between tweets

        Returns:
            Dict with success, thread_url, tweets info
        """
        posted_tweets = []
        previous_id = None

        try:
            for i, content in enumerate(tweets, 1):
                # Validate
                if len(content) > 280:
                    return {
                        "success": False,
                        "error": f"Tweet {i} too long: {len(content)} chars (max 280)",
                        "posted_tweets": posted_tweets,
                    }

                # Post as reply to previous tweet
                if previous_id:
                    response = self.client.create_tweet(
                        text=content, in_reply_to_tweet_id=previous_id
                    )
                else:
                    # First tweet
                    response = self.client.create_tweet(text=content)

                tweet_id = response.data["id"]
                previous_id = tweet_id

                posted_tweets.append(
                    {
                        "tweet_id": str(tweet_id),
                        "url": f"https://twitter.com/{self.username}/status/{tweet_id}",
                        "position": i,
                    }
                )

                # Delay between tweets (except last one)
                if i < len(tweets):
                    time.sleep(delay_seconds)

            # Get first tweet URL (thread URL)
            thread_url = posted_tweets[0]["url"] if posted_tweets else None

            return {
                "success": True,
                "thread_url": thread_url,
                "tweet_count": len(posted_tweets),
                "tweets": posted_tweets,
                "posted_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error: {e}")
            return {
                "success": False,
                "error": str(e),
                "posted_tweets": posted_tweets,
                "failed_at": len(posted_tweets) + 1,
            }


def post_to_twitter_direct(content: str) -> Dict:
    """
    Post to Twitter using direct API.

    Returns:
        Dict with 'success', 'tweet_id', 'url', 'error' keys
    """
    try:
        poster = TwitterPoster()
        result = poster.post_tweet(content)

        # Normalize response format
        if result.get("success"):
            return {
                "success": True,
                "tweet_id": result.get("tweet_id"),
                "url": result.get("url"),
                "error": None,
            }
        else:
            return {"success": False, "error": result.get("error", "Unknown error")}

    except Exception as e:
        logger.error(f"Error: {e}")
        return {
            "success": False,
            "error": f"TwitterPoster initialization failed: {str(e)}",
        }
