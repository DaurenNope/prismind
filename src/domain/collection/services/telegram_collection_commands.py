#!/usr/bin/env python3
"""
Telegram Bot Collection Commands
Provides collection commands for the Telegram bot using unified service
"""

import asyncio
import logging
from typing import Dict

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from src.services.unified_collection_service import (
    CollectionProgress,
    CollectionStatus,
    UnifiedCollectionService,
)

logger = logging.getLogger(__name__)

# Global service instance
_collection_service: UnifiedCollectionService = None


def get_collection_service() -> UnifiedCollectionService:
    """Get or create collection service"""
    global _collection_service
    if _collection_service is None:
        _collection_service = UnifiedCollectionService()
    return _collection_service


async def collect_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /collect command

    Usage:
        /collect - Show collection menu
        /collect threads - Collect from Threads
        /collect twitter - Collect from Twitter
        /collect reddit - Collect from Reddit
        /collect all - Collect from all platforms
    """
    service = get_collection_service()

    # Check if already collecting
    if service.is_collecting():
        await update.message.reply_text(
            "⏳ Collection already in progress. Please wait for it to complete."
        )
        return

    # Parse arguments
    args = context.args if context.args else []

    if not args:
        # Show menu
        keyboard = [
            [
                InlineKeyboardButton("🧵 Threads", callback_data="collect_threads"),
                InlineKeyboardButton("🐦 Twitter", callback_data="collect_twitter"),
            ],
            [
                InlineKeyboardButton("📱 Reddit", callback_data="collect_reddit"),
                InlineKeyboardButton("🚀 All Platforms", callback_data="collect_all"),
            ],
            [
                InlineKeyboardButton("📊 Status", callback_data="collection_status"),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "📥 <b>Collection Manager</b>\n\nSelect a platform to collect from:",
            reply_markup=reply_markup,
            parse_mode="HTML",
        )
        return

    # Handle platform argument
    platform = args[0].lower()

    if platform == "all":
        await _collect_all_platforms(update, service)
    elif platform in service.get_supported_platforms():
        await _collect_from_platform(update, service, platform)
    else:
        await update.message.reply_text(
            f"❌ Unknown platform: {platform}\n\n"
            f"Supported: {', '.join(service.get_supported_platforms())}"
        )


async def _collect_from_platform(
    update: Update, service: UnifiedCollectionService, platform: str
):
    """Collect from a specific platform"""
    # Send initial message
    status_message = await update.message.reply_text(
        f"🚀 Starting {platform.title()} collection...", parse_mode="HTML"
    )

    # Progress callback
    async def update_status(progress: CollectionProgress):
        """Update status message with progress"""
        emoji = {
            CollectionStatus.STARTING: "🚀",
            CollectionStatus.AUTHENTICATING: "🔐",
            CollectionStatus.COLLECTING: "📥",
            CollectionStatus.ANALYZING: "🤖",
            CollectionStatus.COMPLETED: "✅",
            CollectionStatus.FAILED: "❌",
        }.get(progress.status, "⏳")

        status_text = (
            f"{emoji} <b>{platform.title()} Collection</b>\n\n"
            f"Status: {progress.status.value}\n"
            f"Posts collected: {progress.posts_collected}\n"
            f"Message: {progress.current_message}"
        )

        try:
            await status_message.edit_text(status_text, parse_mode="HTML")
        except Exception as e:
            logger.debug(f"Failed to update status message: {e}")

    # Run collection
    result = await service.collect(platform, progress_callback=update_status)

    # Send final result
    if result.success:
        final_text = (
            f"✅ <b>{platform.title()} Collection Complete!</b>\n\n"
            f"📊 Results:\n"
            f"• Posts collected: {result.posts_collected}\n"
            f"• Duration: {result.duration_seconds:.1f}s\n"
            f"• Posts/sec: {result.posts_collected / result.duration_seconds:.1f}"
        )
    else:
        final_text = (
            f"❌ <b>{platform.title()} Collection Failed</b>\n\n"
            f"Error: {result.error}\n"
            f"Duration: {result.duration_seconds:.1f}s"
        )

    await status_message.edit_text(final_text, parse_mode="HTML")


async def _collect_all_platforms(update: Update, service: UnifiedCollectionService):
    """Collect from all platforms"""
    status_message = await update.message.reply_text(
        "🚀 Starting collection from all platforms...", parse_mode="HTML"
    )

    # Track progress
    platform_statuses: Dict[str, str] = {}

    async def update_status(progress: CollectionProgress):
        """Update status for current platform"""
        platform_statuses[progress.platform] = (
            f"{progress.status.value} ({progress.posts_collected})"
        )

        status_text = "📥 <b>Collecting from all platforms</b>\n\n"
        for p in service.get_supported_platforms():
            status = platform_statuses.get(p, "pending")
            emoji = "⏳" if p == progress.platform else "⏸️"
            status_text += f"{emoji} {p.title()}: {status}\n"

        try:
            await status_message.edit_text(status_text, parse_mode="HTML")
        except Exception as e:
            logger.debug(f"Failed to update status: {e}")

    # Run collection
    results = await service.collect_all(progress_callback=update_status)

    # Calculate totals
    total_collected = sum(r.posts_collected for r in results.values())
    total_duration = sum(r.duration_seconds for r in results.values())
    success_count = sum(1 for r in results.values() if r.success)

    # Send final result
    final_text = (
        f"{'✅' if success_count == len(results) else '⚠️'} <b>Collection Complete!</b>\n\n"
        f"📊 Summary:\n"
        f"• Total posts: {total_collected}\n"
        f"• Duration: {total_duration:.1f}s\n"
        f"• Success rate: {success_count}/{len(results)} platforms\n\n"
        f"<b>Details:</b>\n"
    )

    for platform, result in results.items():
        emoji = "✅" if result.success else "❌"
        final_text += f"{emoji} {platform.title()}: {result.posts_collected} posts\n"
        if not result.success:
            final_text += f"   Error: {result.error[:50]}...\n"

    await status_message.edit_text(final_text, parse_mode="HTML")


async def collection_status_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Handle /collection_status command
    Show current collection status and recent history
    """
    service = get_collection_service()

    # Check if collecting
    if service.is_collecting():
        progress = service.get_current_progress()

        text = (
            "⏳ <b>Collection In Progress</b>\n\n"
            f"Platform: {progress.platform.title()}\n"
            f"Status: {progress.status.value}\n"
            f"Posts collected: {progress.posts_collected}\n"
            f"Message: {progress.current_message}"
        )
    else:
        # Show database stats
        from src.services.new_database_manager import NewDatabaseManager

        db = NewDatabaseManager()

        threads_count = len(db.get_posts_by_platform("threads"))
        twitter_count = len(db.get_posts_by_platform("twitter"))
        reddit_count = len(db.get_posts_by_platform("reddit"))
        total_count = threads_count + twitter_count + reddit_count

        text = (
            "📊 <b>Collection Status</b>\n\n"
            f"Current state: Idle\n\n"
            f"<b>Database Statistics:</b>\n"
            f"🧵 Threads: {threads_count} posts\n"
            f"🐦 Twitter: {twitter_count} posts\n"
            f"📱 Reddit: {reddit_count} posts\n"
            f"📦 Total: {total_count} posts\n\n"
            "Use /collect to start a new collection"
        )

    await update.message.reply_text(text, parse_mode="HTML")


