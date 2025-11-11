#!/usr/bin/env python3
"""
Rewrite Reddit posts from Supabase with more natural, less AI-sounding voice
"""
import asyncio
import os
from supabase import create_client
from src.publishing.rewriter import ContentRewriter


async def rewrite_from_supabase():
    """Pull Reddit posts from Supabase and rewrite 2-3 with natural voice"""

    print("=" * 80)
    print("REWRITE REDDIT POSTS FROM SUPABASE")
    print("=" * 80)

    # Connect to Supabase
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_KEY')

    if not url or not key:
        print("❌ Missing SUPABASE_URL or SUPABASE_KEY")
        return

    supabase = create_client(url, key)
    rewriter = ContentRewriter()

    # Get Reddit posts with content (not just URLs)
    print("\n📊 Fetching Reddit posts from Supabase...")
    response = supabase.table('posts')\
        .select('*')\
        .eq('platform', 'reddit')\
        .not_.is_('content', 'null')\
        .limit(20)\
        .execute()

    posts = response.data or []
    print(f"✅ Found {len(posts)} Reddit posts in Supabase\n")

    if not posts:
        print("❌ No Reddit posts with content found")
        return

    # Filter to posts with actual text content (not just image URLs)
    good_posts = []
    for p in posts:
        content = p.get('content', '')
        # Skip if content is just an image URL
        if content and len(content) > 100 and not content.startswith('http'):
            good_posts.append(p)

    print(f"✅ Found {len(good_posts)} posts with actual text content\n")

    # Take first 3
    test_posts = good_posts[:3]

    for i, post in enumerate(test_posts, 1):
        print(f"\n{'='*80}")
        print(f"POST #{i}/{len(test_posts)}")
        print(f"{'='*80}")

        title = post.get('title') or 'No title'
        content = post.get('content') or ''
        author = post.get('author') or 'Unknown'

        # Safe display with None checks
        title_display = title[:80] if title and len(title) > 80 else title
        content_preview = content[:200] if content and len(content) > 200 else content

        print(f"📌 Title: {title_display}")
        print(f"👤 Author: {author}")
        print(f"📝 Content: {content_preview}...")
        print(f"📏 Length: {len(content)} chars")

        # Combine title + content
        full_content = f"{title}\n\n{content}" if title and content else (content or title)

        print(f"\n🔄 Rewriting with qronoya voice (natural, less AI)...\n")

        # Prepare for rewriting
        analyzed_content = {
            "post_id": post.get("post_id"),
            "platform": "reddit",
            "content": full_content,
            "summary": full_content[:250],
            "category": "Discussion",
            "topics": [],
            "key_concepts": [],
            "rewrite_angles": [{
                "persona": "qronoya",
                "angle": "Tech insight",
                "tone": "conversational",
                "platform_fit": "single_post"
            }]
        }

        try:
            result = await rewriter.rewrite_analyzed_post(
                analyzed_content=analyzed_content,
                persona="qronoya",
                platform="twitter"
            )

            if "error" in result:
                print(f"   ❌ Error: {result['error']}")
                continue

            # Success
            print(f"   ✅ Success!")
            print(f"   📏 Length: {result['content_length']} chars")
            print(f"   ⭐ Quality: {result['quality_score']}/100")
            print(f"\n   📝 REWRITTEN:")
            print(f"   {'-'*76}")

            # Display with proper line breaks
            for line in result['rewritten_content'].split('\n'):
                print(f"   {line}")

            print(f"   {'-'*76}\n")

        except Exception as e:
            print(f"   ❌ Exception: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 80)
    print("✅ DONE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(rewrite_from_supabase())
