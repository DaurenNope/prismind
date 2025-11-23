"""
Twitter API Daily Rate Limiter

Tracks daily tweet count to prevent exceeding Free Tier limit of 17 tweets/day.
"""

import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class TwitterRateLimiter:
    """
    Tracks daily Twitter posting limits.

    Free Tier: 17 tweets per 24 hours
    Basic Tier: 100 tweets per 24 hours
    Pro Tier: 10,000 tweets per 24 hours (per app)
    """

    def __init__(self, tier: str = "free"):
        """
        Initialize rate limiter.

        Args:
            tier: API tier - "free", "basic", or "pro"
        """
        self.tier = tier.lower()
        self.limits = {
            "free": 17,  # 17 tweets per 24 hours
            "basic": 100,  # 100 tweets per 24 hours
            "pro": 10000,  # 10,000 tweets per 24 hours (per app)
        }
        self.daily_limit = self.limits.get(self.tier, 17)

        # State file location
        self.state_file = Path(
            os.getenv("TWITTER_RATE_LIMIT_STATE", ".twitter_rate_limit_state.json")
        )
        self._load_state()

    def _load_state(self):
        """Load state from file"""
        self.today = datetime.now().date()
        self.tweets_today = 0
        self.last_reset = None

        if self.state_file.exists():
            try:
                with open(self.state_file, "r") as f:
                    state = json.load(f)
                    saved_date = datetime.fromisoformat(
                        state.get("date", datetime.now().isoformat())
                    ).date()

                    if saved_date == self.today:
                        # Same day - use saved count
                        self.tweets_today = state.get("count", 0)
                        self.last_reset = datetime.fromisoformat(
                            state.get("last_reset", datetime.now().isoformat())
                        )
                    else:
                        # New day - reset
                        self.tweets_today = 0
                        self.last_reset = datetime.now()
                        self._save_state()
            except Exception as e:
                logger.warning(f"Failed to load Twitter rate limit state: {e}")
                self.tweets_today = 0
                self.last_reset = datetime.now()
        else:
            self.last_reset = datetime.now()
            self._save_state()

    def _save_state(self):
        """Save state to file"""
        try:
            with open(self.state_file, "w") as f:
                json.dump(
                    {
                        "date": self.today.isoformat(),
                        "count": self.tweets_today,
                        "last_reset": self.last_reset.isoformat(),
                        "tier": self.tier,
                        "limit": self.daily_limit,
                    },
                    f,
                    indent=2,
                )
        except Exception as e:
            logger.warning(f"Failed to save Twitter rate limit state: {e}")

    def can_post(self) -> tuple[bool, Optional[str]]:
        """
        Check if we can post a tweet.

        Returns:
            (can_post: bool, reason: Optional[str])
        """
        # Check if we've exceeded daily limit
        if self.tweets_today >= self.daily_limit:
            hours_until_reset = (
                24 - (datetime.now() - self.last_reset).total_seconds() / 3600
            )
            return (
                False,
                f"Daily limit reached ({self.tweets_today}/{self.daily_limit}). Resets in {hours_until_reset:.1f} hours.",
            )

        return True, None

    def record_post(self):
        """Record that a tweet was posted"""
        self.tweets_today += 1
        self._save_state()
        logger.info(
            f"📊 Twitter posts today: {self.tweets_today}/{self.daily_limit} ({self.tier} tier)"
        )

    def get_status(self) -> dict:
        """Get current rate limit status"""
        hours_until_reset = (
            24 - (datetime.now() - self.last_reset).total_seconds() / 3600
        )
        if hours_until_reset < 0:
            hours_until_reset = 0

        return {
            "tier": self.tier,
            "limit": self.daily_limit,
            "used": self.tweets_today,
            "remaining": max(0, self.daily_limit - self.tweets_today),
            "hours_until_reset": hours_until_reset,
            "can_post": self.tweets_today < self.daily_limit,
        }


# Global instance
_limiter: Optional[TwitterRateLimiter] = None


def get_twitter_limiter() -> TwitterRateLimiter:
    """Get or create global Twitter rate limiter"""
    global _limiter
    if _limiter is None:
        tier = os.getenv("TWITTER_API_TIER", "free").lower()
        _limiter = TwitterRateLimiter(tier=tier)
    return _limiter