async def collection_callback_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle inline button callbacks for collection"""
    query = update.callback_query
    await query.answer()

    service = get_collection_service()

    # Check if already collecting
    if service.is_collecting():
        await query.edit_message_text(
            "⏳ Collection already in progress. Please wait for it to complete."
        )
        return

    # Handle callback
    data = query.data

    if data == "collection_status":
        # Show status
        from src.services.new_database_manager import NewDatabaseManager

        db = NewDatabaseManager()

        threads_count = len(db.get_posts_by_platform("threads"))
        twitter_count = len(db.get_posts_by_platform("twitter"))
        reddit_count = len(db.get_posts_by_platform("reddit"))

        text = (
            "📊 <b>Current Status</b>\n\n"
            f"🧵 Threads: {threads_count} posts\n"
            f"🐦 Twitter: {twitter_count} posts\n"
            f"📱 Reddit: {reddit_count} posts"
        )
        await query.edit_message_text(text, parse_mode="HTML")

    elif data.startswith("collect_"):
        # Extract platform
        platform = data.replace("collect_", "")

        if platform == "all":
            # Create fake update with message
            class FakeMessage:
                def __init__(self, chat_id, bot):
                    self.chat_id = chat_id
                    self._bot = bot

                async def reply_text(self, text, **kwargs):
                    return await self._bot.send_message(
                        chat_id=self.chat_id, text=text, **kwargs
                    )

            fake_update = Update(update.update_id)
            fake_update._effective_message = FakeMessage(
                query.message.chat_id, context.bot
            )

            await _collect_all_platforms(fake_update, service)
        else:
            # Create fake update
            class FakeMessage:
                def __init__(self, chat_id, bot):
                    self.chat_id = chat_id
                    self._bot = bot

                async def reply_text(self, text, **kwargs):
                    return await self._bot.send_message(
                        chat_id=self.chat_id, text=text, **kwargs
                    )

            fake_update = Update(update.update_id)
            fake_update._effective_message = FakeMessage(
                query.message.chat_id, context.bot
            )

            await _collect_from_platform(fake_update, service, platform)
