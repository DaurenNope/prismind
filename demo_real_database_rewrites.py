#!/usr/bin/env python3
"""
Demo: Real Database Posts → Authentic Personal Voice Rewrites
NO emoji spam, NO hashtag spam, NO brand voice - PERSONAL profiles only
"""

import asyncio
import os
from supabase import create_client
from src.publishing.rewriter import ContentRewriter
from src.publishing.persona_matcher import get_persona_matcher


async def demo_real_rewrites():
    """Show rewrites of ACTUAL database posts"""

    # Connect to Supabase
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
    supabase = create_client(url, key)

    # Get real posts
    response = supabase.table('posts').select('*').limit(20).execute()

    rewriter = ContentRewriter()
    matcher = get_persona_matcher()

    print("\n" + "=" * 100)
    print("REAL DATABASE POSTS → AUTHENTIC PERSONAL VOICE REWRITES")
    print("=" * 100 + "\n")

    shown = 0
    for post in response.data:
        content = post.get('content', post.get('text', ''))
        if not content or len(content) < 100:
            continue

        # Create analyzed content structure
        analyzed = {
            'content': content,
            'summary': content[:200],
            'category': post.get('category', 'General'),
            'topics': [],
            'key_concepts': [],
            'complexity': 'Intermediate',
            'discovery_signals': {'viral_potential': 50}
        }

        # Match to personas
        matches = matcher.match_personas(analyzed)
        if not matches:
            continue

        persona_id, score, reason = matches[0]

        # Prepare rewrite angle
        analyzed['rewrite_angles'] = [{
            'persona': persona_id,
            'angle': f'Rewrite in {persona_id} voice',
            'hook': content[:80],
            'key_points': ['Main idea', 'Supporting points', 'Conclusion'],
            'tone': 'natural, personal',
            'call_to_action': '',
            'platform_fit': 'twitter_thread'
        }]

        print("=" * 100)
        print(f"POST FROM DATABASE (Platform: {post.get('platform', 'unknown').upper()})")
        print("=" * 100 + "\n")

        print("📄 ORIGINAL POST:")
        print("-" * 100)
        print(content[:400] + ('...' if len(content) > 400 else ''))
        print("-" * 100)
        print(f"\n🎯 Matched to: {persona_id.upper()} ({score:.0f} points)")
        print(f"   Reason: {reason}\n")

        # Rewrite
        result = await rewriter.rewrite_analyzed_post(analyzed, persona_id, 'twitter')

        print(f"✍️  {persona_id.upper()} REWRITE (Personal, Natural Voice):")
        print("-" * 100)
        print(result['rewritten_content'])
        print("-" * 100)
        print()

        shown += 1
        if shown >= 3:
            break

    print("\n" + "=" * 100)
    print("KEY POINTS:")
    print("  • Used REAL posts from your Supabase database")
    print("  • Matched to correct profile using strict routing")
    print("  • Rewrites in PERSONAL voice (not brand/corporate)")
    print("  • Minimal emojis - only when natural")
    print("  • NO hashtag spam")
    print("  • Extracts core idea, rewrites authentically")
    print("=" * 100 + "\n")


if __name__ == "__main__":
    asyncio.run(demo_real_rewrites())
