#!/usr/bin/env python3
"""
Live Posting Test - Controlled Real Posting
Tests actual Twitter and Threads posting with safety limits
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# SAFETY CONFIGURATION
MAX_POSTS_PER_PLATFORM = 1  # HARD LIMIT - ONLY 1 POST PER PLATFORM
REQUIRE_MANUAL_CONFIRMATION = True  # MUST CONFIRM BEFORE POSTING
ENABLE_POSTING = True  # MASTER SWITCH


async def confirm_before_posting(platform: str, content: str, mention: str) -> bool:
    """Get user confirmation before posting"""
    print(f"\n🚨 ABOUT TO POST ON {platform.upper()} 🚨")
    print("=" * 60)
    print(f"Replying to: {mention}")
    print(f"Content: {content}")
    print("=" * 60)

    if not REQUIRE_MANUAL_CONFIRMATION:
        return True

    response = (
        input("\n❓ Do you want to post this reply? (yes/y/confirm): ").lower().strip()
    )
    return response in ["yes", "y", "confirm"]


async def test_twitter_live_posting():
    """Test actual Twitter posting"""
    print("🐦 Testing Twitter Live Posting...")

    if not ENABLE_POSTING:
        print("⚠️  Posting is disabled - skipping")
        return True

    try:
        from src.services.profile_content_selector import profile_content_selector
        from src.twitter.interaction_client import (
            InteractionType,
            TwitterInteraction,
            TwitterInteractionClient,
        )

        # Initialize client
        api_keys = {
            "TWITTER_BEARER_TOKEN": os.getenv("TWITTER_BEARER_TOKEN"),
            "TWITTER_API_KEY": os.getenv("TWITTER_API_KEY"),
            "TWITTER_API_SECRET": os.getenv("TWITTER_API_SECRET"),
            "TWITTER_ACCESS_TOKEN": os.getenv("TWITTER_ACCESS_TOKEN"),
            "TWITTER_ACCESS_TOKEN_SECRET": os.getenv("TWITTER_ACCESS_TOKEN_SECRET"),
        }

        client = TwitterInteractionClient(api_keys)
        await client.initialize()

        print(
            f"✅ Twitter client initialized for @{client.client.get_me().data.username}"
        )

        # Get recent mentions
        mentions = client.client.get_users_mentions(
            tweet_fields=[
                "created_at",
                "author_id",
                "public_metrics",
                "context_annotations",
            ],
            user_fields=["username", "name"],
            expansions=["author_id"],
            max_results=5,
        )

        if not mentions.data:
            print("❌ No recent mentions found - skipping Twitter test")
            return True

        print(f"📋 Found {len(mentions.data)} recent mentions")

        # Find a good mention to reply to (not too old, meaningful content)
        users = {user["id"]: user for user in mentions.includes.get("users", [])}
        selected_mention = None

        for mention in mentions.data:
            author_info = users.get(mention.author_id, {})
            username = author_info.get("username", "unknown")

            # Skip self-mentions or very short mentions
            if username == "beyondlines" or len(mention.text.strip()) < 10:
                continue

            # Use the first suitable mention
            selected_mention = mention
            break

        if not selected_mention:
            print("❌ No suitable mentions found for reply test")
            return True

        # Create interaction
        author_info = users.get(selected_mention.author_id, {})
        interaction = TwitterInteraction(
            tweet_id=selected_mention.id,
            author_id=selected_mention.author_id,
            author_username=author_info.get("username", "unknown"),
            content=selected_mention.text,
            interaction_type=InteractionType.MENTION,
        )

        print(
            f"✅ Selected mention from @{interaction.author_username}: {interaction.content[:50]}..."
        )

        # Build conversation context
        interaction.context_thread = await client.build_conversation_thread(
            selected_mention.id
        )
        print(
            f"✅ Built conversation context with {len(interaction.context_thread)} tweets"
        )

        # Generate reply
        reply_content = await client.handle_interaction(interaction)
        print(f"✅ Generated reply: {reply_content[:100]}...")

        # SAFETY CHECK: Confirm before posting
        if not await confirm_before_posting(
            "Twitter",
            reply_content,
            f"@{interaction.author_username}: {interaction.content}",
        ):
            print("❌ User cancelled posting")
            return True

        # POST THE REPLY
        print("\n🚀 POSTING TO TWITTER...")
        success = await client.post_reply(interaction)

        if success:
            print(f"✅ SUCCESS! Reply posted to Twitter")
            print(f"🔗 Tweet ID: {interaction.tweet_id}")
            print(f"💬 Reply: {interaction.reply_content}")
            return True
        else:
            print("❌ FAILED: Could not post reply to Twitter")
            return False

    except Exception as e:
        print(f"❌ Twitter live posting failed: {e}")
        return False


async def test_threads_live_posting():
    """Test actual Threads posting"""
    print("\n🧵 Testing Threads Live Posting...")

    if not ENABLE_POSTING:
        print("⚠️  Posting is disabled - skipping")
        return True

    try:
        from config.threads_cookies import COOKIES as threads_cookies
        from playwright.async_api import async_playwright

        from src.social.multiplatform_interaction import (
            MultiPlatformInteractionClient,
            SocialInteraction,
            SocialPlatform,
        )

        # Initialize multi-platform client
        configs = {
            "threads": {
                "cookies": threads_cookies,
                "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "headless": False,  # Show browser for debugging
            }
        }

        client = MultiPlatformInteractionClient(configs)
        await client.initialize_platform(SocialPlatform.THREADS)

        print("✅ Threads client initialized")

        # Get recent activity (mentions)
        mentions = await client.check_platform_mentions(
            SocialPlatform.THREADS, limit=10
        )

        if not mentions:
            print("❌ No recent Threads mentions found - skipping test")
            return True

        print(f"📋 Found {len(mentions)} Threads interactions")

        # Select a good mention
        selected_mention = mentions[0]  # Use first mention
        print(f"✅ Selected Threads mention: {selected_mention.content[:50]}...")

        # Generate reply using AI
        from src.domain.analysis.analyzers.ai_service_manager import ai_service_manager

        context_prompt = f"""
        You are Beyondlines on Threads. Reply to this mention:

        From: @{selected_mention.author_username}
        Content: {selected_mention.content}

        Guidelines:
        - Be conversational and helpful
        - Keep under 500 characters (Threads limit)
        - Add value to the conversation
        - Use 1-2 relevant emojis max
        - Don't repeat original content
        """

        reply_content = await ai_service_manager.generate_text(
            prompt=context_prompt,
            max_tokens=200,
            temperature=0.7,
            persona_id="threads_reply_assistant",
        )

        # Clean reply
        if not reply_content.startswith(f"@{selected_mention.author_username}"):
            reply_content = f"@{selected_mention.author_username} {reply_content}"

        # Limit length
        if len(reply_content) > 500:
            reply_content = reply_content[:497] + "..."

        selected_mention.reply_content = reply_content
        print(f"✅ Generated Threads reply: {reply_content[:100]}...")

        # SAFETY CHECK: Confirm before posting
        if not await confirm_before_posting(
            "Threads",
            reply_content,
            f"@{selected_mention.author_username}: {selected_mention.content}",
        ):
            print("❌ User cancelled posting")
            return True

        # POST THE REPLY
        print("\n🚀 POSTING TO THREADS...")
        success = await client.post_reply(selected_mention)

        if success:
            print(f"✅ SUCCESS! Reply posted to Threads")
            print(f"💬 Reply: {selected_mention.reply_content}")
            return True
        else:
            print("❌ FAILED: Could not post reply to Threads")
            return False

    except Exception as e:
        print(f"❌ Threads live posting failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def show_posting_summary():
    """Show summary of what was posted"""
    print("\n" + "=" * 70)
    print("📊 LIVE POSTING TEST SUMMARY")
    print("=" * 70)
    print(f"⏰ Test completed at: {datetime.now(timezone.utc).isoformat()}")
    print(f"🔧 Posting enabled: {ENABLE_POSTING}")
    print(f"🛡️  Manual confirmation required: {REQUIRE_MANUAL_CONFIRMATION}")
    print(f"📈 Max posts per platform: {MAX_POSTS_PER_PLATFORM}")
    print("\n⚠️  SAFETY NOTES:")
    print("- Only 1 post per platform allowed")
    print("- All posts require manual confirmation")
    print("- Monitor for any platform warnings")
    print("- Check actual posts on platforms to verify")
    print("=" * 70)


async def main():
    """Run controlled live posting test"""
    print("🚨 LIVE POSTING TEST - CONTROLLED ENVIRONMENT 🚨")
    print("This will ACTUALLY POST to Twitter and Threads!")
    print("Safety limits are in place to prevent spam.")

    if not ENABLE_POSTING:
        print("\n❌ POSTING IS DISABLED - Enable ENABLE_POSTING = True to test")
        return 1

    # Final safety confirmation
    print("\n" + "🛑" * 20)
    print("FINAL SAFETY CHECK")
    print("🛑" * 20)
    print("This will post REAL replies to social media!")
    print(f"Max posts: {MAX_POSTS_PER_PLATFORM} per platform")
    print(f"Manual confirmation: {REQUIRE_MANUAL_CONFIRMATION}")

    final_confirm = input(
        "\n❓ Are you ABSOLUTELY SURE you want to continue? (type 'I UNDERSTAND'): "
    )
    if final_confirm != "I UNDERSTAND":
        print("❌ Test cancelled - safety confirmation failed")
        return 1

    print("\n✅ Starting controlled live posting test...")

    # Test Twitter
    twitter_success = await test_twitter_live_posting()

    # Test Threads
    threads_success = await test_threads_live_posting()

    # Show summary
    await show_posting_summary()

    # Return success if both tests passed (or were skipped)
    if twitter_success and threads_success:
        print("\n🎉 Live posting test completed successfully!")
        print("Check your Twitter and Threads accounts for the actual posts!")
        return 0
    else:
        print(
            f"\n⚠️  Some tests failed - Twitter: {twitter_success}, Threads: {threads_success}"
        )
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
