#!/usr/bin/env python3
"""
Generate 5 readable rewrites across all 3 personas
Uses Vikhr for Russian (Qronoya) and OpenAI for English
"""
import asyncio
import os
from datetime import datetime
from pathlib import Path

from src.publishing.rewriter import ContentRewriter
from src.publishing.persona_matcher import PersonaMatcher
from src.core.analysis.intelligent_content_analyzer import IntelligentContentAnalyzer
from supabase import create_client


# Sample posts for testing
SAMPLE_POSTS = [
    {
        "title": "Chinese AI startups catching up",
        "content": "Chinese AI startups: 1/6th of US funding, bad press, sanctions, brain drain, communism, little English proficiency. But after using Manus AI, Deepseek, Trae, Kling, Vidu, & Ying, I think the US is in trouble. At this pace, China will dominate AI.",
        "category": "Technology",
        "source": "twitter"
    },
    {
        "title": "Vulnerability in dating",
        "content": "Had an interesting conversation on a date last night. We talked about vulnerability and how hard it is to be truly open with someone new. Made me think about how we all wear masks to protect ourselves.",
        "category": "Relationships",
        "source": "twitter"
    },
    {
        "title": "Base L2 airdrop",
        "content": "New Base Layer 2 protocol launching airdrop. Early adopters who stake USDC and interact with the protocol will be eligible for rewards. Estimated allocation up to $2000 per wallet.",
        "category": "Cryptocurrency",
        "source": "twitter"
    },
    {
        "title": "Career transition advice",
        "content": "Many developers ask how to transition into senior roles. Here are the key things: take ownership of projects, mentor juniors, think about architecture not just code, communicate effectively with non-technical stakeholders.",
        "category": "Career",
        "source": "twitter"
    },
    {
        "title": "Solana DeFi opportunities",
        "content": "Solana DeFi is heating up. New lending protocols offering 15-20% APY on stablecoins. Low gas fees make it attractive for smaller wallets. But always DYOR - high yields come with risks.",
        "category": "Cryptocurrency",
        "source": "twitter"
    }
]


async def rewrite_5_posts():
    """Rewrite 5 sample posts and display in readable format"""

    print("\n" + "="*100)
    print("🎨 GENERATING 5 REWRITES - PERSONAL VOICE EDITION")
    print("="*100 + "\n")

    # Initialize components
    analyzer = IntelligentContentAnalyzer()
    matcher = PersonaMatcher()
    rewriter = ContentRewriter()

    results = []

    for i, post_data in enumerate(SAMPLE_POSTS, 1):
        print(f"\n{'='*100}")
        print(f"POST #{i}: {post_data['title']}")
        print("="*100)

        # Analyze
        print(f"\n📝 ORIGINAL:")
        print("-" * 100)
        print(post_data['content'])
        print("-" * 100)

        analyzed = await analyzer.analyze_content({
            'content': post_data['content'],
            'post_id': f'demo_{i}',
            'platform': post_data['source'],
            'url': f'https://example.com/post/{i}'
        })

        # Match persona
        matches = matcher.match_personas(analyzed)

        if not matches:
            print("\n❌ No persona matched for this content")
            continue

        best_match = matches[0]
        persona_id = best_match['persona']
        persona_name = best_match['name']
        score = best_match['score']

        print(f"\n🎯 MATCHED TO: {persona_name.upper()} (score: {score})")
        print(f"   Reason: {best_match['reason']}")

        # Rewrite
        print(f"\n✍️  REWRITING...")
        result = await rewriter.rewrite_analyzed_post(analyzed, persona_id, 'twitter')

        rewritten_content = result.get('rewritten_content', '')

        # Display rewrite
        print(f"\n✨ {persona_name.upper()} REWRITE:")
        print("-" * 100)
        print(rewritten_content)
        print("-" * 100)

        # Check for emojis/hashtags
        import re
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

        emojis = emoji_pattern.findall(rewritten_content)
        hashtags = hashtag_pattern.findall(rewritten_content)

        print(f"\n📊 QUALITY CHECK:")
        print(f"   Emojis: {len(emojis)} {'✅ CLEAN' if len(emojis) == 0 else '⚠️ ' + str(emojis)}")
        print(f"   Hashtags: {len(hashtags)} {'✅ CLEAN' if len(hashtags) == 0 else '⚠️ ' + str(hashtags)}")

        results.append({
            'original': post_data['content'],
            'persona': persona_name,
            'rewrite': rewritten_content,
            'emojis': len(emojis),
            'hashtags': len(hashtags)
        })

    # Summary
    print("\n\n" + "="*100)
    print("📊 SUMMARY")
    print("="*100 + "\n")

    total_emojis = sum(r['emojis'] for r in results)
    total_hashtags = sum(r['hashtags'] for r in results)

    for i, result in enumerate(results, 1):
        print(f"{i}. {result['persona']}: {result['emojis']} emojis, {result['hashtags']} hashtags")

    print(f"\nTOTAL: {total_emojis} emojis, {total_hashtags} hashtags across 5 posts")

    if total_emojis == 0 and total_hashtags == 0:
        print("\n🎉 PERFECT! 100% PERSONAL VOICE - NO BRAND SPAM")

    print("\n" + "="*100 + "\n")


if __name__ == "__main__":
    asyncio.run(rewrite_5_posts())
