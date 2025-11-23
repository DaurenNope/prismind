"""Telegram bot integration for BEYONDLINES."""

import asyncio
import html
import json
import logging
import math
import os
import time
from datetime import time as dt_time
from typing import Dict, List, Optional, Set

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from src.domain.intelligence.agents.github_research_agent import get_github_agent
from src.domain.intelligence.agents.librarian_book_agent import get_librarian
from src.core.discovery.deep_discovery import DeepDiscovery
from src.domain.publishing.modular_rewriter import get_rewriter

# Local imports
from src.infrastructure.database.scrape_state_manager import state_manager
from src.services.automation import IntelligenceAutomation
from src.services.digest import DigestGenerator
from src.services.health import get_health_monitor
from src.services.new_database_manager import get_database_manager

# Import agent command handlers
from src.services.telegram_bot_agents_extension import (
    get_book_command,
    library_command,
    personas_command,
    research_repo_command,
    rewrite_command,
)
from src.services.telegram_formatting import format_post_stats, format_posts_list
from src.shared.utils.duplicate_detector import get_duplicate_detector

LOGGER = logging.getLogger(__name__)

load_dotenv()


def _parse_allowed_user_ids(raw: str) -> Set[int]:
    allowed: Set[int] = set()
    if not raw:
        return allowed
    for part in raw.replace(";", ",").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            allowed.add(int(part))
        except ValueError:
            logger.error(f"Error: {e}")
            LOGGER.warning("Ignoring invalid TELEGRAM_ALLOWED_USER_IDS entry: %s", part)
    return allowed


def _load_access_controls() -> tuple[Set[int], int]:
    allowed_ids = _parse_allowed_user_ids(os.getenv("TELEGRAM_ALLOWED_USER_IDS", ""))
    try:
        cooldown = int(os.getenv("TELEGRAM_COMMAND_COOLDOWN", "15"))
    except ValueError as e:
        logger.error(f"Error parsing cooldown: {e}")
        cooldown = 15
    return allowed_ids, max(0, cooldown)


ALLOWED_USER_IDS, COMMAND_COOLDOWN_SECONDS = _load_access_controls()
_USER_LAST_COMMAND: Dict[int, float] = {}
VALID_PLATFORMS = {"twitter", "reddit", "threads"}

# Global automation instance
_automation_instance = None


def _get_bot_token() -> str:
    # Load variables from .env if present
    load_dotenv()
    token: Optional[str] = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is not set. Export it in your environment or .env."
        )
    return token


async def _ensure_access(update: Update) -> bool:
    """Verify allowlist and cooldown constraints for a command."""
    message = update.effective_message
    user = update.effective_user

    if ALLOWED_USER_IDS and (not user or user.id not in ALLOWED_USER_IDS):
        if message:
            await message.reply_text("❌ You are not authorized to use this bot.")
        LOGGER.warning(
            "Unauthorized access attempt from user %s", getattr(user, "id", "unknown")
        )
        return False

    if not user:
        return True

    if COMMAND_COOLDOWN_SECONDS > 0:
        now = time.time()
        last = _USER_LAST_COMMAND.get(user.id, 0.0)
        remaining = COMMAND_COOLDOWN_SECONDS - (now - last)
        if remaining > 0:
            if message:
                await message.reply_text(
                    f"⏳ Slow down — try again in {int(math.ceil(remaining))}s."
                )
            return False
        _USER_LAST_COMMAND[user.id] = now

    return True


