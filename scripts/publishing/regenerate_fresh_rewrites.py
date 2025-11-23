#!/usr/bin/env python3
"""
Regenerate fresh rewrites for 3-4 selected posts using updated prompts
"""
import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

load_dotenv()

from src.infrastructure.database.manager import SupabaseManager
from src.domain.publishing.modular_rewriter.compat import create_compat_rewriter

# Selected posts to rewrite
SELECTED_POSTS = [
    {
        "post_id": "twitter_1987703781392371859",
        "platform": "twitter",
        "persona": "qronoya",
        "output_platform": "threads",
    },
    {
        "post_id": "DQ6njNDgu5F",
        "platform": "threads",
        "persona": "qronoya",
        "output_platform": "threads",
    },
    {
        "post_id": "DQ7OdORiTzA",
        "platform": "threads",
        "persona": "qronoya",
        "output_platform": "threads",
    },
    {
        "post_id": "twitter_1987571863136981459",
        "platform": "twitter",
        "persona": "qronoya",
        "output_platform": "threads",
    },
]


async def regenerate_rewrites():
    """Regenerate rewrites for selected posts"""
    supabase = SupabaseManager().client
    rewriter = create_compat_rewriter()

    print("🔄 Regenerating rewrites with updated prompts...\n")
    print("=" * 80)

    results = []

    for i, post_config in enumerate(SELECTED_POSTS, 1):
        post_id = post_config["post_id"]
        platform = post_config["platform"]

        print(f"\n📝 Post {i}/{len(SELECTED_POSTS)}: {post_id}")
        print("-" * 80)

        # Get post from database
        try:
            if platform == "threads":
                # Try usable_posts first
                result = (
                    supabase.table("usable_posts")
                    .select("*")
                    .eq("post_id", post_id)
                    .execute()
                )
                if result.data:
                    post = result.data[0]
                else:
                    # Fallback to posts table
                    result = (
                        supabase.table("posts")
                        .select("*")
                        .eq("post_id", post_id)
                        .execute()
                    )
                    post = result.data[0] if result.data else None
            else:
                # For Twitter, check posts table
                result = (
                    supabase.table("posts").select("*").eq("post_id", post_id).execute()
                )
                post = result.data[0] if result.data else None

            if not post:
                print(f"❌ Post not found: {post_id}")
                continue

            content = post.get("content", "") or post.get("title", "")
            if not content:
                print(f"❌ No content found for post: {post_id}")
                continue

            print(f"✅ Found post: {post.get('topic', 'N/A')}")
            print(f"📊 Quality: {post.get('quality_score', 'N/A')}/10")
            print(f"📝 Content length: {len(content)} chars")
            print(f"\n📄 Original content (first 200 chars):")
            print(content[:200] + "..." if len(content) > 200 else content)

            # Prepare analyzed content structure
            analyzed = {
                "content": content,
                "category": post.get("topic", "Technology"),
                "summary": post.get("ai_summary", content[:200]),
                "key_concepts": post.get("key_concepts", [])
                if isinstance(post.get("key_concepts"), list)
                else [],
                "topics": post.get("tags", [])
                if isinstance(post.get("tags"), list)
                else [],
                "rewrite_angles": [
                    {
                        "persona": post_config["persona"],
                        "angle": "Rewrite",
                        "tone": "Natural",
                        "platform_fit": post_config["output_platform"],
                    }
                ],
            }

            # Generate rewrite
            print(
                f"\n✨ Generating rewrite for {post_config['persona']} → {post_config['output_platform']}..."
            )
            result = await rewriter.rewrite_analyzed_post(
                analyzed, post_config["persona"], post_config["output_platform"]
            )

            if "error" in result:
                print(f"❌ Error: {result['error']}")
                if result.get("skipped"):
                    print(f"⚠️ Skipped: {result.get('reason', 'Unknown reason')}")
                continue

            rewritten = result.get("rewritten_content", "")
            if not rewritten:
                print("❌ No rewritten content returned")
                continue

            print(f"\n✅ Rewrite generated ({len(rewritten)} chars)")
            print("\n" + "=" * 80)
            print("📝 REWRITTEN CONTENT:")
            print("=" * 80)
            print(rewritten)
            print("=" * 80)

            results.append(
                {
                    "post_id": post_id,
                    "original": content[:200] + "..."
                    if len(content) > 200
                    else content,
                    "rewritten": rewritten,
                    "platform": post_config["output_platform"],
                    "persona": post_config["persona"],
                }
            )

        except Exception as e:
            print(f"❌ Error processing post {post_id}: {e}")
            import traceback

            traceback.print_exc()
            continue

    # Summary
    print("\n\n" + "=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)
    print(f"✅ Successfully regenerated {len(results)} rewrites")
    print("\nAll rewrites use:")
    print("  - Updated personalization prompts (first-person, specific details)")
    print("  - Single dashes (-) instead of long dashes (—)")
    print("  - Social media optimization (concise, juicy, emotional)")
    print("  - Proper Reddit comment handling (context, not main content)")

    return results


if __name__ == "__main__":
    results = asyncio.run(regenerate_rewrites())
