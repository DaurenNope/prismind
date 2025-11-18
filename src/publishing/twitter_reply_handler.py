"""
Twitter Reply Handler - Ported concepts from elizaOS TwitterInteractionClient

This module handles automatic replies to Twitter mentions, inspired by elizaOS's
"reply guy" feature. Uses LLM to generate contextual replies based on mentions.

Key concepts from elizaOS:
- Process mentions and build conversation threads
- Generate contextual replies using LLM
- Handle interactions (likes, retweets, quotes)
- Cache tweets and manage state
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class TwitterMention:
    """Represents a Twitter mention that needs a reply"""

    tweet_id: str
    username: str
    text: str
    conversation_id: str
    in_reply_to_id: Optional[str] = None
    thread: List[Dict[str, Any]] = None  # Full thread context


@dataclass
class TwitterInteraction:
    """Represents a Twitter interaction (like, retweet, quote)"""

    interaction_id: str
    interaction_type: str  # "like", "retweet", "quote"
    user_id: str
    username: str
    target_tweet_id: str
    timestamp: datetime


class TwitterReplyHandler:
    """
    Handles automatic replies to Twitter mentions, inspired by elizaOS's approach.

    Key features:
    - Monitors mentions and processes them
    - Builds conversation threads for context
    - Generates contextual replies using LLM
    - Manages reply state and rate limiting
    """

    def __init__(self, llm_client, storage_adapter):
        """
        Initialize the reply handler.

        Args:
            llm_client: LLM client for generating replies
            storage_adapter: Storage adapter for caching tweets/state
        """
        self.llm_client = llm_client
        self.storage = storage_adapter
        self.last_checked_mention_id: Optional[str] = None
        self.replied_tweet_ids = set()  # Track which tweets we've already replied to

    async def process_mentions(
        self, mentions: List[TwitterMention]
    ) -> List[Dict[str, Any]]:
        """
        Process incoming mentions and generate replies.

        Inspired by elizaOS's processMentionTweets() method.

        Args:
            mentions: List of Twitter mentions to process

        Returns:
            List of generated replies ready to post
        """
        replies = []

        for mention in mentions:
            # Skip if we've already replied
            if mention.tweet_id in self.replied_tweet_ids:
                continue

            # Build conversation thread for context
            thread = await self.build_conversation_thread(mention)

            # Generate reply using LLM
            reply_text = await self.generate_reply(mention, thread)

            if reply_text:
                replies.append(
                    {
                        "tweet_id": mention.tweet_id,
                        "reply_text": reply_text,
                        "in_reply_to_id": mention.tweet_id,
                        "conversation_id": mention.conversation_id,
                    }
                )
                self.replied_tweet_ids.add(mention.tweet_id)

        return replies

    async def build_conversation_thread(
        self, mention: TwitterMention, max_replies: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Build a conversation thread for context.

        Inspired by elizaOS's buildConversationThread() method.

        Args:
            mention: The mention to build thread for
            max_replies: Maximum number of replies to include

        Returns:
            List of tweets in the conversation thread
        """
        thread = []

        # Start with the mention itself
        thread.append(
            {
                "id": mention.tweet_id,
                "text": mention.text,
                "username": mention.username,
            }
        )

        # Fetch parent tweet if this is a reply
        if mention.in_reply_to_id:
            parent = await self.get_tweet(mention.in_reply_to_id)
            if parent:
                thread.insert(0, parent)

        # Fetch additional replies in the conversation
        # (Implementation would fetch from Twitter API or cache)

        return thread

    async def generate_reply(
        self, mention: TwitterMention, thread: List[Dict[str, Any]]
    ) -> Optional[str]:
        """
        Generate a contextual reply using LLM.

        Inspired by elizaOS's handleTweet() method.

        Args:
            mention: The mention to reply to
            thread: Conversation thread for context

        Returns:
            Generated reply text, or None if no reply should be sent
        """
        # Build prompt from thread context
        thread_text = "\n".join(
            [f"@{tweet['username']}: {tweet['text']}" for tweet in thread]
        )

        prompt = f"""You are a helpful Twitter bot. Generate a brief, contextual reply to this mention.

Conversation thread:
{thread_text}

Latest mention (to reply to):
@{mention.username}: {mention.text}

Generate a natural, helpful reply (under 280 characters). If the mention doesn't require a reply, return "SKIP".
"""

        try:
            reply = await self.llm_client.generate(prompt, max_tokens=100)

            # Clean up reply
            reply = reply.strip()
            if reply.upper() == "SKIP" or len(reply) > 280:
                return None

            return reply

        except Exception as e:
            logger.error(f"Error generating reply: {e}")
            return None

    async def get_tweet(self, tweet_id: str) -> Optional[Dict[str, Any]]:
        """Get a tweet by ID (from cache or API)"""
        # Check cache first
        cached = await self.storage.get_cached_tweet(tweet_id)
        if cached:
            return cached

        # Fetch from API if not cached
        # (Implementation would call Twitter API)
        return None

    async def handle_interactions(self, interactions: List[TwitterInteraction]):
        """
        Handle Twitter interactions (likes, retweets, quotes).

        Inspired by elizaOS's handleInteraction() method.

        Args:
            interactions: List of interactions to process
        """
        for interaction in interactions:
            # Log interaction
            await self.storage.save_interaction(
                {
                    "interaction_id": interaction.interaction_id,
                    "type": interaction.interaction_type,
                    "user_id": interaction.user_id,
                    "username": interaction.username,
                    "target_tweet_id": interaction.target_tweet_id,
                    "timestamp": interaction.timestamp.isoformat(),
                }
            )

            # Could trigger actions based on interaction type
            # e.g., auto-reply to quotes, thank for retweets, etc.


# Example usage pattern (to be integrated into automation):
"""
async def twitter_reply_worker():
    handler = TwitterReplyHandler(llm_client, storage_adapter)

    while True:
        # Fetch new mentions
        mentions = await fetch_mentions(since_id=handler.last_checked_mention_id)

        # Process and generate replies
        replies = await handler.process_mentions(mentions)

        # Post replies (with approval if needed)
        for reply in replies:
            await post_tweet_reply(
                text=reply["reply_text"],
                in_reply_to_id=reply["tweet_id"]
            )

        # Update last checked ID
        if mentions:
            handler.last_checked_mention_id = mentions[-1].tweet_id

        await asyncio.sleep(60)  # Check every minute
"""
