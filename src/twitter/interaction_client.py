"""
Twitter Interaction Client for Beyondlines
Ported from elizaOS concepts - handles mentions, replies, and conversation threading
"""

import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import tweepy

from ..core.analysis.ai_service_manager import ai_service_manager
from ..utils.exceptions import RateLimitExceededError, TwitterInteractionError

logger = logging.getLogger(__name__)


class InteractionType(Enum):
    """Types of Twitter interactions"""

    MENTION = "mention"
    REPLY = "reply"
    QUOTE = "quote"
    RETWEET = "retweet"


class InteractionStatus(Enum):
    """Status of interaction processing"""

    PENDING = "pending"
    PROCESSING = "processing"
    APPROVED = "approved"
    REJECTED = "rejected"
    POSTED = "posted"
    FAILED = "failed"


@dataclass
class TwitterInteraction:
    """Represents a Twitter interaction (mention, reply, etc.)"""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tweet_id: str = ""
    author_id: str = ""
    author_username: str = ""
    content: str = ""
    interaction_type: InteractionType = InteractionType.MENTION
    status: InteractionStatus = InteractionStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    processed_at: Optional[datetime] = None
    reply_content: Optional[str] = None
    context_thread: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "tweet_id": self.tweet_id,
            "author_id": self.author_id,
            "author_username": self.author_username,
            "content": self.content,
            "interaction_type": self.interaction_type.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "processed_at": self.processed_at.isoformat()
            if self.processed_at
            else None,
            "reply_content": self.reply_content,
            "context_thread": self.context_thread,
            "metadata": self.metadata,
        }


@dataclass
class ConversationThread:
    """Represents a Twitter conversation thread"""

    root_tweet_id: str
    tweets: List[Dict[str, Any]] = field(default_factory=list)
    participants: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def add_tweet(self, tweet_data: Dict[str, Any]):
        """Add a tweet to the thread"""
        self.tweets.append(tweet_data)
        self.last_updated = datetime.now(timezone.utc)

        # Update participants
        username = tweet_data.get("author_username")
        if username and username not in self.participants:
            self.participants.append(username)


