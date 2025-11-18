"""
Multi-Platform Social Media Interaction Client
Handles replies and mentions across Twitter, Threads, and other platforms
Based on elizaOS concepts but extended for multiple platforms
"""

import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

from ..core.analysis.ai_service_manager import ai_service_manager
from ..twitter.interaction_client import TwitterInteraction, TwitterInteractionClient
from ..utils.exceptions import ApprovalError, SocialInteractionError

logger = logging.getLogger(__name__)


class SocialPlatform(Enum):
    """Social media platforms"""

    TWITTER = "twitter"
    THREADS = "threads"
    TELEGRAM = "telegram"
    REDDIT = "reddit"


class InteractionStatus(Enum):
    """Status of interaction processing"""

    PENDING = "pending"
    PROCESSING = "processing"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    POSTED = "posted"
    FAILED = "failed"


class ApprovalChannel(Enum):
    """Approval channels"""

    DISCORD = "discord"
    TELEGRAM = "telegram"
    WEB_UI = "web_ui"
    EMAIL = "email"


@dataclass
class SocialInteraction:
    """Represents a social media interaction across platforms"""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    platform: SocialPlatform = SocialPlatform.TWITTER
    post_id: str = ""
    author_id: str = ""
    author_username: str = ""
    content: str = ""
    interaction_type: str = "mention"  # mention, reply, comment, etc.
    status: InteractionStatus = InteractionStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    processed_at: Optional[datetime] = None
    reply_content: Optional[str] = None
    context_thread: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    approval_channel: Optional[ApprovalChannel] = None
    approval_deadline: Optional[datetime] = None
    rejection_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "platform": self.platform.value,
            "post_id": self.post_id,
            "author_id": self.author_id,
            "author_username": self.author_username,
            "content": self.content,
            "interaction_type": self.interaction_type,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "processed_at": self.processed_at.isoformat()
            if self.processed_at
            else None,
            "reply_content": self.reply_content,
            "context_thread": self.context_thread,
            "metadata": self.metadata,
            "approval_channel": self.approval_channel.value
            if self.approval_channel
            else None,
            "approval_deadline": self.approval_deadline.isoformat()
            if self.approval_deadline
            else None,
            "rejection_reason": self.rejection_reason,
        }


class ApprovalTask:
    """Represents an approval task for social content"""

    def __init__(self, interaction: SocialInteraction, deadline_minutes: int = 30):
        self.interaction = interaction
        self.created_at = datetime.now(timezone.utc)
        self.deadline = self.created_at + timedelta(minutes=deadline_minutes)
        self.approved = None  # None, True, or False
        self.approved_by = None
        self.approved_at = None
        self.comments = None

    @property
    def is_expired(self) -> bool:
        """Check if approval deadline has passed"""
        return datetime.now(timezone.utc) > self.deadline

    @property
    def status(self) -> str:
        """Get approval status"""
        if self.approved is True:
            return "approved"
        elif self.approved is False:
            return "rejected"
        elif self.is_expired:
            return "expired"
        else:
            return "pending"


