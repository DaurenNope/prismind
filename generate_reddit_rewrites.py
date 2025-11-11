#!/usr/bin/env python3
"""
Generate rewrites specifically from Reddit posts
"""
import asyncio
import json
import logging
from pathlib import Path
from datetime import datetime
from src.database.operations import DatabaseOperations
from src.publishing.rewriter import ContentRewriter

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def generate_reddit_rewrites():
    """
    Generate rewrites from Reddit posts for personas
    """
    print("=" * 80)
    print("GENERATE REWRITES FROM REDDIT POSTS")
    print("=" * 80)

    # Initialize
    db = DatabaseOperations()
    rewriter = ContentRewriter()

    # Create curation directory
    curation_dir = Path("data/curated_posts")
    curation_dir.mkdir(parents=True, exist_ok=True)

    # Define personas and which subreddits fit them
    # qronoya: Tech/business content
    # aspandead: Relationship/emotional content
    persona_configs = {
        "qronoya": {
            "name": "Qronoya",
            "subreddits": ["entrepreneur", "startups", "technology", "programming", "business"],
            "min_value_score": 7.0
        },
        "aspandead": {
            "name": "Aspandead",
            "subreddits": ["relationships", "dating_advice", "BreakUps", "UnsentLetters", "TrueOffMyChest"],
            "min_value_score": 6.0
        }
    }

    # Get Reddit posts
    print("\n📊 Fetching Reddit posts from database...")
    reddit_posts = db.get_posts_by_platform("reddit", limit=50)

    if not reddit_posts:
        print("❌ No Reddit posts found in database")
        print("💡 Try running the Reddit collector first")
        return

    print(f"✅ Found {len(reddit_posts)} Reddit posts")

    # Filter high-quality posts
    high_quality_posts = []
    for p in reddit_posts:
        quality_score = p.get('quality_score', 0)
        value_score = p.get('value_score', 0)

        # Handle string scores
        if isinstance(quality_score, str):
            try:
                quality_score = float(quality_score)
            except (ValueError, TypeError):
                quality_score = 0

        if isinstance(value_score, str):
            try:
                value_score = float(value_score)
            except (ValueError, TypeError):
                value_score = 0

        if quality_score >= 7.0 and value_score >= 6.0:
            high_quality_posts.append(p)

    print(f"✅ Found {len(high_quality_posts)} high-quality Reddit posts")

    if not high_quality_posts:
        print("⚠️  No high-quality Reddit posts (quality >= 7.0, value >= 6.0)")
        print("💡 Using all available posts...")
        high_quality_posts = reddit_posts[:20]

    # Generate rewrites for each persona
    for persona_key, config in persona_configs.items():
        print("\n" + "=" * 80)
        print(f"🎭 GENERATING REWRITES FOR: {config['name'].upper()}")
        print("=" * 80)

        # Open curation file
        curation_file = curation_dir / f"{persona_key}_curated.jsonl"

        # Track stats
        success_count = 0
        error_count = 0
        skipped_count = 0

        # Filter posts for this persona (by subreddit if available)
        persona_posts = high_quality_posts[:15]  # Take first 15 for now

        for i, post in enumerate(persona_posts, 1):
            print(f"\n[{i}/{len(persona_posts)}] Processing post: {post.get('post_id')}")

            try:
                # Get full content
                title = post.get('title', '')
                content = post.get('content', '')

                # Combine title and content for Reddit posts
                full_content = f"{title}\n\n{content}" if title and content else (content or title)

                if not full_content or len(full_content) < 50:
                    print(f"   ⚠️  Skipping - content too short ({len(full_content)} chars)")
                    skipped_count += 1
                    continue

                # Prepare analyzed content format
                analyzed_content = {
                    "post_id": post.get("post_id"),
                    "platform": "reddit",
                    "content": full_content,
                    "summary": post.get("ai_summary") or full_content[:200],
                    "category": post.get("topic", "General"),
                    "topics": post.get("tags", []),
                    "key_concepts": post.get("key_concepts", []),
                    "rewrite_angles": [{
                        "persona": persona_key,
                        "angle": f"Reframe for {persona_key} audience",
                        "tone": "authentic",
                        "platform_fit": "single_post",
                        "hook": "",
                        "key_points": [],
                        "call_to_action": ""
                    }]
                }

                # Generate rewrite
                result = await rewriter.rewrite_analyzed_post(
                    analyzed_content=analyzed_content,
                    persona=persona_key,
                    platform="twitter"  # Target platform
                )

                if "error" in result:
                    print(f"   ❌ Error: {result['error']}")
                    error_count += 1
                    continue

                # Check if it's an error propagation issue
                rewritten = result['rewritten_content'].lower()
                from src.utils.error_handler import is_rate_limit_error_in_content

                if is_rate_limit_error_in_content(rewritten):
                    print(f"   ⚠️  Skipping - appears to be error content")
                    error_count += 1
                    continue

                # Display the rewrite
                print(f"   ✅ Success!")
                print(f"   📏 Length: {result['content_length']} chars")
                print(f"   ⭐ Quality: {result['quality_score']}/100 ({result['quality_rating']})")
                print(f"   📝 Preview: {result['rewritten_content'][:100]}...")

                # Prepare curated post entry
                curated_entry = {
                    "created_at": datetime.now().isoformat(),
                    "persona": persona_key,
                    "persona_name": result['persona_name'],
                    "platform": result['platform'],
                    "original_post_id": result['original_post_id'],
                    "original_platform": "reddit",
                    "content": result['rewritten_content'],
                    "rewritten_content": result['rewritten_content'],
                    "content_type": result.get('content_type', 'unknown'),
                    "quality_score": result['quality_score'],
                    "quality_rating": result['quality_rating'],
                    "length": result['content_length'],
                    "original_url": post.get('url', ''),
                    "original_title": post.get('title', ''),
                    "tags": post.get('tags', []),
                    "value_score": post.get('value_score', 0),
                    "source": "reddit_curation"
                }

                # Save to curation file (append)
                with open(curation_file, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(curated_entry, ensure_ascii=False) + '\n')

                success_count += 1

            except Exception as e:
                print(f"   ❌ Exception: {e}")
                logger.error(f"Error processing post {post.get('post_id')}: {e}", exc_info=True)
                error_count += 1

        # Persona summary
        print("\n" + "-" * 80)
        print(f"📊 {config['name'].upper()} SUMMARY:")
        print(f"   ✅ Success: {success_count}")
        print(f"   ❌ Errors: {error_count}")
        print(f"   ⏭️  Skipped: {skipped_count}")
        print(f"   💾 Saved to: {curation_file}")

    # Final summary
    print("\n" + "=" * 80)
    print("✅ REDDIT CURATION COMPLETE!")
    print("=" * 80)
    print("\n📁 Curated posts saved to:")
    for persona_key in persona_configs.keys():
        curation_file = curation_dir / f"{persona_key}_curated.jsonl"
        if curation_file.exists():
            # Count lines
            with open(curation_file, 'r', encoding='utf-8') as f:
                count = sum(1 for line in f if line.strip())
            print(f"   • {curation_file} ({count} total posts)")

    print("\n💡 View curated posts in the web UI:")
    print("   → Publishing Page → 💎 Curated tab")


if __name__ == "__main__":
    asyncio.run(generate_reddit_rewrites())
