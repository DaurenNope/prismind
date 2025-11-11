#!/usr/bin/env python3
"""
Generate actual rewrites from database posts and save to curation for each persona
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


async def generate_and_curate_rewrites():
    """
    Generate rewrites from database posts and save to curation system
    """
    print("=" * 80)
    print("GENERATE & CURATE REWRITES FOR ALL PERSONAS")
    print("=" * 80)

    # Initialize
    db = DatabaseOperations()
    rewriter = ContentRewriter()

    # Create curation directory
    curation_dir = Path("data/curated_posts")
    curation_dir.mkdir(parents=True, exist_ok=True)

    # Define personas to generate for
    # NOTE: Only qronoya for now - aspandead needs relationship/emotional content in database
    personas = ["qronoya"]

    # Get posts from database (high value posts that are ready for rewrite)
    print("\n📊 Fetching posts from database...")

    # Fetch posts with high value score (min_score filters by value_score)
    posts = db.get_posts(
        limit=20,
        min_score=7.0  # High value posts only
    )

    if not posts:
        print("❌ No high-value posts found in database")
        print("💡 Try collecting some posts first or lowering the score threshold")
        return

    # Filter to get best quality posts
    high_quality_posts = []
    for p in posts:
        quality_score = p.get('quality_score', 0)
        # Handle string scores (convert to float)
        if isinstance(quality_score, str):
            try:
                quality_score = float(quality_score)
            except (ValueError, TypeError):
                quality_score = 0
        if quality_score >= 7.0:
            high_quality_posts.append(p)

    if not high_quality_posts:
        print("⚠️  No posts with quality_score >= 7.0, using all fetched posts")
        high_quality_posts = posts

    posts = high_quality_posts[:10]  # Take top 10
    print(f"✅ Found {len(posts)} high-value, high-quality posts")

    # Generate rewrites for each persona
    for persona in personas:
        print("\n" + "=" * 80)
        print(f"🎭 GENERATING REWRITES FOR: {persona.upper()}")
        print("=" * 80)

        # Open curation file for this persona
        curation_file = curation_dir / f"{persona}_curated.jsonl"

        # Track stats
        success_count = 0
        error_count = 0

        for i, post in enumerate(posts, 1):
            print(f"\n[{i}/{len(posts)}] Processing post: {post.get('post_id')}")

            try:
                # Prepare analyzed content format expected by rewriter
                analyzed_content = {
                    "post_id": post.get("post_id"),
                    "platform": post.get("platform"),
                    "content": post.get("content"),
                    "summary": post.get("ai_summary") or post.get("content", "")[:200],
                    "category": post.get("topic", "General"),
                    "topics": post.get("tags", []),
                    "key_concepts": post.get("key_concepts", []),
                    "rewrite_angles": [{
                        "persona": persona,
                        "angle": f"Reframe for {persona} audience",
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
                    persona=persona,
                    platform="twitter"
                )

                if "error" in result:
                    print(f"   ❌ Error: {result['error']}")
                    error_count += 1
                    continue

                # Filter out error posts (posts that mention errors or API issues)
                rewritten = result['rewritten_content'].lower()
                error_keywords = ['error:', 'api ключи кончились', 'api keys', 'exhausted', 'rate limit']
                if any(keyword in rewritten for keyword in error_keywords):
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
                    "persona": persona,
                    "persona_name": result['persona_name'],
                    "platform": result['platform'],
                    "original_post_id": result['original_post_id'],
                    "original_platform": result['original_platform'],
                    "content": result['rewritten_content'],
                    "rewritten_content": result['rewritten_content'],
                    "content_type": result.get('content_type', 'unknown'),
                    "quality_score": result['quality_score'],
                    "quality_rating": result['quality_rating'],
                    "length": result['content_length'],
                    "original_url": post.get('url', ''),
                    "original_author": post.get('author', ''),
                    "tags": post.get('tags', []),
                    "value_score": post.get('value_score', 0),
                    "source": "automated_curation"
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
        print(f"📊 {persona.upper()} SUMMARY:")
        print(f"   ✅ Success: {success_count}")
        print(f"   ❌ Errors: {error_count}")
        print(f"   💾 Saved to: {curation_file}")

    # Final summary
    print("\n" + "=" * 80)
    print("✅ CURATION COMPLETE!")
    print("=" * 80)
    print("\n📁 Curated posts saved to:")
    for persona in personas:
        curation_file = curation_dir / f"{persona}_curated.jsonl"
        if curation_file.exists():
            # Count lines
            with open(curation_file, 'r', encoding='utf-8') as f:
                count = sum(1 for line in f if line.strip())
            print(f"   • {curation_file} ({count} posts)")

    print("\n💡 View curated posts in the web UI:")
    print("   → Publishing Page → 💎 Curated tab")


if __name__ == "__main__":
    asyncio.run(generate_and_curate_rewrites())