class ThreadsInteractionClient:
    """Threads-specific interaction client"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.rate_limiter = ThreadsRateLimiter()
        # Note: Threads doesn't have a public API for mentions yet
        # This would need to use browser automation or unofficial APIs

    async def check_mentions(self) -> List[SocialInteraction]:
        """Check for Threads mentions (conceptual - depends on available APIs)"""
        # Implementation would depend on Threads API availability
        logger.warning(
            "Threads mention checking not yet implemented - no public API available"
        )
        return []

    async def post_reply(self, interaction: SocialInteraction) -> bool:
        """Post a reply to Threads"""
        try:
            await self.rate_limiter.wait_for_slot()

            # This would use the Threads API or browser automation
            # For now, this is a placeholder
            logger.info(f"Would post Threads reply: {interaction.reply_content}")
            return True

        except Exception as e:
            logger.error(f"Error posting Threads reply: {e}")
            return False


class ThreadsRateLimiter:
    """Rate limiter for Threads API calls"""

    def __init__(self):
        self.last_request_time = 0
        self.min_interval = 2.0  # Conservative rate limit for Threads

    async def wait_for_slot(self):
        """Wait until we can make a request"""
        now = time.time()
        time_since_last = now - self.last_request_time
        if time_since_last < self.min_interval:
            await asyncio.sleep(self.min_interval - time_since_last)
        self.last_request_time = time.time()


class ApprovalWorkflow:
    """Approval workflow system for social interactions"""

    def __init__(self):
        self.pending_tasks: Dict[str, ApprovalTask] = {}
        self.approval_handlers: Dict[ApprovalChannel, callable] = {}
        self.auto_approve_patterns = []  # List of regex patterns for auto-approval
        self.auto_reject_patterns = []  # List of regex patterns for auto-rejection
        self.approval_statistics = {
            "total_submissions": 0,
            "auto_approved": 0,
            "manually_approved": 0,
            "auto_rejected": 0,
            "manually_rejected": 0,
            "expired": 0,
        }

    def register_approval_handler(self, channel: ApprovalChannel, handler: callable):
        """Register an approval handler for a channel"""
        self.approval_handlers[channel] = handler

    async def submit_for_approval(
        self,
        interaction: SocialInteraction,
        deadline_minutes: int = 30,
        channel: ApprovalChannel = ApprovalChannel.DISCORD,
    ) -> str:
        """Submit an interaction for approval"""

        # Check auto-approval patterns first
        auto_decision = await self._check_auto_patterns(interaction)

        if auto_decision == "approve":
            interaction.status = InteractionStatus.APPROVED
            self.approval_statistics["auto_approved"] += 1
            logger.info(f"Auto-approved interaction {interaction.id}")
            return "auto_approved"

        elif auto_decision == "reject":
            interaction.status = InteractionStatus.REJECTED
            interaction.rejection_reason = "Auto-rejected by pattern matching"
            self.approval_statistics["auto_rejected"] += 1
            logger.info(f"Auto-rejected interaction {interaction.id}")
            return "auto_rejected"

        # Create approval task
        task = ApprovalTask(interaction, deadline_minutes)
        self.pending_tasks[interaction.id] = task

        # Update interaction status
        interaction.status = InteractionStatus.AWAITING_APPROVAL
        interaction.approval_channel = channel
        interaction.approval_deadline = task.deadline

        # Submit to approval channel
        await self._send_to_approval_channel(task, channel)

        self.approval_statistics["total_submissions"] += 1
        logger.info(
            f"Submitted interaction {interaction.id} for approval via {channel.value}"
        )

        return "submitted"

    async def approve_interaction(
        self, interaction_id: str, approved_by: str, comments: Optional[str] = None
    ) -> bool:
        """Manually approve an interaction"""
        if interaction_id not in self.pending_tasks:
            return False

        task = self.pending_tasks[interaction_id]
        if task.status != "pending":
            return False

        # Update task
        task.approved = True
        task.approved_by = approved_by
        task.approved_at = datetime.now(timezone.utc)
        task.comments = comments

        # Update interaction
        task.interaction.status = InteractionStatus.APPROVED
        self.approval_statistics["manually_approved"] += 1

        logger.info(f"Manually approved interaction {interaction_id} by {approved_by}")
        return True

    async def reject_interaction(
        self, interaction_id: str, rejected_by: str, reason: str
    ) -> bool:
        """Manually reject an interaction"""
        if interaction_id not in self.pending_tasks:
            return False

        task = self.pending_tasks[interaction_id]
        if task.status != "pending":
            return False

        # Update task
        task.approved = False
        task.approved_by = rejected_by
        task.approved_at = datetime.now(timezone.utc)
        task.comments = reason

        # Update interaction
        task.interaction.status = InteractionStatus.REJECTED
        task.interaction.rejection_reason = reason
        self.approval_statistics["manually_rejected"] += 1

        logger.info(
            f"Manually rejected interaction {interaction_id} by {rejected_by}: {reason}"
        )
        return True

    async def process_expired_tasks(self):
        """Process expired approval tasks"""
        now = datetime.now(timezone.utc)
        expired_tasks = []

        for interaction_id, task in self.pending_tasks.items():
            if task.status == "pending" and now > task.deadline:
                expired_tasks.append(interaction_id)

        for interaction_id in expired_tasks:
            task = self.pending_tasks[interaction_id]
            task.interaction.status = InteractionStatus.REJECTED
            task.interaction.rejection_reason = "Approval deadline expired"
            self.approval_statistics["expired"] += 1

            # Remove from pending tasks
            del self.pending_tasks[interaction_id]

            logger.info(f"Approval expired for interaction {interaction_id}")

    async def _check_auto_patterns(
        self, interaction: SocialInteraction
    ) -> Optional[str]:
        """Check if interaction matches auto-approval/rejection patterns"""
        content_lower = interaction.content.lower()
        reply_lower = (
            interaction.reply_content.lower() if interaction.reply_content else ""
        )

        # Auto-approval patterns (e.g., positive mentions, simple questions)
        auto_approve_patterns = [
            r"(good|great|awesome|amazing|love|thanks)",
            r"\b(what|how|when|where|why)\b.*\?",
            r"help.*\?",
        ]

        # Auto-rejection patterns (e.g., spam, inappropriate content)
        auto_reject_patterns = [
            r"(spam|scam|buy now|click here)",
            r"(inappropriate|offensive)",
            r"http[s]?://\S+",  # Too many URLs
        ]

        import re

        for pattern in auto_approve_patterns:
            if re.search(pattern, content_lower) or re.search(pattern, reply_lower):
                return "approve"

        for pattern in auto_reject_patterns:
            if re.search(pattern, content_lower) or re.search(pattern, reply_lower):
                return "reject"

        return None

    async def _send_to_approval_channel(
        self, task: ApprovalTask, channel: ApprovalChannel
    ):
        """Send approval task to the specified channel"""
        handler = self.approval_handlers.get(channel)
        if handler:
            try:
                await handler(task)
            except Exception as e:
                logger.error(f"Error sending to approval channel {channel.value}: {e}")
        else:
            logger.warning(
                f"No handler registered for approval channel: {channel.value}"
            )

    def get_pending_tasks(self) -> List[Dict[str, Any]]:
        """Get list of pending approval tasks"""
        return [
            {
                "interaction_id": interaction_id,
                "interaction": task.interaction.to_dict(),
                "deadline": task.deadline.isoformat(),
                "status": task.status,
                "time_remaining": max(
                    0, (task.deadline - datetime.now(timezone.utc)).total_seconds()
                ),
            }
            for interaction_id, task in self.pending_tasks.items()
        ]

    def get_statistics(self) -> Dict[str, Any]:
        """Get approval workflow statistics"""
        stats = self.approval_statistics.copy()
        stats["pending_tasks"] = len(self.pending_tasks)

        if stats["total_submissions"] > 0:
            stats["approval_rate"] = (
                stats["auto_approved"] + stats["manually_approved"]
            ) / stats["total_submissions"]
            stats["auto_approval_rate"] = (
                stats["auto_approved"] / stats["total_submissions"]
            )
        else:
            stats["approval_rate"] = 0
            stats["auto_approval_rate"] = 0

        return stats


class MultiPlatformInteractionClient:
    """
    Multi-platform social media interaction client
    Based on elizaOS concepts but extended for Twitter, Threads, etc.
    """

    def __init__(self, platform_configs: Dict[str, Dict[str, Any]]):
        self.platform_configs = platform_configs
        self.clients: Dict[SocialPlatform, Any] = {}
        self.approval_workflow = ApprovalWorkflow()
        self.interaction_cache: Dict[str, SocialInteraction] = {}
        self.processing_queue = asyncio.Queue()

    async def initialize(self):
        """Initialize all platform clients"""
        # Initialize Twitter client
        if "twitter" in self.platform_configs:
            from ..twitter.interaction_client import init_twitter_interaction_client

            self.clients[
                SocialPlatform.TWITTER
            ] = await init_twitter_interaction_client(self.platform_configs["twitter"])
            logger.info("Twitter interaction client initialized")

        # Initialize Threads client
        if "threads" in self.platform_configs:
            self.clients[SocialPlatform.THREADS] = ThreadsInteractionClient(
                self.platform_configs["threads"]
            )
            logger.info("Threads interaction client initialized")

        # Register default approval handlers
        await self._register_default_handlers()

    async def _register_default_handlers(self):
        """Register default approval handlers"""

        # Discord handler (placeholder - would need Discord bot implementation)
        async def discord_handler(task: ApprovalTask):
            logger.info(f"[DISCORD] Approval needed for {task.interaction.id}")
            # Implement Discord notification logic here

        # Telegram handler (placeholder - would need Telegram bot implementation)
        async def telegram_handler(task: ApprovalTask):
            logger.info(f"[TELEGRAM] Approval needed for {task.interaction.id}")
            # Implement Telegram notification logic here

        self.approval_workflow.register_approval_handler(
            ApprovalChannel.DISCORD, discord_handler
        )
        self.approval_workflow.register_approval_handler(
            ApprovalChannel.TELEGRAM, telegram_handler
        )

    async def check_all_platforms(self) -> List[SocialInteraction]:
        """Check for new interactions across all platforms"""
        all_interactions = []

        for platform, client in self.clients.items():
            try:
                if platform == SocialPlatform.TWITTER:
                    # Use existing Twitter client
                    twitter_interactions = await client.process_mentions()
                    for twitter_interaction in twitter_interactions:
                        # Convert to multi-platform format
                        interaction = SocialInteraction(
                            platform=SocialPlatform.TWITTER,
                            post_id=twitter_interaction.tweet_id,
                            author_id=twitter_interaction.author_id,
                            author_username=twitter_interaction.author_username,
                            content=twitter_interaction.content,
                            interaction_type=twitter_interaction.interaction_type.value,
                            context_thread=twitter_interaction.context_thread,
                            metadata=twitter_interaction.metadata,
                        )
                        all_interactions.append(interaction)

                elif platform == SocialPlatform.THREADS:
                    # Use Threads client
                    threads_interactions = await client.check_mentions()
                    all_interactions.extend(threads_interactions)

            except Exception as e:
                logger.error(f"Error checking {platform.value} for interactions: {e}")

        # Cache interactions
        for interaction in all_interactions:
            self.interaction_cache[interaction.id] = interaction

        logger.info(f"Found {len(all_interactions)} new interactions across platforms")
        return all_interactions

    async def process_interaction(self, interaction: SocialInteraction) -> bool:
        """Process an interaction (generate reply, submit for approval, post)"""
        try:
            # Generate reply content
            reply_content = await self._generate_reply(interaction)
            interaction.reply_content = reply_content
            interaction.processed_at = datetime.now(timezone.utc)

            # Submit for approval
            approval_result = await self.approval_workflow.submit_for_approval(
                interaction
            )

            if approval_result == "approved":
                # Auto-approved, post immediately
                return await self._post_reply(interaction)
            elif approval_result == "submitted":
                # Waiting for manual approval
                logger.info(f"Interaction {interaction.id} submitted for approval")
                return True
            else:
                # Auto-rejected
                logger.info(f"Interaction {interaction.id} auto-rejected")
                return False

        except Exception as e:
            logger.error(f"Error processing interaction {interaction.id}: {e}")
            interaction.status = InteractionStatus.FAILED
            return False

    async def _generate_reply(self, interaction: SocialPlatform) -> str:
        """Generate a contextual reply for an interaction"""
        # Build platform-specific prompt
        if interaction.platform == SocialPlatform.TWITTER:
            platform_context = (
                "Twitter (280 character limit, supports @ mentions and hashtags)"
            )
        elif interaction.platform == SocialPlatform.THREADS:
            platform_context = "Threads (500 character limit, more conversational tone)"
        else:
            platform_context = "Social media platform"

        prompt_parts = [
            f"You are Beyondlines, an intelligent AI assistant responding on {platform_context}.",
            f"You're replying to {interaction.interaction_type} from @{interaction.author_username}.",
            "",
            "Conversation Context:",
        ]

        # Add thread context
        for i, tweet_text in enumerate(interaction.context_thread):
            prompt_parts.append(f"{i+1}. {tweet_text}")

        prompt_parts.extend(
            [
                "",
                "Guidelines:",
                "- Be helpful and conversational",
                f"Keep it under the character limit for {platform_context}",
                "- Add value to the conversation",
                "- Use appropriate tone for the platform",
                "",
                "Your reply:",
            ]
        )

        prompt = "\n".join(prompt_parts)

        # Generate reply using AI
        reply_content = await ai_service_manager.generate_text(
            prompt=prompt,
            max_tokens=500,  # Will be trimmed based on platform
            temperature=0.7,
            persona_id=f"{interaction.platform.value}_reply_assistant",
        )

        # Clean and format reply for platform
        return self._clean_reply_for_platform(reply_content, interaction)

    def _clean_reply_for_platform(
        self, reply: str, interaction: SocialInteraction
    ) -> str:
        """Clean and format reply for specific platform"""
        reply = reply.strip()

        if interaction.platform == SocialPlatform.TWITTER:
            # Twitter-specific formatting
            if not reply.startswith(f"@{interaction.author_username}"):
                reply = f"@{interaction.author_username} {reply}"
            max_length = 280

        elif interaction.platform == SocialPlatform.THREADS:
            # Threads-specific formatting
            max_length = 500
            # Threads doesn't use @ mentions the same way
            if reply.startswith(f"@{interaction.author_username}"):
                reply = reply[len(f"@{interaction.author_username}") :].strip()

        else:
            max_length = 500

        # Clean up whitespace
        reply = " ".join(reply.split())

        # Ensure length limit
        if len(reply) > max_length:
            reply = reply[: max_length - 3] + "..."

        return reply

    async def _post_reply(self, interaction: SocialInteraction) -> bool:
        """Post the reply to the appropriate platform"""
        if interaction.platform not in self.clients:
            logger.error(
                f"No client available for platform {interaction.platform.value}"
            )
            return False

        try:
            client = self.clients[interaction.platform]

            if interaction.platform == SocialPlatform.TWITTER:
                # Use Twitter client
                twitter_interaction = TwitterInteraction(
                    tweet_id=interaction.post_id,
                    author_id=interaction.author_id,
                    author_username=interaction.author_username,
                    content=interaction.content,
                    interaction_type=interaction.interaction_type,
                    reply_content=interaction.reply_content,
                )
                success = await client.post_reply(twitter_interaction)

            elif interaction.platform == SocialPlatform.THREADS:
                # Use Threads client
                success = await client.post_reply(interaction)

            else:
                logger.warning(
                    f"Posting not implemented for platform {interaction.platform.value}"
                )
                return False

            if success:
                interaction.status = InteractionStatus.POSTED
                logger.info(
                    f"Successfully posted reply for {interaction.id} on {interaction.platform.value}"
                )

            return success

        except Exception as e:
            logger.error(f"Error posting reply for {interaction.id}: {e}")
            interaction.status = InteractionStatus.FAILED
            return False

    async def start_monitoring_loop(self, check_interval: int = 300):
        """Start the main monitoring and processing loop"""
        logger.info(
            f"Starting multi-platform monitoring with {check_interval}s interval"
        )

        while True:
            try:
                # Check all platforms for new interactions
                interactions = await self.check_all_platforms()

                # Add to processing queue
                for interaction in interactions:
                    await self.processing_queue.put(interaction)

                # Process expired approval tasks
                await self.approval_workflow.process_expired_tasks()

                # Wait for next check
                await asyncio.sleep(check_interval)

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)  # Wait before retrying

    async def start_processing_loop(self):
        """Start processing interactions from the queue"""
        logger.info("Starting interaction processing loop")

        while True:
            try:
                # Get interaction from queue
                interaction = await self.processing_queue.get()

                # Process the interaction
                await self.process_interaction(interaction)

                # Mark task as done
                self.processing_queue.task_done()

            except Exception as e:
                logger.error(f"Error in processing loop: {e}")
                await asyncio.sleep(5)  # Brief pause before continuing

    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status"""
        return {
            "platforms": list(self.platform_configs.keys()),
            "initialized_clients": list(self.clients.keys()),
            "cache_size": len(self.interaction_cache),
            "queue_size": self.processing_queue.qsize(),
            "approval_stats": self.approval_workflow.get_statistics(),
            "pending_approvals": len(self.approval_workflow.get_pending_tasks()),
        }


# Global instance
multiplatform_client: Optional[MultiPlatformInteractionClient] = None


async def init_multiplatform_client(
    platform_configs: Dict[str, Dict[str, Any]]
) -> MultiPlatformInteractionClient:
    """Initialize global multi-platform client"""
    global multiplatform_client
    multiplatform_client = MultiPlatformInteractionClient(platform_configs)
    await multiplatform_client.initialize()
    return multiplatform_client


def get_multiplatform_client() -> Optional[MultiPlatformInteractionClient]:
    """Get global multi-platform client"""
    return multiplatform_client
