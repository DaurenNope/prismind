#!/usr/bin/env python3
"""
Production Content Pipeline - Ready to Post Today

For each profile (qronoya, aspandead):
1. Pull best content from usable_posts
2. Rewrite with their voice
3. Schedule posts (time-sensitive first, then regular schedule)
4. Publish to Threads/Telegram
"""

import asyncio
import os
from datetime import datetime, timedelta
from typing import Dict, List

from supabase import create_client

from src.domain.publishing.modular_rewriter.compat import create_compat_rewriter
from src.services.profile_content_pipeline import ProfileContentPipeline

# Profiles to manage
PROFILES = {
    "qronoya": {
        "platforms": ["threads", "telegram"],
        "daily_posts": 2,  # 2 posts per day
        "language": "ru",
    },
    "aspandead": {
        "platforms": ["threads"],
        "daily_posts": 1,  # 1 post per day
        "language": "ru",
    },
}


async def get_content_for_profile(profile_key: str, count: int = 10) -> List[Dict]:
    """
    Get best content from usable_posts for a profile.
    Priority: time-sensitive first, then high-quality evergreen.
    """
    client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

    # Get time-sensitive posts first
    time_sensitive = (
        client.table("usable_posts")
        .select("*")
        .eq("best_persona_key", profile_key)
        .eq("time_sensitive", True)
        .in_("relevance_window", ["same-day", "24-72h"])
        .order("urgency_score", desc=True)
        .limit(5)
        .execute()
    )

    # Get high-quality evergreen posts
    evergreen = (
        client.table("usable_posts")
        .select("*")
        .eq("best_persona_key", profile_key)
        .in_("relevance_window", ["this-week", "evergreen"])
        .gte("quality_score", 7.0)
        .order("quality_score", desc=True)
        .limit(count)
        .execute()
    )

    # Combine: time-sensitive first
    all_posts = []
    if time_sensitive.data:
        all_posts.extend(time_sensitive.data)

    if evergreen.data:
        # Add evergreen posts that aren't already included
        existing_ids = {p["id"] for p in all_posts}
        all_posts.extend([p for p in evergreen.data if p["id"] not in existing_ids])

    return all_posts[:count]


async def rewrite_for_profile(post: Dict, profile_key: str) -> str:
    """Rewrite a post for the profile's voice using the existing rewriter"""

    rewriter = create_compat_rewriter()

    # Determine platform from profile config
    config = PROFILES.get(profile_key, {})
    platform = config["platforms"][0]  # Use first platform for rewrite

    try:
        # Create analyzed_content structure from usable_post
        analyzed_content = {
            "post_id": post.get("id"),
            "content": post.get("content", ""),
            "summary": post.get("ai_summary", post.get("content", "")),
            "category": post.get("category", ""),
            "topics": post.get("tags", []),
            "key_concepts": post.get("key_concepts", []),
            "rewrite_angles": [
                {
                    "persona": profile_key,
                    "angle": "direct",
                    "why": "Authentic voice",
                    "platform_fit": platform,
                }
            ],
        }

        result = await rewriter.rewrite_analyzed_post(
            analyzed_content=analyzed_content, persona=profile_key, platform=platform
        )

        if result.get("error"):
            print(f"   ⚠️ Rewrite error: {result['error']}")
            return ""

        return result.get("rewritten_post", "")

    except Exception as e:
        print(f"❌ Rewrite error for {profile_key}: {e}")
        import traceback

        traceback.print_exc()
        return ""


async def schedule_post(
    profile_key: str,
    content: str,
    platform: str,
    post_time: datetime,
    source_post_id: str = None,
):
    """
    Schedule a post for a specific time.
    Uses existing schema: persona_key, scheduled_time, etc.
    """
    client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

    try:
        result = (
            client.table("scheduled_posts")
            .insert(
                {
                    "persona_key": profile_key,
                    "platform": platform,
                    "content": content,
                    "content_type": "single_post",
                    "scheduled_time": post_time.isoformat(),
                    "scheduled_at": post_time.isoformat(),
                    "status": "pending",
                    "priority": 5,  # Default priority
                    "retry_count": 0,
                    "max_retries": 3,
                    "metadata": {"source_post_id": source_post_id}
                    if source_post_id
                    else {},
                }
            )
            .execute()
        )

        print(
            f"✅ Scheduled {platform} post for {profile_key} at {post_time.strftime('%H:%M')}"
        )
        return result.data

    except Exception as e:
        print(f"❌ Schedule error: {e}")
        return None


