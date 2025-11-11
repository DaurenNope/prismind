#!/usr/bin/env python3
"""
Generate full batch of curated rewrites for both personas from ALL Supabase posts
(Twitter, Reddit, Threads, etc.)
"""
import asyncio
import json
import os
import logging
import time
from pathlib import Path
from datetime import datetime
from supabase import create_client
from src.publishing.rewriter import ContentRewriter
from src.utils.error_handler import is_rate_limit_error_in_content

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def generate_full_curated_batch():
    """
    Generate rewrites for BOTH personas from ALL posts in Supabase
    """
    print("=" * 80)
    print("GENERATE FULL CURATED BATCH - ALL POSTS, BOTH PERSONAS")
    print("=" * 80)

    # Initialize
    rewriter = ContentRewriter()

    # Connect to Supabase
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_KEY')

    if not url or not key:
        print("❌ Missing SUPABASE_URL or SUPABASE_KEY")
        return

    supabase = create_client(url, key)

    # Create curation directory
    curation_dir = Path("data/curated_posts")
    curation_dir.mkdir(parents=True, exist_ok=True)

    # Persona configuration
    personas = {
        "qronoya": {
            "name": "Qronoya",
            "description": "Tech/business insights, analytical, Russian",
            "target_topics": ["tech", "business", "ai", "startups", "programming"]
        },
        "aspandead": {
            "name": "Aspandead",
            "description": "Emotional/relationships, vulnerable, Russian",
            "target_topics": ["relationships", "emotions", "personal", "life", "dating"]
        }
    }

    # Fetch ALL posts from Supabase
    print("\n📊 Fetching ALL posts from Supabase...")
    try:
        # Get posts with actual content (not just URLs)
        response = supabase.table('posts')\
            .select('*')\
            .not_.is_('content', 'null')\
            .order('created_at', desc=True)\
            .limit(100)\
            .execute()

        all_posts = response.data or []
        print(f"✅ Found {len(all_posts)} total posts in Supabase\n")

    except Exception as e:
        print(f"❌ Error fetching from Supabase: {e}")
        return

    if not all_posts:
        print("❌ No posts found in Supabase")
        return

    # Filter to posts with substantial text content
    good_posts = []
    for p in all_posts:
        content = p.get('content') or ''
        title = p.get('title') or ''

        # Skip if content is just a URL or too short
        if content and len(content) > 50 and not content.startswith('http'):
            good_posts.append(p)
        elif title and len(title) > 30:  # Allow posts with good titles
            good_posts.append(p)

    print(f"✅ Found {len(good_posts)} posts with substantial content\n")

    # Show platform breakdown
    platform_counts = {}
    for p in good_posts:
        platform = p.get('platform', 'unknown')
        platform_counts[platform] = platform_counts.get(platform, 0) + 1

    print("📊 Platform breakdown:")
    for platform, count in sorted(platform_counts.items()):
        print(f"   • {platform}: {count} posts")
    print()

    # Generate rewrites for EACH persona
    for persona_key, persona_config in personas.items():
        print("\n" + "=" * 80)
        print(f"🎭 GENERATING REWRITES FOR: {persona_config['name'].upper()}")
        print(f"   {persona_config['description']}")
        print("=" * 80)

        # Open curation file (append mode to keep existing posts)
        curation_file = curation_dir / f"{persona_key}_curated.jsonl"

        # Track stats
        success_count = 0
        error_count = 0
        skipped_count = 0
        ollama_skipped = 0  # Track how many we skip due to Ollama

        # Limit per persona to avoid excessive API usage
        posts_to_process = good_posts[:30]  # Process up to 30 posts per persona

        print(f"\n📝 Processing {len(posts_to_process)} posts for {persona_config['name']}...")
        print(f"⏱️  Rate limiting: 3s delay between requests to stay under API limits\n")

        for i, post in enumerate(posts_to_process, 1):
            post_id = post.get('post_id', 'unknown')
            platform = post.get('platform', 'unknown')

            print(f"[{i}/{len(posts_to_process)}] {platform.upper()}: {post_id[:20]}...")

            try:
                # Get content
                title = post.get('title') or ''
                content = post.get('content') or ''

                # Combine title + content
                if title and content:
                    full_content = f"{title}\n\n{content}"
                else:
                    full_content = content or title

                if not full_content or len(full_content) < 30:
                    print(f"   ⏭️  Skipping - content too short ({len(full_content)} chars)")
                    skipped_count += 1
                    continue

                # Prepare analyzed content format
                analyzed_content = {
                    "post_id": post_id,
                    "platform": platform,
                    "content": full_content,
                    "summary": full_content[:250],
                    "category": post.get("topic") or "General",
                    "topics": post.get("tags") or [],
                    "key_concepts": post.get("key_concepts") or [],
                    "rewrite_angles": [{
                        "persona": persona_key,
                        "angle": f"Reframe for {persona_key} audience",
                        "tone": "authentic",
                        "platform_fit": "single_post"
                    }]
                }

                # Generate rewrite
                result = await rewriter.rewrite_analyzed_post(
                    analyzed_content=analyzed_content,
                    persona=persona_key,
                    platform="twitter"  # Target platform
                )

                # Check for errors
                if "error" in result:
                    print(f"   ❌ Error: {result['error']}")
                    error_count += 1
                    continue

                # Check for error propagation
                if is_rate_limit_error_in_content(result['rewritten_content']):
                    print(f"   ⚠️  Skipping - error content detected")
                    error_count += 1
                    continue

                # 🚨 QUALITY FILTER: Only save Gemini/Mistral outputs (skip Ollama)
                model_used = result.get('model_used', 'unknown')
                if 'ollama' in model_used.lower() or 'qwen' in model_used.lower():
                    print(f"   ⏭️  Skipping Ollama output (low quality) - model: {model_used}")
                    ollama_skipped += 1
                    continue

                # Success!
                print(f"   ✅ {result['content_length']} chars | Quality: {result['quality_score']}/100 | Model: {model_used}")

                # Prepare curated entry (with model tracking)
                curated_entry = {
                    "created_at": datetime.now().isoformat(),
                    "persona": persona_key,
                    "persona_name": result['persona_name'],
                    "platform": result['platform'],
                    "original_post_id": result['original_post_id'],
                    "original_platform": platform,
                    "content": result['rewritten_content'],
                    "rewritten_content": result['rewritten_content'],
                    "content_type": result.get('content_type', 'unknown'),
                    "quality_score": result['quality_score'],
                    "quality_rating": result['quality_rating'],
                    "length": result['content_length'],
                    "model_used": model_used,  # Track which model generated this
                    "original_url": post.get('url', ''),
                    "original_title": post.get('title', ''),
                    "tags": post.get('tags', []),
                    "value_score": post.get('value_score', 0),
                    "source": f"{platform}_curation",
                    "source_platform": platform
                }

                # Save to curation file (append)
                with open(curation_file, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(curated_entry, ensure_ascii=False) + '\n')

                success_count += 1

                # Rate limiting: 3 seconds between requests (20 req/min with 2 keys = well under 15 RPM limit)
                if i < len(posts_to_process):  # Don't sleep after last post
                    print(f"   ⏱️  Waiting 3s (rate limiting)...")
                    await asyncio.sleep(3)

            except Exception as e:
                print(f"   ❌ Exception: {e}")
                logger.error(f"Error processing {post_id}: {e}", exc_info=True)
                error_count += 1

        # Persona summary
        print("\n" + "-" * 80)
        print(f"📊 {persona_config['name'].upper()} SUMMARY:")
        print(f"   ✅ Success (Gemini/Mistral only): {success_count}")
        print(f"   ❌ Errors: {error_count}")
        print(f"   ⏭️  Skipped (too short): {skipped_count}")
        print(f"   🚫 Skipped (Ollama/low quality): {ollama_skipped}")

        # Count total posts in file
        if curation_file.exists():
            with open(curation_file, 'r', encoding='utf-8') as f:
                total_count = sum(1 for line in f if line.strip())
            print(f"   💾 Total in file: {total_count} posts")
            print(f"   📁 Saved to: {curation_file}")

    # Final summary
    print("\n" + "=" * 80)
    print("✅ FULL BATCH GENERATION COMPLETE!")
    print("=" * 80)

    print("\n📁 Curated posts saved to:")
    for persona_key in personas.keys():
        curation_file = curation_dir / f"{persona_key}_curated.jsonl"
        if curation_file.exists():
            with open(curation_file, 'r', encoding='utf-8') as f:
                count = sum(1 for line in f if line.strip())
            print(f"   • {curation_file} ({count} total posts)")

    print("\n💡 View in web UI:")
    print("   1. Run: streamlit run src/web/app.py")
    print("   2. Go to: Publishing Page → 💎 Curated tab")
    print("   3. Filter by persona (qronoya/aspandead)")
    print("   4. Click 🚀 Post Now to publish")


if __name__ == "__main__":
    asyncio.run(generate_full_curated_batch())