async def _cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _ensure_access(update):
        return

    # Modern welcome message with emojis
    msg = (
        "╔═══════════════════════════╗\n"
        "║   🧠 <b>BEYONDLINES AI</b>   ║\n"
        "╚═══════════════════════════╝\n\n"
        "✨ <b>Your Autonomous Intelligence Companion</b>\n\n"
        "🎯 <b>Quick Start:</b>\n"
        "Tap a button below to begin, or use commands\n\n"
        "💡 <b>What I do:</b>\n"
        "• 📥 Collect your bookmarks\n"
        "• 🤖 Analyze with AI\n"
        "• 🔬 Research topics automatically\n"
        "• 📚 Curate personalized content\n"
        "• 🌐 Discover related resources\n\n"
        "Type /help for all commands"
    )

    # Create inline keyboard with main actions
    keyboard = [
        [
            InlineKeyboardButton("📥 Collect", callback_data="action_collect"),
            InlineKeyboardButton("📊 Status", callback_data="action_status"),
        ],
        [
            InlineKeyboardButton("🔬 Research", callback_data="action_research"),
            InlineKeyboardButton("📚 Curate", callback_data="action_curate"),
        ],
        [
            InlineKeyboardButton("⭐ Recommend", callback_data="action_recommend"),
            InlineKeyboardButton("📖 Latest", callback_data="action_latest"),
        ],
        [
            InlineKeyboardButton("❓ Help", callback_data="action_help"),
            InlineKeyboardButton("⚙️ Settings", callback_data="action_env"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        msg, parse_mode=ParseMode.HTML, reply_markup=reply_markup
    )


async def _cmd_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show and manage profiles"""
    if not await _ensure_access(update):
        return

    try:
        from src.core.discovery.profile_manager import ProfileManager

        manager = ProfileManager()

        # If argument provided, switch profile
        if context.args and len(context.args) > 0:
            profile_id = context.args[0].lower()

            if manager.set_active_profile(profile_id):
                profile = manager.get_active_profile()
                await update.message.reply_text(
                    f"✅ Switched to profile: {profile.get('emoji', '📋')} <b>{profile.get('name')}</b>",
                    parse_mode=ParseMode.HTML,
                )
            else:
                await update.message.reply_text(f"❌ Profile '{profile_id}' not found")
            return

        # Show current profile and list all
        active = manager.get_active_profile()
        all_profiles = manager.list_profiles()

        lines = [
            "━━━━━━━━━━━━━━━━━━━━━━━━",
            "👤 <b>YOUR PROFILES</b>",
            "━━━━━━━━━━━━━━━━━━━━━━━━\n",
            f"<b>Active:</b> {active.get('emoji', '📋')} {active.get('name')}\n",
            "<b>Available Profiles:</b>",
        ]

        for p in all_profiles:
            active_mark = "✅" if p["id"] == active.get("id") else "  "
            lines.append(
                f"{active_mark} {p['emoji']} <b>{p['name']}</b> ({p['topic_count']} topics)"
            )

        lines.append(
            f"\n━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💡 Switch: /profile [id]\n"
            f"📊 Details: /profile_info [id]"
        )

        await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)

    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text(f"Error: {e}")


async def _cmd_topics(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show tracked topics for current profile"""
    if not await _ensure_access(update):
        return

    try:
        from src.core.discovery.profile_manager import ProfileManager

        manager = ProfileManager()
        summary = manager.get_summary()

        await update.message.reply_text(summary, parse_mode=ParseMode.HTML)

    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text(f"Error showing topics: {e}")


async def _cmd_discover_new(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """COMPREHENSIVE intelligence gathering from all sources"""
    if not await _ensure_access(update):
        return

    try:
        from src.core.discovery.comprehensive_discovery import ComprehensiveDiscovery

        progress_msg = await update.message.reply_text(
            "🚀 <b>COMPREHENSIVE DISCOVERY STARTED</b>\n\n"
            "Searching across:\n"
            "• GitHub trending repositories\n"
            "• Reddit (10+ subreddits)\n"
            "• RSS feeds (tech news)\n"
            "• Research analysis\n"
            "• AI curation\n\n"
            "⏳ This may take 1-2 minutes...",
            parse_mode=ParseMode.HTML,
        )

        # Run comprehensive discovery
        discovery = ComprehensiveDiscovery()
        report = await discovery.comprehensive_discovery(max_per_source=30)

        # Save discovered posts to database with source='discovered'
        discovered = report.get("discovered_posts", [])
        try:
            db = get_database_manager()
            saved_count = 0

            for item in discovered[:30]:  # Save top 30
                # Handle both dict and object
                post = item.get("post") if isinstance(item, dict) else item
                if post and hasattr(post, "post_id"):
                    # Check if already exists
                    existing = db.get_post_by_id(post.post_id)
                    if not existing:
                        # Mark as discovered content
                        if hasattr(post, "metadata"):
                            if isinstance(post.metadata, dict):
                                post.metadata["source"] = "discovered"
                            else:
                                post.metadata = {"source": "discovered"}

                        db.add_post(post)
                        saved_count += 1

            if saved_count > 0:
                logger.info(f"   💾 Saved {saved_count} discovered posts to database")
        except Exception as e:
            logger.error(f"   ⚠️ Failed to save to database: {e}")

        # Build comprehensive report
        curated = report.get("curated", {})
        research = report.get("research", {})
        sources = report.get("sources", {})

        lines = [
            "╔═══════════════════════════╗",
            "║ 🎯 <b>INTELLIGENCE REPORT</b> ║",
            "╚═══════════════════════════╝\n",
            f"📊 <b>Discovery Stats:</b>",
            f"   Total found: {report.get('total_discovered', 0)}",
            f"   High-quality: {report.get('high_quality', 0)}\n",
            f"📦 <b>Sources:</b>",
        ]

        for source, count in sources.items():
            lines.append(f"   {source.title()}: {count}")

        lines.append(f"\n📚 <b>Curated Collections:</b>")
        lines.append(f"   🔥 Must-read: {len(curated.get('must_read', []))}")
        lines.append(f"   ⭐ Interesting: {len(curated.get('interesting', []))}")

        # Show trending topics
        if "trending_topics" in research:
            lines.append(f"\n🔥 <b>Trending Topics:</b>")
            for topic_name, data in research["trending_topics"][:3]:
                lines.append(f"   • {topic_name}: {data['count']} mentions")

        # Store discovered posts temporarily for viewing
        import json

        context.user_data["discovered_posts"] = [
            {
                "post_id": item["post"].post_id,
                "platform": item["post"].platform,
                "author": item["post"].author,
                "content": item["post"].content,
                "url": item["post"].url,
                "quality": item.get("quality_score", 0),
                "topics": [t["topic_name"] for t in item.get("topics", [])[:2]],
            }
            for item in discovered[:20]  # Store top 20
        ]

        # Show top 5 must-reads with buttons
        lines.append(f"\n\n🔥 <b>TOP MUST-READS:</b>\n")

        keyboard_buttons = []

        for i, item in enumerate(curated.get("must_read", [])[:5], 1):
            post = item["post"]
            quality = item.get("quality_score", 0)
            topics = item.get("topics", [])
            ai_summary = item.get("ai_summary", "")

            topic_names = ", ".join([t["topic_name"] for t in topics[:2]])

            # Use AI summary if available, otherwise content preview
            if ai_summary and len(ai_summary) > 20:
                display = ai_summary
            else:
                display = post.content[:200].replace("\n", " ")
                if len(post.content) > 200:
                    display += "..."

            lines.append(
                f"{i}. [{post.platform.upper()}] <b>{html.escape(post.author)}</b>\n"
                f"   💡 {html.escape(display)}\n"
                f"   📊 {quality:.2f} | 🎯 {topic_names}\n"
            )

            # Add button to view full post
            keyboard_buttons.append(
                [
                    InlineKeyboardButton(
                        f"📖 Read #{i}", callback_data=f"read_discovered_{i - 1}"
                    ),
                    InlineKeyboardButton(f"🔗 Open", url=post.url) if post.url else None,
                ]
            )

        # Filter out None buttons
        keyboard_buttons = [[btn for btn in row if btn] for row in keyboard_buttons]

        # Show stats
        stats = report.get("stats", {})
        lines.append(
            f"\n━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📈 Today: {stats.get('discovered_today', 0)}/{stats.get('max_daily', 50)}\n"
            f"💡 Use /analyze to process all discoveries"
        )

        await progress_msg.edit_text("\n".join(lines), parse_mode=ParseMode.HTML)

    except Exception as e:
        logger.error(f"Error: {e}")
        LOGGER.exception("Active discovery failed")
        await update.message.reply_text(f"Discovery error: {e}")


async def _cmd_discover(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Run discovery on existing bookmarked posts"""
    if not await _ensure_access(update):
        return

    try:
        from src.core.discovery.discovery_engine import DiscoveryEngine
        from src.services.new_database_manager import get_database_manager

        await update.message.reply_text("🔍 Running autonomous discovery...")

        # Get recent posts
        db = get_database_manager()
        posts_data = db.get_posts(limit=100)

        # Convert to SocialPost objects
        from datetime import datetime

        from src.domain.collection.extractors.social_extractor_base import SocialPost

        posts = []
        for p in posts_data:
            try:
                posts.append(
                    SocialPost(
                        post_id=p.get("id") or p.get("post_id"),
                        platform=p.get("platform", "unknown"),
                        author=p.get("author", "Unknown"),
                        author_handle=p.get("author", "Unknown"),
                        content=p.get("content", ""),
                        url=p.get("url", ""),
                        created_at=datetime.fromisoformat(p["created_at"])
                        if p.get("created_at")
                        else datetime.now(),
                        post_type=p.get("post_type", "post"),
                    )
                )
            except Exception as e:
                logger.debug(f"Failed to parse post {p.get('id')}: {e}")
                continue

        # Run discovery
        engine = DiscoveryEngine()

        # Get value scores if available
        value_scores = {
            p.get("id"): p.get("value_score", 0)
            for p in posts_data
            if p.get("value_score")
        }

        discovered = engine.discover_from_posts(posts, value_scores)

        # Show results
        lines = [
            "━━━━━━━━━━━━━━━━━━━━━━━━",
            "✨ <b>DISCOVERY RESULTS</b>",
            "━━━━━━━━━━━━━━━━━━━━━━━━\n",
        ]

        if discovered:
            lines.append(f"Found <b>{len(discovered)}</b> high-quality posts:\n")

            for i, item in enumerate(discovered[:5], 1):
                post = item["post"]
                topics = item["topics"]
                quality = item.get("quality_score", 0)

                topic_names = ", ".join([t["topic_name"] for t in topics[:2]])
                content_preview = post.content[:80].replace("\n", " ")

                lines.append(
                    f"{i}. {post.author}\n"
                    f"   {content_preview}...\n"
                    f"   📊 Quality: {quality:.2f} | 🎯 {topic_names}\n"
                )

            if len(discovered) > 5:
                lines.append(f"\n...and {len(discovered) - 5} more\n")
        else:
            lines.append("No high-quality posts found in recent content.")

        # Show stats
        stats = engine.get_discovery_stats()
        lines.append(
            f"\n━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📈 Today: {stats['discovered_today']}/{stats['max_daily']}\n"
            f"🎯 Remaining: {stats['remaining']}"
        )

        await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)

    except Exception as e:
        logger.error(f"Error: {e}")
        LOGGER.exception("Discovery failed")
        await update.message.reply_text(f"Discovery error: {e}")


async def _cmd_automate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Control autonomous automation"""
    if not await _ensure_access(update):
        return

    global _automation_instance

    args = context.args or []
    if not args:
        await update.message.reply_text(
            "🤖 <b>Automation Control</b>\n\n"
            "Usage:\n"
            "/automate start - Start autonomous scheduler\n"
            "/automate stop - Stop scheduler\n"
            "/automate status - Show status\n"
            "/automate run [profile] - Run discovery now\n\n"
            "Schedule:\n"
            "• 6 AM: Work profile\n"
            "• 10 AM: Startup profile\n"
            "• 2 PM: Learning profile\n"
            "• 6 PM: Trends profile\n"
            "• 10 PM: Work prep",
            parse_mode=ParseMode.HTML,
        )
        return

    command = args[0].lower()

    if command == "start":
        if _automation_instance and _automation_instance.scheduler.running:
            await update.message.reply_text("✅ Scheduler already running!")
            return

        _automation_instance = IntelligenceAutomation()
        _automation_instance.start(mode="rotation")

        await update.message.reply_text(
            "🚀 <b>Autonomous Scheduler Started!</b>\n\n"
            "Discovery will run automatically:\n"
            "• Every 4 hours\n"
            "• Rotating through profiles\n"
            "• Saving discoveries to database\n\n"
            "Use /scheduler_status to monitor",
            parse_mode=ParseMode.HTML,
        )

    elif command == "stop":
        if not _automation_instance or not _automation_instance.scheduler.running:
            await update.message.reply_text("⚠️ Scheduler not running")
            return

        _automation_instance.stop()
        await update.message.reply_text("🛑 Scheduler stopped")

    elif command == "status":
        await _cmd_scheduler_status(update, context)

    elif command == "run":
        profile_id = args[1] if len(args) > 1 else "work"

        msg = await update.message.reply_text(
            f"🔄 Running discovery for {profile_id} profile..."
        )

        automation = IntelligenceAutomation()
        result = await automation.scheduled_discovery(profile_id)

        if result["status"] == "success":
            await msg.edit_text(
                f"✅ <b>Discovery Complete</b>\n\n"
                f"Profile: {result['profile']}\n"
                f"Discovered: {result['discovered']}\n"
                f"High-quality: {result['high_quality']}\n"
                f"Saved: {result['saved']}\n"
                f"Avg quality: {result['avg_quality']:.2f}",
                parse_mode=ParseMode.HTML,
            )
        else:
            await msg.edit_text(f"❌ Error: {result['error']}")


async def _cmd_scheduler_status(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Show scheduler status"""
    if not await _ensure_access(update):
        return

    global _automation_instance

    if not _automation_instance:
        await update.message.reply_text(
            "⚪ <b>Scheduler Status: Not Started</b>\n\nUse /automate start to begin",
            parse_mode=ParseMode.HTML,
        )
        return

    status = _automation_instance.get_status()
    metrics = status["metrics"]
    jobs = status["scheduled_jobs"]

    lines = [
        "🤖 <b>Scheduler Status</b>",
        "━━━━━━━━━━━━━━━━━━━━━━━━\n",
        f"Status: {'🟢 Running' if status['running'] else '🔴 Stopped'}",
        f"Total runs: {metrics['total_runs']}",
        f"Successful: {metrics['successful_runs']}",
        f"Failed: {metrics['failed_runs']}",
        f"Discoveries: {metrics['total_discoveries']}",
        f"Avg quality: {metrics['avg_quality']:.2f}\n",
    ]

    if metrics["last_run"]:
        lines.append(f"Last run: {metrics['last_run']}\n")

    if jobs:
        lines.append("<b>Scheduled Jobs:</b>")
        for job in jobs[:5]:
            lines.append(f"• {job['name']}")
            if job["next_run"]:
                lines.append(f"  Next: {job['next_run']}")

    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


async def _cmd_collections(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show thematic collections"""
    if not await _ensure_access(update):
        return

    msg = await update.message.reply_text("📚 Curating collections...")

    try:
        db = get_database_manager()
        librarian = EnhancedLibrarianAgent(db)

        # Get recent posts
        posts = db.get_posts(limit=100)

        # Convert to format librarian expects
        post_items = [
            {
                "post": post,
                "quality_score": post.quality_score
                if hasattr(post, "quality_score")
                else 0.5,
                "topics": [],
            }
            for post in posts
        ]

        # Curate
        curated = await librarian.curate_content(post_items)

        lines = ["📚 <b>THEMATIC COLLECTIONS</b>", "━━━━━━━━━━━━━━━━━━━━━━━━\n"]

        # Show collections
        if curated["collections"]:
            for name, items in curated["collections"].items():
                emoji = {
                    "ai_breakthroughs": "🧠",
                    "startup_stories": "🚀",
                    "dev_tools": "🛠️",
                    "learning_resources": "📚",
                    "industry_news": "📈",
                }.get(name, "📦")

                display_name = name.replace("_", " ").title()
                lines.append(f"{emoji} <b>{display_name}</b>: {len(items)} items")
        else:
            lines.append("No collections yet. Run /discover_new first!")

        lines.append(f"\n📊 <b>By Format:</b>")
        for format_type, items in curated["by_format"].items():
            lines.append(f"• {format_type}: {len(items)}")

        lines.append(f"\n🎯 <b>Curation Stats:</b>")
        lines.append(f"Must-read: {len(curated['must_read'])}")
        lines.append(f"Interesting: {len(curated['interesting'])}")
        lines.append(f"Quick reads: {len(curated['quick_reads'])}")
        lines.append(f"Deep dives: {len(curated['deep_dives'])}")

        await msg.edit_text("\n".join(lines), parse_mode=ParseMode.HTML)

    except Exception as e:
        logger.error(f"Error: {e}")
        await msg.edit_text(f"❌ Error: {e}")


async def _cmd_reading_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Create or view reading lists"""
    if not await _ensure_access(update):
        return

    args = context.args or []

    if not args:
        await update.message.reply_text(
            "📖 <b>Reading Lists</b>\n\n"
            "Usage:\n"
            "/reading_list create [name] - Create new list\n"
            "/reading_list show - Show all lists\n"
            "/reading_list ai - AI & ML reading list\n"
            "/reading_list startup - Startup reading list",
            parse_mode=ParseMode.HTML,
        )
        return

    command = args[0].lower()

    if command == "ai":
        # Create AI reading list
        msg = await update.message.reply_text("📚 Curating AI reading list...")

        db = get_database_manager()
        librarian = EnhancedLibrarianAgent(db)

        # Get AI-related posts
        posts = db.get_posts(limit=100)
        ai_posts = [
            {"post": p, "quality_score": 0.7}
            for p in posts
            if hasattr(p, "content")
            and any(
                word in p.content.lower()
                for word in ["ai", "machine learning", "llm", "gpt", "claude", "neural"]
            )
        ]

        reading_list = await librarian.create_reading_list(
            "AI & Machine Learning", ai_posts[:20], "Essential AI and ML content"
        )

        await msg.edit_text(
            f"📖 <b>Reading List Created</b>\n\n"
            f"Name: {reading_list['name']}\n"
            f"Items: {reading_list['progress']['total']}\n"
            f"Status: Ready to read\n\n"
            f"Use /latest to view items",
            parse_mode=ParseMode.HTML,
        )

    else:
        await update.message.reply_text("Feature coming soon!")


async def _cmd_digest(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate thematic digest"""
    if not await _ensure_access(update):
        return

    args = context.args or []
    theme = " ".join(args) if args else "This Week in Tech"

    msg = await update.message.reply_text(f"📬 Generating digest: {theme}...")

    try:
        db = get_database_manager()
        librarian = EnhancedLibrarianAgent(db)

        # Get recent posts
        posts = db.get_posts(limit=50)
        post_items = [
            {
                "post": post,
                "quality_score": post.quality_score
                if hasattr(post, "quality_score")
                else 0.5,
                "topics": [],
            }
            for post in posts
        ]

        # Generate digest
        digest = await librarian.create_thematic_digest(theme, post_items)

        # Send as text (might be long)
        await msg.edit_text(f"<pre>{digest}</pre>", parse_mode=ParseMode.HTML)

    except Exception as e:
        logger.error(f"Error: {e}")
        await msg.edit_text(f"❌ Error: {e}")


async def _cmd_morning_digest(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Generate and send morning digest"""
    if not await _ensure_access(update):
        return

    msg = await update.message.reply_text("☀️ Generating morning digest...")

    try:
        digest_gen = DigestGenerator()

        # Get profile from args (optional)
        profile = context.args[0] if context.args else None

        # Generate digest
        digest = digest_gen.generate_morning_digest(profile)

        # Format for Telegram
        telegram_text = digest_gen.format_for_telegram(digest)

        await msg.edit_text(telegram_text, parse_mode=ParseMode.HTML)

    except Exception as e:
        logger.error(f"Error: {e}")
        LOGGER.exception("Morning digest failed")
        await msg.edit_text(f"❌ Error: {e}")


async def _cmd_evening_summary(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Generate and send evening summary"""
    if not await _ensure_access(update):
        return

    msg = await update.message.reply_text("🌙 Generating evening summary...")

    try:
        digest_gen = DigestGenerator()

        # Generate summary
        summary = digest_gen.generate_evening_summary()

        # Format for Telegram
        telegram_text = digest_gen.format_for_telegram(summary)

        await msg.edit_text(telegram_text, parse_mode=ParseMode.HTML)

    except Exception as e:
        logger.error(f"Error: {e}")
        LOGGER.exception("Evening summary failed")
        await msg.edit_text(f"❌ Error: {e}")


async def _cmd_health(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show system health status"""
    if not await _ensure_access(update):
        return

    msg = await update.message.reply_text("🏥 Checking system health...")

    try:
        monitor = get_health_monitor()
        health = monitor.get_system_health()

        # Format for Telegram
        lines = [
            "🏥 <b>SYSTEM HEALTH</b>",
            "━━━━━━━━━━━━━━━━━━━━━━━━\n",
            f"Status: {health['status'].upper()}",
            f"Uptime: {health['uptime']}\n",
            "<b>Components:</b>",
        ]

        for name, comp in health["components"].items():
            emoji = "✅" if comp["status"] == "healthy" else "⚠️"
            lines.append(f"{emoji} {name.replace('_', ' ').title()}")

        perf = health["performance"]
        lines.append(f"\n<b>Performance:</b>")
        lines.append(f"CPU: {perf['cpu']['percent']}%")
        lines.append(f"Memory: {perf['memory']['percent']}%")
        lines.append(f"Disk: {perf['disk']['percent']}% used")

        db = health["database"]
        if db["status"] == "healthy":
            lines.append(f"\n<b>Database:</b>")
            lines.append(f"Total: {db['total_posts']} posts")
            lines.append(f"Last 24h: {db['last_24h']} new")

        if health["alerts"]:
            lines.append(f"\n⚠️ <b>Alerts:</b>")
            for alert in health["alerts"]:
                lines.append(f"• {alert}")

        await msg.edit_text("\n".join(lines), parse_mode=ParseMode.HTML)

    except Exception as e:
        logger.error(f"Error: {e}")
        await msg.edit_text(f"❌ Health check error: {e}")


async def _cmd_deep_research(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Run deep research on a topic (10-15 minutes)"""
    if not await _ensure_access(update):
        return

    args = context.args or []

    if not args:
        await update.message.reply_text(
            "🔬 <b>Deep Research Mode</b>\n\n"
            "Usage: /research [topic]\n\n"
            "Examples:\n"
            "• /research AI Agents\n"
            "• /research Startup Funding\n"
            "• /research React 19\n\n"
            "⏱️  Deep research takes 10-15 minutes\n"
            "   for thorough multi-source analysis",
            parse_mode=ParseMode.HTML,
        )
        return

    topic = " ".join(args)

    msg = await update.message.reply_text(
        f"🔬 <b>Starting Deep Research: {topic}</b>\n\n"
        f"⏱️  This will take 10-15 minutes...\n\n"
        f"📊 Phase 1: Multi-source gathering (5 min)\n"
        f"🧠 Phase 2: Context analysis (5 min)\n"
        f"📝 Phase 3: Briefing synthesis (5 min)\n\n"
        f"I'll send updates as we progress...",
        parse_mode=ParseMode.HTML,
    )

    try:
        # Create deep discovery instance
        deep = DeepDiscovery()

        # Send progress update
        await msg.edit_text(
            f"🔬 <b>Deep Research: {topic}</b>\n\n📊 Gathering sources (2-3 min)...",
            parse_mode=ParseMode.HTML,
        )

        # Run research (this takes time!)
        briefing = deep.research_topic(topic, profile_id="work")

        # Format results for Telegram
        lines = [
            f"🔬 <b>Deep Research: {topic}</b>",
            "━━━━━━━━━━━━━━━━━━━━━━━━\n",
            f"⏱️  Duration: {briefing['duration_seconds']:.0f}s",
            f"📊 Sources: {briefing['total_sources']}",
            f"⭐ High Quality: {briefing['high_quality']}\n",
            "<b>Summary:</b>",
            briefing["summary"] + "\n",
        ]

        # Add context
        if briefing.get("context"):
            ctx = briefing["context"]
            lines.append("<b>Context:</b>")
            lines.append(f"• Sentiment: {ctx['sentiment']}")
            lines.append(f"• Why it matters: {ctx['why_this_matters']}\n")

        # Add trends
        if briefing.get("trends"):
            trends = briefing["trends"]
            lines.append("<b>Trends:</b>")
            lines.append(f"• Direction: {trends['direction']}")
            lines.append(f"• Momentum: {trends['momentum']}")
            lines.append(f"• {trends['prediction']}\n")

        # Add experts
        if briefing.get("experts") and len(briefing["experts"]) > 0:
            lines.append("<b>Key Voices:</b>")
            for expert in briefing["experts"][:3]:
                lines.append(f"• {expert['author']} ({expert['posts']} posts)")

        lines.append(f"\n━━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append("Use /latest to view discovered posts")

        await msg.edit_text("\n".join(lines), parse_mode=ParseMode.HTML)

    except Exception as e:
        logger.error(f"Error: {e}")
        LOGGER.exception("Deep research failed")
        await msg.edit_text(
            f"❌ Research error: {e}\n\n"
            f"Try /discover_new for quick mode or a simpler topic"
        )


async def _cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _ensure_access(update):
        return

    help_msg = (
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "📖 <b>COMMAND REFERENCE</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "┌─ 📥 <b>COLLECTION</b>\n"
        "├ /collect → Full autonomous pipeline\n"
        "├ /status → View statistics\n"
        "└ /latest [N] [platform] → Browse posts\n\n"
        "┌─ 🧠 <b>INTELLIGENCE</b>\n"
        "├ /analyze [N] → AI analysis\n"
        "├ /ask <query> → Research question\n"
        "├ /research [N] → Auto-research topics\n"
        "├ /recommend → Top content\n"
        "└ /curate → Personalized library\n\n"
        "┌─ 📊 <b>INSIGHTS</b>\n"
        "└ /insight <id> → Detailed analysis\n\n"
        "┌─ ⚙️ <b>SYSTEM</b>\n"
        "├ /env → Configuration\n"
        "├ /schedule daily <HH:MM> → Schedule daily collection\n"
        "├ /schedule off → Disable scheduled collection\n"
        "└ /help → This message\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "💫 <b>AUTONOMOUS FEATURES</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "✓ Auto-analyzes new content\n"
        "✓ Researches high-value topics\n"
        "✓ Discovers related resources\n"
        "✓ Learns your preferences\n"
        "✓ Curates smart collections\n\n"
        "🎯 <i>Tap /start for quick actions</i>"
    )

    keyboard = [
        [InlineKeyboardButton("🏠 Home", callback_data="action_start")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        help_msg, parse_mode=ParseMode.HTML, reply_markup=reply_markup
    )


async def _cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _ensure_access(update):
        return
    try:
        stats = state_manager.get_scraping_stats()
        total = stats.get("total_posts", 0)

        lines = [
            "━━━━━━━━━━━━━━━━━━━━━━━━",
            "📊 <b>SYSTEM STATISTICS</b>",
            "━━━━━━━━━━━━━━━━━━━━━━━━\n",
            f"🗄️ <b>Total Content:</b> {total:,} posts\n",
        ]

        # Platform breakdown with emojis
        platform_emojis = {"twitter": "🐦", "reddit": "🤖", "threads": "🧵"}

        lines.append("<b>Platform Breakdown:</b>")
        for platform_stat in stats.get("platform_stats", []):
            platform = platform_stat.get("platform", "-")
            count = platform_stat.get("total_posts_scraped", 0)
            emoji = platform_emojis.get(platform.lower(), "📌")
            percentage = (count / total * 100) if total > 0 else 0
            bar_length = int(percentage / 10)
            bar = "▰" * bar_length + "▱" * (10 - bar_length)
            lines.append(f"{emoji} <b>{platform.title()}</b>: {count:,} posts")
            lines.append(f"   {bar} {percentage:.1f}%\n")

        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append("<i>Use /latest to browse content</i>")

        text = "\n".join(lines)

        keyboard = [
            [
                InlineKeyboardButton("📥 Collect More", callback_data="action_collect"),
                InlineKeyboardButton("📖 Latest", callback_data="action_latest"),
            ],
            [InlineKeyboardButton("🏠 Home", callback_data="action_start")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            text, parse_mode=ParseMode.HTML, reply_markup=reply_markup
        )
    except Exception as exc:  # pylint: disable=broad-except
        logger.error(f"Error: {e}")
        LOGGER.exception("Failed to get status: %s", exc)
        await update.message.reply_text(f"❌ Status error: {exc}")


async def _cmd_collect(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Trigger the multi-platform collection orchestrator and report results."""
    if not await _ensure_access(update):
        return

    message = update.effective_message
    if not message:
        return

    # Show animated progress message
    progress_msg = await message.reply_text(
        "╔═══════════════════════════╗\n"
        "║  🚀 <b>COLLECTION STARTED</b>  ║\n"
        "╚═══════════════════════════╝\n\n"
        "⏳ <i>Starting collection...</i>",
        parse_mode=ParseMode.HTML,
    )

    # Track progress
    import time

    start_time = time.time()
    platform_status = {"twitter": "⏳", "reddit": "⏳", "threads": "⏳"}
    platform_counts = {"twitter": 0, "reddit": 0, "threads": 0}

    async def update_progress(platform: str, msg: str, counts: dict):
        """Update progress message with live status"""
        try:
            elapsed = int(time.time() - start_time)

            # Update status emoji
            if "Collected" in msg or "done" in msg.lower():
                platform_status[platform] = "✅"
            elif "Error" in msg:
                platform_status[platform] = "❌"
            else:
                platform_status[platform] = "🔄"

            # Update counts
            platform_counts.update(counts)

            # Build message
            lines = [
                "╔═══════════════════════════╗",
                "║  🚀 <b>COLLECTION RUNNING</b> ║",
                "╚═══════════════════════════╝\n",
                f"⏱️ <b>Time:</b> {elapsed}s\n",
            ]

            for plat in ["twitter", "reddit", "threads"]:
                emoji = platform_status[plat]
                count = platform_counts.get(plat, 0)
                lines.append(f"{emoji} <b>{plat.title()}:</b> {count} posts")

            lines.append(f"\n💬 <i>{msg}</i>")

            await progress_msg.edit_text("\n".join(lines), parse_mode=ParseMode.HTML)
        except Exception as e:
            logger.error(f"Error: {e}")
            pass  # Ignore edit errors

    try:
        # Use new orchestrator API
        from src.application.automation.orchestrator import get_orchestrator

        orch = get_orchestrator()
        # Only bookmark platforms via /collect; RSS is discovery mode, not part of /collect
        results = await orch.collect_all(platforms=["twitter", "reddit", "threads"])
        total = results.get("total", 0)
        twitter_count = results.get("twitter", 0)
        reddit_count = results.get("reddit", 0)
        threads_count = results.get("threads", 0)
        errors = results.get("errors", [])
        intelligence = results.get("intelligence", {})

        lines = [
            "╔═══════════════════════════╗",
            "║  ✅ <b>COLLECTION COMPLETE</b> ║",
            "╚═══════════════════════════╝\n",
            f"📊 <b>Total New Content:</b> {total} items\n",
            "<b>Platform Breakdown:</b>",
        ]

        # Platform results with emojis
        if twitter_count > 0:
            lines.append(f"🐦 <b>Twitter:</b> {twitter_count} posts")
        if reddit_count > 0:
            lines.append(f"🤖 <b>Reddit:</b> {reddit_count} posts")
        if threads_count > 0:
            lines.append(f"🧵 <b>Threads:</b> {threads_count} posts")

        if total == 0:
            lines.append("\n<i>No new content found</i>")

        # Intelligence results
        if intelligence:
            analyzed = intelligence.get("analyzed", 0)
            researched = intelligence.get("researched", 0)
            lines.append(f"\n🧠 <b>Intelligence:</b>")
            if analyzed > 0:
                lines.append(f"  • {analyzed} items analyzed with AI")
            if researched > 0:
                lines.append(f"  • {researched} topics researched")

        if errors:
            lines.append(f"\n⚠️ <b>Errors ({len(errors)}):</b>")
            for err in errors[:3]:
                lines.append(f"  • {html.escape(str(err)[:60])}")
            if len(errors) > 3:
                lines.append(f"  <i>... and {len(errors) - 3} more</i>")

        lines.append("\n━━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append("💡 <i>Use /latest to browse content</i>")

        keyboard = [
            [
                InlineKeyboardButton("📖 Browse", callback_data="action_latest"),
                InlineKeyboardButton("⭐ Recommend", callback_data="action_recommend"),
            ],
            [
                InlineKeyboardButton("🔬 Research", callback_data="action_research"),
                InlineKeyboardButton("📚 Curate", callback_data="action_curate"),
            ],
            [InlineKeyboardButton("🏠 Home", callback_data="action_start")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await progress_msg.edit_text(
            "\n".join(lines), parse_mode=ParseMode.HTML, reply_markup=reply_markup
        )

        # Per-platform summaries in a digestible news format
        try:
            feed = await orch.build_news_feed(limit=30)
            platforms = [
                p for p in ("twitter", "reddit", "threads") if results.get(p, 0) > 0
            ]
            for platform in platforms:
                items = [
                    i for i in feed if (i.get("platform") or "").lower() == platform
                ]
                if not items:
                    continue
                header = f"Here is the summary for {platform.capitalize()}:"
                parts = [header, ""]
                for idx, it in enumerate(items[:5], start=1):
                    title = it.get("title") or "Untitled"
                    url = it.get("url") or ""
                    summary = it.get("summary") or ""
                    # Build compact bullet with title and link; summary optional
                    line = (
                        f'{idx}. <a href="{html.escape(url)}">{html.escape(title)}</a>'
                    )
                    if summary:
                        line += f"\n   <i>{html.escape(summary[:180])}</i>"
                    parts.append(line)
                text = "\n\n".join(parts)
                await message.reply_text(
                    text, parse_mode=ParseMode.HTML, disable_web_page_preview=True
                )
        except Exception as e:
            logger.error(f"Error: {e}")
            # Non-fatal; skip summaries if any error occurs
            pass

    except Exception as exc:  # pylint: disable=broad-except
        logger.error(f"Error: {e}")
        LOGGER.exception("Collection failed: %s", exc)
        await message.reply_text(
            "━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "❌ <b>COLLECTION ERROR</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"<code>{html.escape(str(exc))}</code>\n\n"
            "<i>Try again or contact support</i>",
            parse_mode=ParseMode.HTML,
        )


async def _job_collect(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Background job to run collection and send a brief summary."""
    chat_id = context.job.chat_id if context.job else None
    try:
        from src.domain.collection.services.collection_orchestrator import run_full_collection

        results = await run_full_collection()
        total = results.get("total", 0)
        twitter_count = results.get("twitter", 0)
        reddit_count = results.get("reddit", 0)
        threads_count = results.get("threads", 0)
        msg = (
            "🗓️ Scheduled collection complete\n\n"
            f"Total: <b>{total}</b>\n"
            f"🐦 Twitter: {twitter_count} | 🤖 Reddit: {reddit_count} | 🧵 Threads: {threads_count}"
        )
        if chat_id:
            await context.bot.send_message(
                chat_id=chat_id, text=msg, parse_mode=ParseMode.HTML
            )
    except Exception as exc:  # pylint: disable=broad-except
        logger.error(f"Error: {e}")
        if chat_id:
            await context.bot.send_message(
                chat_id=chat_id, text=f"Scheduled collection error: {exc}"
            )


async def _cmd_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Schedule or cancel automated daily collection.
    Usage:
      /schedule daily HH:MM   -> run once per day at that time (server time)
      /schedule off           -> cancel existing scheduled job
    """
    if not await _ensure_access(update):
        return

    message = update.effective_message
    args = context.args or []
    if not args:
        await message.reply_text("Usage: /schedule daily <HH:MM> or /schedule off")
        return

    # Cancel
    if args[0].lower() == "off":
        removed = 0
        for job in list(context.job_queue.jobs()):
            if job.chat_id == update.effective_chat.id:
                job.schedule_removal()
                removed += 1
        await message.reply_text(
            "🛑 Scheduling disabled" if removed else "No schedule to disable."
        )
        return

    # Daily schedule
    if args[0].lower() == "daily":
        if len(args) < 2 or ":" not in args[1]:
            await message.reply_text("Usage: /schedule daily <HH:MM>")
            return
        try:
            hh, mm = args[1].split(":", 1)
            hh_i, mm_i = int(hh), int(mm)
            hh_i = max(0, min(23, hh_i))
            mm_i = max(0, min(59, mm_i))
            run_time = dt_time(hour=hh_i, minute=mm_i)
        except Exception as e:
            logger.error(f"Error: {e}")
            await message.reply_text("Time must be in HH:MM format, e.g., 09:00")
            return

        for job in list(context.job_queue.jobs()):
            if job.chat_id == update.effective_chat.id:
                job.schedule_removal()

        context.job_queue.run_daily(
            _job_collect, run_time, chat_id=update.effective_chat.id
        )
        await message.reply_text(f"✅ Scheduled daily collection at {args[1]}")
        return

    await message.reply_text(
        "Unknown schedule command. Use /schedule daily <HH:MM> or /schedule off"
    )


async def _cmd_analyze(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Run a quick analysis sweep over the most recent posts and summarize."""
    if not await _ensure_access(update):
        return

    message = update.effective_message
    args = context.args or []
    limit = 10
    platform = None

    for arg in args:
        lowered = arg.lower()
        if lowered in VALID_PLATFORMS:
            platform = lowered
        else:
            try:
                limit = int(arg)
            except ValueError:
                logger.error(f"Error: {e}")
                if message:
                    await message.reply_text(
                        "Usage: /analyze [count] [platform] — platform options: twitter, reddit, threads"
                    )
                return

    limit = max(1, min(50, limit))

    if message:
        await message.reply_text("Analyzing recent posts…")
    try:
        # Lazy import to keep bot light
        from src.domain.analysis.services.post_analyzer import analyze_and_store_post, log

        db = get_database_manager()
        platforms_filter = [platform] if platform else None
        # Prefer unanalyzed posts first; fallback to recent posts
        try:
            unanalyzed = db.get_unanalyzed_posts(
                limit=limit, platforms=platforms_filter
            )  # type: ignore[attr-defined]
        except Exception as e:
            logger.error(f"Error: {e}")
            unanalyzed = []
        posts = unanalyzed or db.get_posts(limit=limit, platforms=platforms_filter)

        if not posts:
            if message:
                await message.reply_text("No posts available for analysis.")
            return

        analyzed = 0
        errors: List[str] = []
        for post in posts[:limit]:
            post_id = post.get("post_id") or post.get("id") or "unknown"
            try:
                success = await analyze_and_store_post(db, post, supabase_manager=None)
                if success:
                    analyzed += 1
                else:
                    errors.append(f"{post_id}: storage failed")
            except Exception as inner_exc:  # pylint: disable=broad-except
                logger.error(f"Error: {e}")
                LOGGER.warning("Analyze failed for post %s: %s", post_id, inner_exc)
                errors.append(f"{post_id}: {inner_exc}")

        attempted = min(limit, len(posts))
        lines = [
            f"Analysis complete. Processed <b>{analyzed}</b> of {attempted} posts."
        ]
        if platform:
            lines.append(f"Platform: <b>{platform.title()}</b>")
        if errors:
            lines.append("Errors:")
            for err in errors[:5]:
                lines.append(f"- {html.escape(err)}")
            if len(errors) > 5:
                lines.append(f"- …and {len(errors) - 5} more errors.")
        if message:
            await message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="🔔 Analysis completed.",
            )
        except Exception as e:
            logger.error(f"Error: {e}")
            pass
    except Exception as exc:  # pylint: disable=broad-except
        logger.error(f"Error: {e}")
        LOGGER.exception("Analysis failed: %s", exc)
        await update.message.reply_text(f"Analysis error: {exc}")


async def _cmd_env(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Report presence (not values) of required environment variables."""
    if not await _ensure_access(update):
        return
    load_dotenv()
    keys = [
        "TELEGRAM_BOT_TOKEN",
        "TWITTER_USERNAME",
        "REDDIT_CLIENT_ID",
        "REDDIT_CLIENT_SECRET",
        "REDDIT_USER_AGENT",
        "REDDIT_USERNAME",
        "REDDIT_PASSWORD",
        "REDDIT_ACCESS_TOKEN",
        "THREADS_USERNAME",
        "THREADS_PASSWORD",
    ]
    presence = {k: bool(os.getenv(k)) for k in keys}
    lines = ["🔧 <b>Env vars detected</b>"]
    for k, v in presence.items():
        status = "✅" if v else "❌"
        lines.append(f"{status} {k}")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


async def _cmd_latest(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show recent posts as rich Telegram cards. Usage: /latest [limit] [platform]"""
    if not await _ensure_access(update):
        return
    try:
        args = context.args or []
        limit = 5  # Default to 5 for rich cards
        platform = None
        if args:
            try:
                limit = max(1, min(10, int(args[0])))  # Max 10 for rich display
                if len(args) > 1:
                    platform = args[1].lower()
            except ValueError:
                logger.error(f"Error: {e}")
                platform = args[0].lower()
                if len(args) > 1:
                    try:
                        limit = max(1, min(10, int(args[1])))
                    except ValueError:
                        logger.error(f"Error: {e}")
                        pass

        if platform and platform not in VALID_PLATFORMS:
            await update.effective_message.reply_text(
                "Unknown platform. Use one of: twitter, reddit, threads."
            )
            return

        db = get_database_manager()
        platforms = [platform] if platform else None
        posts = db.get_posts(limit=limit, platforms=platforms)
        if not posts:
            await update.message.reply_text("📭 No recent posts found.")
            return

        # Format posts with enhanced GitHub display
        from datetime import datetime

        today = datetime.now().strftime("%d.%m.%Y")

        header = f"<b>Latest Posts</b> — {today}\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        formatted = format_posts_list(posts)
        footer = f"\n━━━━━━━━━━━━━━━━━━━━━━━━\n{format_post_stats(posts)}"

        message_text = header + formatted + footer
        await update.message.reply_text(message_text, parse_mode=ParseMode.HTML)

    except Exception as exc:  # pylint: disable=broad-except
        logger.error(f"Error: {e}")
        LOGGER.exception("Latest failed: %s", exc)
        await update.message.reply_text(f"Latest error: {exc}")


async def _send_posts_feed(message, posts: list, platform_filter: str = None):
    """Send all posts in one message as a clean, professional feed"""

    from datetime import datetime

    # Get current date for header
    today = datetime.now().strftime("%d.%m.%Y")

    # Clean header
    lines = [f"<b>Latest Posts</b> — {today}", "━━━━━━━━━━━━━━━━━━━━━━━━\n"]

    for i, post in enumerate(posts, 1):
        platform = post.get("platform", "unknown").lower()
        author = post.get("author") or "Unknown"
        raw_content = post.get("content") or post.get("title") or ""
        url = post.get("url", "")
        value_score = post.get("value_score", 0)
        key_concepts = post.get("key_concepts") or []

        # Check for existing AI summary
        ai_summary = post.get("ai_summary") or post.get("content_summary")
        insights = post.get("insights") or post.get("actionable_insights")

        # Parse key_concepts if JSON string
        if isinstance(key_concepts, str):
            try:
                import json as json_lib

                key_concepts = json_lib.loads(key_concepts)
            except (json.JSONDecodeError, TypeError, ValueError) as e:
                logger.debug(f"Failed to parse key_concepts JSON: {e}")
                key_concepts = []

        # Simple platform indicator
        platform_label = {
            "twitter": "Twitter",
            "reddit": "Reddit",
            "threads": "Threads",
        }.get(platform, platform.title())

        # Header: Number, Platform, Author
        lines.append(f"<b>{i}.</b> {platform_label} • {html.escape(author)}")

        # Clean up content and create readable display
        display_text = None

        # Check for AI summary first (make sure it's a string)
        if ai_summary and isinstance(ai_summary, str):
            ai_summary = ai_summary.strip()
            if (
                len(ai_summary) > 10
                and not ai_summary.startswith("{")
                and not ai_summary.startswith("```")
            ):
                display_text = ai_summary

        # Try insights if no summary
        if not display_text and insights and isinstance(insights, str):
            insights = insights.strip()
            if (
                len(insights) > 10
                and not insights.startswith("{")
                and not insights.startswith("```")
            ):
                display_text = f"💡 {insights}"

        # Fall back to raw content if no good summary
        if not display_text and raw_content:
            # Skip if content looks like JSON analysis
            if raw_content.startswith("```json") or raw_content.startswith("{"):
                display_text = (
                    "<i>Content analysis available - use /insight for details</i>"
                )
            else:
                # Clean up the content
                clean_content = (
                    raw_content.replace("\n\n", " ").replace("\n", " ").strip()
                )
                # Remove URLs from display
                import re

                clean_content = re.sub(r"https?://\S+", "", clean_content).strip()

                if len(clean_content) > 250:
                    # Find a good break point at sentence end
                    break_at = clean_content[:250].rfind(". ")
                    if break_at > 100:
                        clean_content = clean_content[: break_at + 1]
                    else:
                        clean_content = clean_content[:247] + "..."
                display_text = clean_content

        # Display the text
        if not display_text or len(display_text.strip()) < 5:
            lines.append("<i>No preview available</i>")
        else:
            if len(display_text) > 280:
                display_text = display_text[:277] + "..."
            lines.append(html.escape(display_text))

        # Value score - only show if high
        if value_score and value_score > 0.7:
            score_text = f"Value: {value_score:.1f}"
            lines.append(f"<i>{score_text}</i>")

        # Tags - clean, minimal
        if key_concepts and isinstance(key_concepts, list) and len(key_concepts) > 0:
            tags = " ".join([f"#{str(c).replace(' ', '_')}" for c in key_concepts[:2]])
            lines.append(f"<i>{tags}</i>")

        # URL at the end
        if url:
            lines.append(f"<a href='{url}'>View Post</a>")

        lines.append("")  # Space between posts

    # Footer
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"Total: <b>{len(posts)}</b> posts")

    # Simple action buttons
    keyboard = [
        [
            InlineKeyboardButton("🔄 Refresh", callback_data="action_latest"),
            InlineKeyboardButton("📥 Collect New", callback_data="action_collect"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        await message.reply_text(
            "\n".join(lines),
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup,
            disable_web_page_preview=True,
        )
    except Exception as e:
        logger.error(f"Error: {e}")
        # Fallback to simple format
        simple_lines = [
            f"{i}. {p.get('author', 'Unknown')}: {(p.get('content') or '')[:80]}..."
            for i, p in enumerate(posts, 1)
        ]
        await message.reply_text(
            "\n\n".join(simple_lines), disable_web_page_preview=True
        )


async def _cmd_insight(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Render an AI insight card for a specific post."""
    if not await _ensure_access(update):
        return

    args = context.args or []
    if not args:
        await update.effective_message.reply_text("Usage: /insight <post_id>")
        return

    post_id = args[0]
    try:
        db = get_database_manager()
        post = db.get_post_by_id(post_id)
        if not post:
            await update.effective_message.reply_text(
                f"No post found with ID {post_id}."
            )
            return

        title = (
            post.get("title")
            or (post.get("content") or "").split("\n")[0][:120]
            or "Untitled"
        )
        platform = (post.get("platform") or "unknown").title()
        author = post.get("author") or "Unknown"
        created_at = (
            post.get("created_at") or post.get("created_timestamp") or "Unknown"
        )
        url = post.get("url") or ""
        value_score = post.get("value_score")
        quality_score = post.get("quality_score")
        summary = (
            post.get("content_summary")
            or post.get("ai_summary")
            or "No summary available."
        )
        if summary and len(summary) > 600:
            summary = summary[:597] + "…"

        key_concepts = post.get("key_concepts") or []
        if isinstance(key_concepts, str):
            key_concepts = [key_concepts]

        tags = post.get("tags") or []
        if isinstance(tags, str):
            tags = [tags]

        insights = post.get("insights") or []
        action_items = post.get("action_items") or []
        recommendations = post.get("recommendations") or []
        sentiment_info = post.get("sentiment_analysis") or {}
        if isinstance(sentiment_info, str):
            try:
                sentiment_info = json.loads(sentiment_info)
            except Exception as e:
                logger.error(f"Error: {e}")
                sentiment_info = {}
        sentiment_label = "Unknown"
        if isinstance(sentiment_info, dict):
            sentiment_label = (
                sentiment_info.get("label")
                or sentiment_info.get("sentiment")
                or sentiment_info.get("overall")
                or sentiment_label
            )
            sentiment_score = sentiment_info.get("score")
        else:
            sentiment_score = None

        lines = [
            "🔍 <b>AI Insight</b>",
            f"<b>Title:</b> {html.escape(title)}",
            f"<b>Platform:</b> {html.escape(platform)}",
            f"<b>Author:</b> {html.escape(author)}",
            f"<b>Created:</b> {html.escape(str(created_at))}",
        ]

        if url:
            lines.append(f"<b>Link:</b> {html.escape(url)}")

        lines.append(
            f"<b>Value score:</b> {value_score if value_score is not None else 'N/A'} | "
            f"<b>Quality score:</b> {quality_score if quality_score is not None else 'N/A'}"
        )

        if sentiment_label:
            sentiment_text = sentiment_label
            if sentiment_score is not None:
                sentiment_text += f" ({sentiment_score:.2f})"
            lines.append(f"<b>Sentiment:</b> {html.escape(sentiment_text)}")

        if summary:
            lines.append(f"<b>Summary:</b> {html.escape(summary)}")

        if key_concepts:
            lines.append(
                "<b>Key concepts:</b> "
                + ", ".join(html.escape(str(c)) for c in key_concepts[:6])
            )

        if tags:
            lines.append(
                "<b>Tags:</b> " + ", ".join(f"#{html.escape(str(t))}" for t in tags[:8])
            )

        if insights:
            lines.append("<b>Insights:</b>")
            for insight in insights[:5]:
                lines.append(f"• {html.escape(str(insight))}")

        if action_items:
            lines.append("<b>Action items:</b>")
            for action in action_items[:5]:
                lines.append(f"• {html.escape(str(action))}")

        if recommendations:
            lines.append("<b>Recommendations:</b>")
            for rec in recommendations[:5]:
                lines.append(f"• {html.escape(str(rec))}")

        await update.effective_message.reply_text(
            "\n".join(lines),
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )
    except Exception as exc:  # pylint: disable=broad-except
        logger.error(f"Error: {e}")
        LOGGER.exception("Insight failed: %s", exc)
        await update.effective_message.reply_text(f"Insight error: {exc}")


async def _cmd_ask(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Research a query using AI agents. Usage: /ask <your question>"""
    if not await _ensure_access(update):
        return

    args = context.args or []
    if not args:
        await update.effective_message.reply_text(
            "Usage: /ask <your question>\n\n"
            "Example: /ask best practices for prompt engineering"
        )
        return

    query = " ".join(args)
    message = update.effective_message

    try:
        await message.reply_text(
            f"🔍 Researching: {html.escape(query)}...", parse_mode=ParseMode.HTML
        )

        # Lazy import research agent
        from src.domain.intelligence.agents.enhanced_research_agent import EnhancedResearchAgent

        # Perform research
        agent = EnhancedResearchAgent()
        result = await agent.research(query)

        if not result:
            await message.reply_text(
                "❌ Research returned no results. Try rephrasing your query."
            )
            return

        # Format response
        lines = [
            "🔬 <b>Research Results</b>",
            f"<b>Query:</b> {html.escape(query)}",
            "",
        ]

        # Add summary if available
        if isinstance(result, dict):
            summary = result.get("summary") or result.get("synthesis") or ""
            sources = result.get("sources") or []

            if summary:
                lines.append(f"<b>Summary:</b>")
                # Truncate if too long
                if len(summary) > 800:
                    summary = summary[:797] + "..."
                lines.append(html.escape(summary))
                lines.append("")

            if sources:
                lines.append(f"<b>Sources ({len(sources)}):</b>")
                for i, source in enumerate(sources[:5], 1):
                    if isinstance(source, dict):
                        title = source.get("title", "Unknown")
                        url = source.get("url", "")
                        lines.append(f"{i}. {html.escape(title)}")
                        if url:
                            lines.append(f"   {html.escape(url)}")
                    else:
                        lines.append(f"{i}. {html.escape(str(source))}")

                if len(sources) > 5:
                    lines.append(f"... and {len(sources) - 5} more sources")
        else:
            # Fallback for string results
            result_str = str(result)
            if len(result_str) > 1000:
                result_str = result_str[:997] + "..."
            lines.append(html.escape(result_str))

        await message.reply_text(
            "\n".join(lines), parse_mode=ParseMode.HTML, disable_web_page_preview=True
        )

    except Exception as exc:  # pylint: disable=broad-except
        logger.error(f"Error: {e}")
        LOGGER.exception("Research failed: %s", exc)
        await message.reply_text(f"❌ Research error: {exc}")


async def _cmd_recommend(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Get content recommendations based on quality/value scores. Usage: /recommend [platform] [count]"""
    if not await _ensure_access(update):
        return

    args = context.args or []
    platform = None
    limit = 10

    # Parse arguments
    for arg in args:
        lowered = arg.lower()
        if lowered in VALID_PLATFORMS:
            platform = lowered
        else:
            try:
                limit = max(1, min(20, int(arg)))
            except ValueError:
                logger.error(f"Error: {e}")
                pass

    message = update.effective_message

    try:
        await message.reply_text("🎯 Finding top recommendations...")

        db = get_database_manager()

        # Query high-value posts
        # Get more than needed so we can filter and sort
        posts = db.get_posts(
            limit=limit * 3, platforms=[platform] if platform else None
        )

        if not posts:
            await message.reply_text("No posts found for recommendations.")
            return

        # Filter and sort by value_score (high to low)
        scored_posts = [
            p
            for p in posts
            if p.get("value_score") is not None and p.get("value_score") > 6
        ]
        scored_posts.sort(key=lambda x: x.get("value_score", 0), reverse=True)

        # Take top N
        top_posts = scored_posts[:limit]

        if not top_posts:
            await message.reply_text(
                f"No high-value posts found (value score > 6).\n"
                f"Try collecting more content or check existing posts."
            )
            return

        # Format recommendations
        lines = [
            "⭐ <b>Top Recommendations</b>",
            f"Found {len(top_posts)} high-value posts"
            + (f" on {platform.title()}" if platform else ""),
            "",
        ]

        for i, post in enumerate(top_posts, 1):
            title = (
                post.get("title")
                or (post.get("content") or "").split("\n")[0][:80]
                or "Untitled"
            )
            author = post.get("author") or "Unknown"
            plat = (post.get("platform") or "?").title()
            value = post.get("value_score", 0)
            quality = post.get("quality_score", 0)
            url = post.get("url") or ""

            lines.append(
                f"{i}. <b>{html.escape(title)}</b>\n"
                f"   {plat} by {html.escape(author)}\n"
                f"   ⭐ Value: {value:.1f}/10 | Quality: {quality:.1f}/10"
            )
            if url:
                lines.append(f"   🔗 {html.escape(url)}")
            lines.append("")

        lines.append(f"💡 Tip: Use /insight <post_id> to see detailed analysis")

        await message.reply_text(
            "\n".join(lines), parse_mode=ParseMode.HTML, disable_web_page_preview=True
        )

    except Exception as exc:  # pylint: disable=broad-except
        logger.error(f"Error: {e}")
        LOGGER.exception("Recommend failed: %s", exc)
        await message.reply_text(f"❌ Recommendation error: {exc}")


async def _cmd_research(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Run autonomous research on high-value content. Usage: /research [limit]"""
    if not await _ensure_access(update):
        return

    args = context.args or []
    limit = 5

    if args:
        try:
            limit = max(1, min(10, int(args[0])))
        except ValueError:
            logger.error(f"Error: {e}")
            pass

    message = update.effective_message

    try:
        await message.reply_text(
            f"🔬 Running autonomous research on up to {limit} high-value posts...\n"
            f"This will take a few minutes."
        )

        # Lazy import
        from src.domain.intelligence.agents.autonomous_research_orchestrator import (
            get_research_orchestrator,
        )

        orchestrator = get_research_orchestrator()
        results = await orchestrator.auto_research_recent(limit=limit)

        researched = results.get("researched", 0)
        total = results.get("total", 0)

        lines = [
            "🔬 <b>Autonomous Research Complete</b>",
            f"Researched: <b>{researched}</b> out of {total} posts",
            "",
        ]

        if researched > 0:
            lines.append("Topics researched:")
            for result in results.get("results", [])[:5]:
                if result.get("success"):
                    topics = result.get("result", {}).get("topics", [])
                    if topics:
                        lines.append(f"• {', '.join(topics[:3])}")

            lines.append("")
            lines.append("💡 Use /latest to see updated posts with research insights")
        else:
            lines.append("No posts needed research at this time.")
            lines.append("High-value posts (score >= 7) are automatically researched.")

        await message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)

    except Exception as exc:  # pylint: disable=broad-except
        logger.error(f"Error: {e}")
        LOGGER.exception("Research failed: %s", exc)
        await message.reply_text(f"❌ Research error: {exc}")


async def _cmd_curate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Get curated reading list and content organization. Usage: /curate"""
    if not await _ensure_access(update):
        return

    message = update.effective_message

    try:
        await message.reply_text("📚 Curating your personalized content...")

        # Lazy import
        from src.domain.intelligence.agents.librarian_agent import get_librarian_agent

        librarian = get_librarian_agent()

        # Organize content
        organization = librarian.organize_content(limit=50)

        # Get reading list
        reading_list = librarian.curate_reading_list()

        lines = ["📚 <b>Content Curation</b>", ""]

        # Show categories
        categories = organization.get("categories", {})
        if categories:
            lines.append(f"<b>Categories ({len(categories)}):</b>")
            for category, posts in sorted(
                categories.items(), key=lambda x: len(x[1]), reverse=True
            )[:5]:
                lines.append(f"• {category}: {len(posts)} posts")
            lines.append("")

        # Show patterns
        patterns = organization.get("patterns", {})
        trending = patterns.get("trending_topics", [])
        if trending:
            lines.append("<b>Trending Topics:</b>")
            for topic, count in trending[:5]:
                lines.append(f"• {html.escape(str(topic))}: {count}x")
            lines.append("")

        # Show reading list
        if reading_list:
            lines.append(f"<b>Curated Reading List ({len(reading_list)} items):</b>")
            for i, item in enumerate(reading_list[:5], 1):
                post = item["post"]
                score = item["curation_score"]
                title = (
                    post.get("title") or (post.get("content") or "").split("\n")[0][:60]
                )
                lines.append(f"{i}. {html.escape(title)} (score: {score:.1f})")

            if len(reading_list) > 5:
                lines.append(f"... and {len(reading_list) - 5} more items")

        lines.append("")
        lines.append("💡 Use /latest to browse all content")

        await message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)

    except Exception as exc:  # pylint: disable=broad-except
        logger.error(f"Error: {e}")
        LOGGER.exception("Curate failed: %s", exc)
        await message.reply_text(f"❌ Curation error: {exc}")


async def _cmd_publish(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Publish analyzed content to social media. Usage: /publish <post_id> <platform>"""
    if not await _ensure_access(update):
        return

    args = context.args or []
    if len(args) < 2:
        await update.effective_message.reply_text(
            "Usage: /publish <post_id> <platform>\n\n"
            "Platforms: twitter, telegram, threads\n"
            "Example: /publish abc123 twitter"
        )
        return

    post_id = args[0]
    platform = args[1].lower()
    message = update.effective_message

    try:
        # Get post from database
        db = get_database_manager()
        post = db.get_post_by_id(post_id)

        if not post:
            await message.reply_text(f"❌ Post not found: {post_id}")
            return

        # Get or generate content to publish
        content = post.get("content") or post.get("title", "")

        if not content:
            await message.reply_text("❌ Post has no content to publish")
            return

        # Lazy import posting service
        from src.services.posting_service import get_posting_service

        await message.reply_text(f"📤 Publishing to {platform.title()}...")

        posting_service = get_posting_service()
        result = posting_service.publish(platform, content)

        if result.get("success"):
            await message.reply_text(
                f"✅ <b>Published Successfully</b>\n\n"
                f"Platform: {platform.title()}\n"
                f"Post ID: {post_id}\n"
                f"Timestamp: {result.get('timestamp', 'N/A')}",
                parse_mode=ParseMode.HTML,
            )
        else:
            error = result.get("error", "Unknown error")
            await message.reply_text(
                f"❌ <b>Publishing Failed</b>\n\n"
                f"Platform: {platform.title()}\n"
                f"Error: {html.escape(error)}",
                parse_mode=ParseMode.HTML,
            )

    except Exception as exc:  # pylint: disable=broad-except
        logger.error(f"Error: {e}")
        LOGGER.exception("Publish failed: %s", exc)
        await message.reply_text(f"❌ Publish error: {exc}")


async def _cmd_transform(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Transform content for a specific platform/persona. Usage: /transform <post_id> <persona> <platform>"""
    if not await _ensure_access(update):
        return

    args = context.args or []
    if len(args) < 3:
        await update.effective_message.reply_text(
            "Usage: /transform <post_id> <persona> <platform>\n\n"
            "Personas: skeptical_builder, technical_teacher, storyteller\n"
            "Platforms: twitter, telegram, threads\n"
            "Example: /transform abc123 skeptical_builder twitter"
        )
        return

    post_id = args[0]
    persona = args[1]
    platform = args[2].lower()
    message = update.effective_message

    try:
        # Get post from database
        db = get_database_manager()
        post = db.get_post_by_id(post_id)

        if not post:
            await message.reply_text(f"❌ Post not found: {post_id}")
            return

        content = post.get("content") or post.get("title", "")

        if not content:
            await message.reply_text("❌ Post has no content to transform")
            return

        await message.reply_text(
            f"🎭 Transforming content for {persona} on {platform}..."
        )

        # Here you would call transformation service from mimesis
        # For now, just return a placeholder
        transformed = f"[{persona}] {content[:200]}"

        await message.reply_text(
            f"✨ <b>Transformed Content</b>\n\n"
            f"<b>Persona:</b> {persona}\n"
            f"<b>Platform:</b> {platform.title()}\n\n"
            f"<code>{html.escape(transformed)}</code>\n\n"
            f"💡 Use /publish {post_id} {platform} to post this",
            parse_mode=ParseMode.HTML,
        )

    except Exception as exc:  # pylint: disable=broad-except
        logger.error(f"Error: {e}")
        LOGGER.exception("Transform failed: %s", exc)
        await message.reply_text(f"❌ Transform error: {exc}")


async def _handle_read_discovered(
    update: Update, context: ContextTypes.DEFAULT_TYPE, index: int
) -> None:
    """Show full content of a discovered post"""
    query = update.callback_query
    await query.answer()

    discovered_posts = context.user_data.get("discovered_posts", [])

    if 0 <= index < len(discovered_posts):
        post = discovered_posts[index]

        # Build full post display
        lines = [
            "━━━━━━━━━━━━━━━━━━━━━━━━",
            f"📖 <b>DISCOVERED POST #{index + 1}</b>",
            "━━━━━━━━━━━━━━━━━━━━━━━━\n",
            f"🔸 <b>Platform:</b> {post['platform'].upper()}",
            f"👤 <b>Author:</b> {html.escape(post['author'])}",
            f"📊 <b>Quality:</b> {post['quality']:.2f}",
            f"🎯 <b>Topics:</b> {', '.join(post['topics'])}\n",
            f"📝 <b>Content:</b>",
            html.escape(post["content"][:2000]),  # Show up to 2000 chars
        ]

        if len(post["content"]) > 2000:
            lines.append("\n<i>... (content truncated)</i>")

        # Add buttons
        keyboard = [
            [InlineKeyboardButton("🔗 Open Full Post", url=post["url"])]
            if post["url"]
            else [],
            [
                InlineKeyboardButton("⬅️ Back", callback_data="back_to_report"),
                InlineKeyboardButton(
                    "💾 Save", callback_data=f"save_discovered_{index}"
                ),
            ],
        ]
        keyboard = [row for row in keyboard if row]  # Filter empty rows

        await query.edit_message_text(
            "\n".join(lines),
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    else:
        await query.edit_message_text("Post not found. Please run /discover_new again.")


async def _handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline keyboard button presses"""
    query = update.callback_query
    await query.answer()

    # Create fake update with the message from callback
    fake_update = Update(update_id=update.update_id, message=query.message)

    action = query.data

    # Handle discovered post viewing
    if action.startswith("read_discovered_"):
        index = int(action.split("_")[-1])
        await _handle_read_discovered(update, context, index)
        return

    # Map actions to command handlers
    action_map = {
        "action_start": _cmd_start,
        "action_help": _cmd_help,
        "action_status": _cmd_status,
        "action_collect": _cmd_collect,
        "action_latest": _cmd_latest,
        "action_recommend": _cmd_recommend,
        "action_research": _cmd_research,
        "action_curate": _cmd_curate,
        "action_env": _cmd_env,
    }

    if action in action_map:
        # Show loading indicator
        try:
            await query.edit_message_text(
                "⏳ <i>Processing...</i>", parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logger.error(f"Error: {e}")
            pass

        # Execute the command
        await action_map[action](fake_update, context)
    else:
        await query.edit_message_text("❌ Unknown action")


def build_application() -> Application:
    token = _get_bot_token()
    app: Application = ApplicationBuilder().token(token).build()

    # Command handlers
    # Core commands
    app.add_handler(CommandHandler("start", _cmd_start))
    app.add_handler(CommandHandler("help", _cmd_help))

    # Automation commands
    app.add_handler(CommandHandler("automate", _cmd_automate))
    app.add_handler(CommandHandler("scheduler_status", _cmd_scheduler_status))

    # NEW: Agent commands
    app.add_handler(CommandHandler("research_repo", research_repo_command))
    app.add_handler(CommandHandler("get_book", get_book_command))
    app.add_handler(CommandHandler("rewrite", rewrite_command))
    app.add_handler(CommandHandler("personas", personas_command))
    app.add_handler(CommandHandler("library", library_command))

    # Autonomous discovery (PHASE 5)
    #     app.add_handler(CommandHandler("autonomous", _cmd_autonomous))
    # MISSING:     app.add_handler(CommandHandler("daily_digest", _cmd_daily_digest))

    # Librarian commands
    app.add_handler(CommandHandler("collections", _cmd_collections))
    app.add_handler(CommandHandler("reading_list", _cmd_reading_list))
    app.add_handler(CommandHandler("digest", _cmd_digest))

    # Digest commands
    app.add_handler(CommandHandler("morning", _cmd_morning_digest))
    app.add_handler(CommandHandler("evening", _cmd_evening_summary))

    # Deep research command
    app.add_handler(CommandHandler("research", _cmd_deep_research))

    # Health monitoring command
    app.add_handler(CommandHandler("health", _cmd_health))
    app.add_handler(CommandHandler("status", _cmd_status))
    app.add_handler(CommandHandler("collect", _cmd_collect))
    app.add_handler(CommandHandler("analyze", _cmd_analyze))
    app.add_handler(CommandHandler("env", _cmd_env))
    app.add_handler(CommandHandler("latest", _cmd_latest))
    app.add_handler(CommandHandler("insight", _cmd_insight))
    app.add_handler(CommandHandler("ask", _cmd_ask))
    app.add_handler(CommandHandler("recommend", _cmd_recommend))
    app.add_handler(CommandHandler("research", _cmd_research))
    app.add_handler(CommandHandler("curate", _cmd_curate))
    app.add_handler(CommandHandler("schedule", _cmd_schedule))
    app.add_handler(CommandHandler("publish", _cmd_publish))
    app.add_handler(CommandHandler("transform", _cmd_transform))
    app.add_handler(CommandHandler("profile", _cmd_profile))
    app.add_handler(CommandHandler("topics", _cmd_topics))
    app.add_handler(CommandHandler("discover", _cmd_discover))
    app.add_handler(CommandHandler("discover_new", _cmd_discover_new))

    # Callback query handler for inline keyboard buttons
    app.add_handler(CallbackQueryHandler(_handle_callback))

    return app


def run_bot() -> None:
    app = build_application()
    LOGGER.info("Starting BEYONDLINES Telegram bot...")
    # Use single polling loop to avoid multiple updater conflicts
    app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_bot()