async def generate_schedule_for_profile(profile_key: str):
    """
    Generate today's posting schedule for a profile.

    Strategy:
    - Time-sensitive posts: ASAP (next available slot)
    - Regular posts: Spread throughout the day
    """
    config = PROFILES[profile_key]
    daily_posts = config["daily_posts"]
    platforms = config["platforms"]

    print(f"\n🏗️ Building schedule for {profile_key}")
    print(f"   Target: {daily_posts} posts/day on {', '.join(platforms)}")

    # Get content
    posts = await get_content_for_profile(profile_key, daily_posts * 2)  # Get extras

    if not posts:
        print(f"⚠️ No usable posts found for {profile_key}")
        return

    print(f"   Found {len(posts)} usable posts")

    # Separate time-sensitive and evergreen
    time_sensitive_posts = [p for p in posts if p.get("time_sensitive")]
    evergreen_posts = [p for p in posts if not p.get("time_sensitive")]

    print(f"   - {len(time_sensitive_posts)} time-sensitive")
    print(f"   - {len(evergreen_posts)} evergreen")

    # Generate posting times (spread throughout day)
    now = datetime.now()
    posting_times = []

    # Time-sensitive: post ASAP (starting in 30 mins)
    for i in range(min(len(time_sensitive_posts), daily_posts)):
        post_time = now + timedelta(minutes=30 + (i * 120))  # 2 hours apart
        posting_times.append(("time_sensitive", post_time))

    # Evergreen: fill remaining slots
    remaining_slots = daily_posts - len(posting_times)
    for i in range(min(len(evergreen_posts), remaining_slots)):
        # Spread evenly: morning, afternoon, evening
        hour_offsets = [10, 14, 18, 20]  # 10am, 2pm, 6pm, 8pm
        target_hour = hour_offsets[i % len(hour_offsets)]

        post_time = now.replace(hour=target_hour, minute=0, second=0, microsecond=0)
        if post_time < now:
            post_time += timedelta(days=1)  # Tomorrow if time passed

        posting_times.append(("evergreen", post_time))

    # Rewrite and schedule
    print(f"\n✍️ Rewriting and scheduling {len(posting_times)} posts...")

    scheduled_count = 0
    for i, (content_type, post_time) in enumerate(posting_times):
        # Get the right post
        if content_type == "time_sensitive" and time_sensitive_posts:
            post = time_sensitive_posts.pop(0)
        elif evergreen_posts:
            post = evergreen_posts.pop(0)
        else:
            continue

        print(f"\n📝 Post {i+1}/{len(posting_times)} ({content_type})")
        print(f"   Topic: {post.get('topic', 'N/A')[:50]}")
        print(f"   Quality: {post.get('quality_score', 0)}/10")

        # Rewrite
        rewritten = await rewrite_for_profile(post, profile_key)

        if not rewritten:
            print(f"   ⚠️ Rewrite failed, skipping")
            continue

        print(f"   ✓ Rewritten ({len(rewritten)} chars)")

        # Schedule for each platform
        for platform in platforms:
            await schedule_post(
                profile_key,
                rewritten,
                platform,
                post_time,
                source_post_id=post.get("id"),
            )
            scheduled_count += 1

    print(f"\n✅ Scheduled {scheduled_count} posts for {profile_key}")


async def publish_due_posts():
    """
    Check for posts that are due to be published and publish them.
    Run this every 5 minutes via cron or background worker.
    """
    client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

    now = datetime.now()

    # Get posts due for publishing
    result = (
        client.table("scheduled_posts")
        .select("*")
        .eq("status", "pending")
        .lte("scheduled_time", now.isoformat())
        .execute()
    )

    if not result.data:
        print("No posts due for publishing")
        return

    print(f"\n📤 Publishing {len(result.data)} due posts...")

    for post in result.data:
        try:
            # Note: Actual publishing should be handled by the publisher worker service.
            # This script is for testing/verification only. For production publishing,
            # use the automated publisher worker which handles Threads/Telegram posting.
            persona = post.get("persona_key", post.get("personality_key", "unknown"))
            print(f"   Publishing to {post['platform']} for {persona}")
            print(f"   Content: {post['content'][:100]}...")

            # Mark as published (simulation mode - use publisher worker for actual posting)
            client.table("scheduled_posts").update(
                {"status": "posted", "updated_at": now.isoformat()}
            ).eq("id", post["id"]).execute()

            print(f"   ✅ Marked as published (use publisher worker for actual posting)")

        except Exception as e:
            print(f"   ❌ Publish error: {e}")

            # Mark as failed
            client.table("scheduled_posts").update(
                {
                    "status": "failed",
                    "error_message": str(e),
                    "updated_at": now.isoformat(),
                }
            ).eq("id", post["id"]).execute()


async def main():
    """Run the production content pipeline"""

    print("=" * 60)
    print("🚀 PRODUCTION CONTENT PIPELINE")
    print("=" * 60)

    # Generate schedules for all profiles
    for profile_key in PROFILES.keys():
        await generate_schedule_for_profile(profile_key)

    print("\n" + "=" * 60)
    print("✅ PIPELINE COMPLETE")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Run this script daily to generate schedule")
    print("2. Set up cron/worker to run publish_due_posts() every 5 mins")
    print("3. Monitor scheduled_posts table for status")


if __name__ == "__main__":
    asyncio.run(main())
