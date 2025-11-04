#!/usr/bin/env python3
"""
Generate 5 rewrites from ACTUAL DATABASE POSTS (Supabase)
"""
import asyncio
import os
import re
from supabase import create_client

from src.publishing.rewriter import ContentRewriter
from src.publishing.persona_matcher import PersonaMatcher


async def get_5_real_rewrites():
    """Fetch 5 real posts from DB and rewrite them"""

    print("\n" + "="*100)
    print("🎨 5 REWRITES FROM ACTUAL DATABASE POSTS")
    print("="*100 + "\n")

    # Connect to Supabase
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')

    if not url or not key:
        print("❌ Missing Supabase credentials")
        return

    supabase = create_client(url, key)

    # Fetch 20 recent posts (to have variety)
    print("📡 Fetching posts from Supabase...")
    response = supabase.table('posts').select('*').limit(20).execute()

    if not response.data:
        print("❌ No posts found in database")
        return

    print(f"✅ Found {len(response.data)} posts in database\n")

    # Initialize components
    matcher = PersonaMatcher()
    rewriter = ContentRewriter()

    # Emoji/hashtag patterns
    emoji_pattern = re.compile('['
        u'\U0001F600-\U0001F64F'
        u'\U0001F300-\U0001F5FF'
        u'\U0001F680-\U0001F6FF'
        u'\U0001F1E0-\U0001F1FF'
        u'\U00002702-\U000027B0'
        u'\U000024C2-\U0001F251'
        u'\U0001F900-\U0001F9FF'
        u'\U0001FA70-\U0001FAFF'
        ']+', flags=re.UNICODE)
    hashtag_pattern = re.compile(r'#\w+')

    results = []
    posts_processed = 0

    for db_post in response.data:
        if posts_processed >= 5:
            break

        # Get content
        content = db_post.get('content') or db_post.get('summary', '')
        if not content or len(content) < 50:
            continue

        # Create analyzed structure
        analyzed = {
            'content': content,
            'summary': content[:200],
            'category': db_post.get('category', 'General'),
            'topics': db_post.get('topics', []),
            'key_concepts': db_post.get('key_concepts', []),
            'complexity': db_post.get('complexity', 'Intermediate'),
            'platform': db_post.get('platform', 'unknown'),
            'post_id': db_post.get('id'),
            'url': db_post.get('url', ''),
            'discovery_signals': {'viral_potential': 60},
            'rewrite_angles': []
        }

        # Match to persona
        matches = matcher.match_personas(analyzed)

        if not matches:
            continue

        # matches returns list of tuples: (persona_id, score, reason)
        persona_id, score, reason = matches[0]
        persona_name = persona_id.replace('_', ' ').title()

        posts_processed += 1

        print(f"\n{'='*100}")
        print(f"POST #{posts_processed} FROM DB (Platform: {analyzed['platform'].upper()})")
        print("="*100)

        print(f"\n📝 ORIGINAL:")
        print("-" * 100)
        print(content[:500] + ("..." if len(content) > 500 else ""))
        print("-" * 100)

        print(f"\n🎯 MATCHED TO: {persona_name.upper()} (score: {score})")
        print(f"   Reason: {reason}")

        # Add rewrite angle for matched persona
        key_concepts = analyzed.get('key_concepts') or []
        analyzed['rewrite_angles'] = [{
            'persona': persona_id,
            'angle': f'Rewrite in {persona_name} voice',
            'hook': content[:100],
            'key_points': key_concepts[:3] if key_concepts else [],
            'call_to_action': 'Engage with audience',
            'target_audience': 'General',
            'tone': 'Natural',
            'platform_fit': 'twitter_thread'
        }]

        # Rewrite
        print(f"\n✍️  REWRITING AS {persona_name.upper()}...")
        result = await rewriter.rewrite_analyzed_post(analyzed, persona_id, 'twitter')

        rewritten = result.get('rewritten_content', '')

        print(f"\n✨ {persona_name.upper()} REWRITE:")
        print("-" * 100)
        print(rewritten)
        print("-" * 100)

        # Quality check
        emojis = emoji_pattern.findall(rewritten)
        hashtags = hashtag_pattern.findall(rewritten)

        print(f"\n📊 QUALITY:")
        print(f"   Emojis: {len(emojis)} {'✅ CLEAN' if len(emojis) == 0 else '⚠️ ' + str(emojis)}")
        print(f"   Hashtags: {len(hashtags)} {'✅ CLEAN' if len(hashtags) == 0 else '⚠️ ' + str(hashtags)}")

        results.append({
            'platform': analyzed['platform'],
            'persona': persona_name,
            'original_length': len(content),
            'rewrite_length': len(rewritten),
            'emojis': len(emojis),
            'hashtags': len(hashtags)
        })

    # Summary
    print("\n\n" + "="*100)
    print("📊 SUMMARY - REAL DATABASE POSTS")
    print("="*100 + "\n")

    total_emojis = sum(r['emojis'] for r in results)
    total_hashtags = sum(r['hashtags'] for r in results)

    for i, r in enumerate(results, 1):
        status = "✅" if (r['emojis'] == 0 and r['hashtags'] == 0) else "⚠️"
        print(f"{status} Post #{i} ({r['platform']}) → {r['persona']}: {r['emojis']} emojis, {r['hashtags']} hashtags")

    print(f"\nTOTAL: {total_emojis} emojis, {total_hashtags} hashtags across {len(results)} real DB posts")

    if total_emojis == 0 and total_hashtags == 0:
        print("\n🎉 PERFECT! 100% PERSONAL VOICE ON REAL DATA")

    print("\n" + "="*100 + "\n")


if __name__ == "__main__":
    asyncio.run(get_5_real_rewrites())