class TwitterInteractionClient:
    """
    Twitter client for handling interactions, mentions, and replies
    Based on elizaOS TwitterInteractionClient concepts
    """

    def __init__(self, api_keys: Dict[str, str]):
        self.api_keys = api_keys
        self.client: Optional[tweepy.Client] = None
        self.rate_limiter = TwitterRateLimiter()
        self.interaction_cache: Dict[str, TwitterInteraction] = {}
        self.thread_cache: Dict[str, ConversationThread] = {}
        self.last_mention_check: Optional[datetime] = None
        self.processing_queue: asyncio.Queue = asyncio.Queue()

    async def initialize(self):
        """Initialize Twitter client"""
        try:
            self.client = tweepy.Client(
                bearer_token=self.api_keys.get("TWITTER_BEARER_TOKEN"),
                consumer_key=self.api_keys.get("TWITTER_API_KEY"),
                consumer_secret=self.api_keys.get("TWITTER_API_SECRET"),
                access_token=self.api_keys.get("TWITTER_ACCESS_TOKEN"),
                access_token_secret=self.api_keys.get("TWITTER_ACCESS_TOKEN_SECRET"),
                wait_on_rate_limit=True,
            )

            # Test authentication
            me = self.client.get_me()
            logger.info(
                f"Twitter Interaction Client initialized for user: @{me.data.username}"
            )

        except Exception as e:
            logger.error(f"Failed to initialize Twitter client: {e}")
            raise TwitterInteractionError(f"Twitter client initialization failed: {e}")

    async def process_mentions(
        self, check_interval: int = 300
    ) -> List[TwitterInteraction]:
        """
        Process recent mentions and create interaction objects
        Based on elizaOS processMentionTweets()
        """
        if not self.client:
            raise TwitterInteractionError("Twitter client not initialized")

        try:
            await self.rate_limiter.wait_for_slot()

            # Get mentions since last check
            since_id = None
            if self.last_mention_check:
                # Convert to Twitter API format
                since_id = str(int(self.last_mention_check.timestamp()))

            # Get recent mentions - use search instead of mentions endpoint
            # The mentions endpoint requires special permissions
            mentions = self.client.search_recent_tweets(
                query="@beyondlines -is:retweet",
                tweet_fields=[
                    "created_at",
                    "author_id",
                    "public_metrics",
                    "context_annotations",
                ],
                user_fields=["username", "name"],
                expansions=["author_id"],
                max_results=50,
            )

            interactions = []

            if mentions.data:
                # Build user lookup
                users = (
                    {user["id"]: user for user in mentions.includes.get("users", [])}
                    if mentions.includes
                    else {}
                )

                for tweet in mentions.data:
                    # Get author info
                    author_info = users.get(tweet.author_id, {})
                    author_username = author_info.get("username", "unknown")

                    # Create interaction
                    interaction = TwitterInteraction(
                        tweet_id=tweet.id,
                        author_id=tweet.author_id,
                        author_username=author_username,
                        content=tweet.text,
                        interaction_type=InteractionType.MENTION,
                        metadata={
                            "created_at": tweet.created_at.isoformat()
                            if tweet.created_at
                            else None,
                            "public_metrics": tweet.public_metrics or {},
                            "context_annotations": tweet.context_annotations or [],
                        },
                    )

                    # Build conversation context
                    interaction.context_thread = await self.build_conversation_thread(
                        tweet.id
                    )

                    # Cache the interaction
                    self.interaction_cache[tweet.id] = interaction
                    interactions.append(interaction)

                logger.info(f"Processed {len(interactions)} new mentions")

            self.last_mention_check = datetime.now(timezone.utc)
            return interactions

        except Exception as e:
            logger.error(f"Error processing mentions: {e}")
            raise TwitterInteractionError(f"Failed to process mentions: {e}")

    async def build_conversation_thread(
        self, tweet_id: str, max_depth: int = 10
    ) -> List[str]:
        """
        Build conversation thread context for a tweet
        Based on elizaOS buildConversationThread()
        """
        if not self.client:
            raise TwitterInteractionError("Twitter client not initialized")

        try:
            thread_tweets = []
            current_tweet_id = tweet_id
            depth = 0

            # Walk up the conversation thread
            while current_tweet_id and depth < max_depth:
                await self.rate_limiter.wait_for_slot()

                # Get the tweet
                tweet = self.client.get_tweet(
                    current_tweet_id,
                    tweet_fields=[
                        "created_at",
                        "author_id",
                        "in_reply_to_tweet_id",
                        "conversation_id",
                    ],
                    user_fields=["username"],
                    expansions=["author_id", "in_reply_to_tweet_id"],
                )

                if not tweet.data:
                    break

                # Get author info
                users = (
                    {user["id"]: user for user in includes.get("users", [])}
                    if "users" in str(tweet)
                    else {}
                )
                author_info = users.get(tweet.data.author_id, {})

                tweet_data = {
                    "id": tweet.data.id,
                    "text": tweet.data.text,
                    "author_id": tweet.data.author_id,
                    "author_username": author_info.get("username", "unknown"),
                    "created_at": tweet.data.created_at.isoformat()
                    if tweet.data.created_at
                    else None,
                    "in_reply_to_tweet_id": tweet.data.in_reply_to_tweet_id,
                }

                thread_tweets.append(tweet_data)

                # Move to the parent tweet
                current_tweet_id = tweet.data.in_reply_to_tweet_id
                depth += 1

            # Return thread in chronological order (oldest first)
            return [tweet["text"] for tweet in reversed(thread_tweets)]

        except Exception as e:
            logger.error(f"Error building conversation thread for {tweet_id}: {e}")
            return []

    async def handle_interaction(self, interaction: TwitterInteraction) -> str:
        """
        Generate a contextual reply for an interaction
        Based on elizaOS handleTweet()
        """
        try:
            # Build context prompt
            context_prompt = self._build_context_prompt(interaction)

            # Generate reply using AI
            reply_content = await ai_service_manager.generate_text(
                prompt=context_prompt,
                max_tokens=280,  # Twitter limit
                temperature=0.7,
                persona_id="twitter_reply_assistant",
            )

            # Clean and validate reply
            reply_content = self._clean_reply(
                reply_content, interaction.author_username
            )

            # Store reply in interaction
            interaction.reply_content = reply_content
            interaction.processed_at = datetime.now(timezone.utc)

            logger.info(
                f"Generated reply for mention {interaction.tweet_id}: {reply_content[:50]}..."
            )
            return reply_content

        except Exception as e:
            logger.error(f"Error handling interaction {interaction.tweet_id}: {e}")
            raise TwitterInteractionError(f"Failed to generate reply: {e}")

    def _build_context_prompt(self, interaction: TwitterInteraction) -> str:
        """Build AI prompt with conversation context"""
        prompt_parts = [
            "You are @Beyondlines, an intelligent AI assistant responding to Twitter mentions.",
            f"You need to reply to a mention from @{interaction.author_username}.",
            "",
            "Conversation Thread (chronological):",
        ]

        # Add thread context
        for i, tweet_text in enumerate(interaction.context_thread):
            prompt_parts.append(f"{i+1}. {tweet_text}")

        prompt_parts.extend(
            [
                "",
                "The latest tweet above is the one mentioning you.",
                "",
                "Guidelines for your reply:",
                "- Be helpful and conversational",
                "- Keep it under 280 characters",
                "- Don't repeat the original content",
                "- Add value to the conversation",
                "- Use appropriate emojis sparingly",
                "- If it's a question, answer it thoughtfully",
                "",
                "Your reply:",
            ]
        )

        return "\n".join(prompt_parts)

    def _clean_reply(self, reply: str, mentioned_user: str) -> str:
        """Clean and format the reply"""
        # Remove any potential @ mentions to avoid spam
        reply = reply.strip()

        # Ensure we mention the original user
        if not reply.startswith(f"@{mentioned_user}"):
            reply = f"@{mentioned_user} {reply}"

        # Remove extra whitespace
        reply = " ".join(reply.split())

        # Ensure it's within Twitter limit
        if len(reply) > 280:
            reply = reply[:277] + "..."

        return reply

    async def post_reply(self, interaction: TwitterInteraction) -> bool:
        """Post the generated reply to Twitter"""
        if not self.client or not interaction.reply_content:
            return False

        try:
            await self.rate_limiter.wait_for_slot()

            # Post the reply
            response = self.client.create_tweet(
                text=interaction.reply_content,
                in_reply_to_tweet_id=interaction.tweet_id,
            )

            if response.data:
                interaction.status = InteractionStatus.POSTED
                logger.info(f"Successfully posted reply for {interaction.tweet_id}")
                return True
            else:
                interaction.status = InteractionStatus.FAILED
                return False

        except Exception as e:
            logger.error(f"Error posting reply for {interaction.tweet_id}: {e}")
            interaction.status = InteractionStatus.FAILED
            return False

    async def start_mention_monitoring(self, check_interval: int = 300):
        """Start background monitoring for mentions"""
        logger.info(f"Starting mention monitoring with {check_interval}s interval")

        while True:
            try:
                # Process mentions
                mentions = await self.process_mentions(check_interval)

                # Add to processing queue
                for mention in mentions:
                    await self.processing_queue.put(mention)

                # Wait for next check
                await asyncio.sleep(check_interval)

            except Exception as e:
                logger.error(f"Error in mention monitoring: {e}")
                await asyncio.sleep(60)  # Wait before retrying

    async def start_interaction_processor(self):
        """Start processing interactions from the queue"""
        logger.info("Starting interaction processor")

        while True:
            try:
                # Get interaction from queue
                interaction = await self.processing_queue.get()

                # Process the interaction
                await self.handle_interaction(interaction)

                # In a real system, you might want to add human approval here
                # For now, auto-approve
                interaction.status = InteractionStatus.APPROVED

                # Post the reply
                await self.post_reply(interaction)

                # Mark task as done
                self.processing_queue.task_done()

            except Exception as e:
                logger.error(f"Error processing interaction: {e}")
                await asyncio.sleep(5)  # Brief pause before continuing

    def get_interaction_stats(self) -> Dict[str, Any]:
        """Get statistics about processed interactions"""
        stats = {
            "total_interactions": len(self.interaction_cache),
            "by_status": {},
            "by_type": {},
            "queue_size": self.processing_queue.qsize(),
            "last_mention_check": self.last_mention_check.isoformat()
            if self.last_mention_check
            else None,
        }

        for interaction in self.interaction_cache.values():
            # Count by status
            status = interaction.status.value
            stats["by_status"][status] = stats["by_status"].get(status, 0) + 1

            # Count by type
            interaction_type = interaction.interaction_type.value
            stats["by_type"][interaction_type] = (
                stats["by_type"].get(interaction_type, 0) + 1
            )

        return stats


