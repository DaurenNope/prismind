#!/usr/bin/env python3
"""
Regenerate qronoya voice examples using the fixed rewriter
"""
import asyncio
import json
import os

from dotenv import load_dotenv
from supabase import create_client

from src.publishing.rewriter import ContentRewriter

load_dotenv()


async def regenerate_examples():
    supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
    rewriter = ContentRewriter()

    print("🔄 Regenerating qronoya voice examples with fixed rewriter...\n")

    # Get diverse Reddit posts (different topics, lengths, styles)
    response = (
        supabase.table("posts")
        .select("*")
        .eq("platform", "reddit")
        .not_.is_("content", "null")
        .order("created_at", desc=True)
        .limit(30)
        .execute()
    )

    posts = response.data
    print(f"✅ Found {len(posts)} Reddit posts\n")

    new_examples = []

    for i, post in enumerate(posts[:25], 1):  # Generate 25 examples
        post_id = post.get("post_id", "unknown")
        title = post.get("title", "")
        content = post.get("content", "")

        # Skip very short or very long posts
        if len(content) < 50 or len(content) > 2000:
            continue

        print(f"[{i}/25] Processing: {title[:60]}...")

        analyzed_content = {
            "post_id": post_id,
            "platform": "reddit",
            "content": content,
            "title": title,
            "summary": content[:200],
            "category": post.get("category", "tech"),
            "topics": post.get("topics", []) or ["general"],
            "key_concepts": [],
            "rewrite_angles": [
                {
                    "persona": "qronoya",
                    "angle": "Reframe for qronoya audience",
                    "tone": "analytical",
                    "platform_fit": "single_post",
                }
            ],
        }

        try:
            result = await rewriter.rewrite_analyzed_post(
                analyzed_content=analyzed_content, persona="qronoya", platform="twitter"
            )

            if "error" not in result:
                rewritten = result.get("rewritten_content", "")
                quality = result.get("quality_score", 0)

                if quality >= 90 and len(rewritten) > 50:  # Only keep high quality
                    example = {
                        "id": f"regenerated_{i}",
                        "content": rewritten,
                        "content_type": "professional_analysis",
                        "structure": "direct_statement",
                        "tone": "analytical",
                        "notes": f"Regenerated from Reddit: {title[:40]}...",
                    }
                    new_examples.append(example)
                    print(f"   ✅ Quality: {quality}/100 - Added")
                    print(f"   📝 {rewritten[:100]}...\n")
                else:
                    print(f"   ⚠️  Quality: {quality}/100 - Skipped\n")
            else:
                print(f"   ❌ Error: {result['error'][:50]}\n")

        except Exception as e:
            print(f"   ❌ Exception: {str(e)[:50]}\n")
            continue

        # Don't overwhelm API
        if i % 5 == 0:
            print("⏸️  Pausing 10s to avoid rate limits...")
            await asyncio.sleep(10)

    print(f"\n✅ Generated {len(new_examples)} new high-quality examples\n")

    # Save to file
    output_path = "config/personas/qronoya_examples.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(new_examples, f, ensure_ascii=False, indent=2)

    print(f"💾 Saved to {output_path}")
    print(f"📊 Total examples: {len(new_examples)}")

    # Show samples
    print("\n📋 Sample of new examples:")
    for ex in new_examples[:3]:
        print(f"\n{ex['id']}:")
        print(f"  {ex['content']}")


if __name__ == "__main__":
    asyncio.run(regenerate_examples())