class TwitterRateLimiter:
    """Rate limiter for Twitter API calls with exponential backoff"""

    def __init__(self):
        self.last_request_time = 0
        self.min_interval = 1.0  # Minimum 1 second between requests
        self.rate_limit_window = 900  # 15 minutes
        self.max_requests_per_window = 300
        self.request_times = []

    async def wait_for_slot(self):
        """Wait until we can make a request"""
        now = time.time()

        # Clean old request times
        cutoff = now - self.rate_limit_window
        self.request_times = [t for t in self.request_times if t > cutoff]

        # Check if we're rate limited
        if len(self.request_times) >= self.max_requests_per_window:
            sleep_time = self.request_times[0] + self.rate_limit_window - now
            if sleep_time > 0:
                logger.warning(f"Rate limit reached, sleeping for {sleep_time:.1f}s")
                await asyncio.sleep(sleep_time)

        # Ensure minimum interval between requests
        time_since_last = now - self.last_request_time
        if time_since_last < self.min_interval:
            await asyncio.sleep(self.min_interval - time_since_last)

        # Record this request
        self.request_times.append(time.time())
        self.last_request_time = time.time()


# Global instance
twitter_interaction_client: Optional[TwitterInteractionClient] = None


async def init_twitter_interaction_client(
    api_keys: Dict[str, str]
) -> TwitterInteractionClient:
    """Initialize global Twitter interaction client"""
    global twitter_interaction_client
    twitter_interaction_client = TwitterInteractionClient(api_keys)
    await twitter_interaction_client.initialize()
    return twitter_interaction_client


def get_twitter_interaction_client() -> Optional[TwitterInteractionClient]:
    """Get global Twitter interaction client"""
    return twitter_interaction_client
