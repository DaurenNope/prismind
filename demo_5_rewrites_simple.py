#!/usr/bin/env python3
"""
Generate 5 readable rewrites - simplified version
"""
import asyncio
import re
from dotenv import load_dotenv

# Load environment variables (override system env)
load_dotenv(override=True)

from src.publishing.rewriter import ContentRewriter


# Sample posts for testing (manually assigned to personas)
SAMPLE_POSTS = [
    {
        "title": "Chinese AI startups",
        "content": "Chinese AI startups: 1/6th of US funding, bad press, sanctions. But after using Manus AI, Deepseek, Trae, Kling, Vidu, I think the US is in trouble. At this pace, China will dominate AI.",
        "persona": "qronoya",  # Tech/AI content
        "category": "Technology"
    },
    {
        "title": "Vulnerability in dating",
        "content": "Had an interesting conversation on a date last night. We talked about vulnerability and how hard it is to be truly open with someone new. Made me think about how we all wear masks to protect ourselves.",
        "persona": "aspandead",  # Dating/relationships
        "category": "Relationships"
    },
    {
        "title": "Base L2 airdrop",
        "content": "New Base Layer 2 protocol launching airdrop. Early adopters who stake USDC and interact with the protocol will be eligible for rewards. Estimated allocation up to $2000 per wallet.",
        "persona": "claimzilla",  # Crypto
        "category": "Cryptocurrency"
    },
    {
        "title": "Career transition",
        "content": "Many developers ask how to transition into senior roles. Key things: take ownership of projects, mentor juniors, think about architecture not just code, communicate effectively with non-technical stakeholders.",
        "persona": "qronoya",  # Career/tech
        "category": "Career"
    },
    {
        "title": "Solana DeFi",
        "content": "Solana DeFi is heating up. New lending protocols offering 15-20% APY on stablecoins. Low gas fees make it attractive for smaller wallets. But always DYOR - high yields come with risks.",
        "persona": "claimzilla",  # Crypto/DeFi
        "category": "Cryptocurrency"
    }
]


async def rewrite_5_posts():
    """Rewrite 5 sample posts"""

    print("\n" + "="*100)
    print("🎨 5 REWRITES - PERSONAL VOICE (Vikhr for Russian)")
    print("="*100 + "\n")

    rewriter = ContentRewriter()

    # Emoji/hashtag patterns for checking
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

    for i, post in enumerate(SAMPLE_POSTS, 1):
        print(f"\n{'='*100}")
        print(f"POST #{i}: {post['title']} → {post['persona'].upper()}")
        print("="*100)

        # Display original
        print(f"\n📝 ORIGINAL:")
        print("-" * 100)
        print(post['content'])
        print("-" * 100)

        # Create analyzed content structure
        analyzed = {
            'content': post['content'],
            'summary': post['content'][:100],
            'category': post['category'],
            'topics': [],
            'key_concepts': [],
            'complexity': 'Intermediate',
            'discovery_signals': {'viral_potential': 60},
            'rewrite_angles': [{
                'persona': post['persona'],
                'angle': f"Rewrite in {post['persona']} voice",
                'hook': post['title'],
                'key_points': [],
                'call_to_action': 'Engage with audience',
                'target_audience': 'General',
                'tone': 'Natural',
                'platform_fit': 'twitter_thread'
            }]
        }

        # Rewrite
        print(f"\n✍️  REWRITING AS {post['persona'].upper()}...")
        result = await rewriter.rewrite_analyzed_post(analyzed, post['persona'], 'twitter')

        rewritten = result.get('rewritten_content', '')

        # Display
        print(f"\n✨ {post['persona'].upper()} REWRITE:")
        print("-" * 100)
        print(rewritten)
        print("-" * 100)

        # Quality check
        emojis = emoji_pattern.findall(rewritten)
        hashtags = hashtag_pattern.findall(rewritten)

        print(f"\n📊 QUALITY:")
        print(f"   Emojis: {len(emojis)} {'✅' if len(emojis) == 0 else '⚠️ ' + str(emojis)}")
        print(f"   Hashtags: {len(hashtags)} {'✅' if len(hashtags) == 0 else '⚠️ ' + str(hashtags)}")

        results.append({
            'title': post['title'],
            'persona': post['persona'],
            'emojis': len(emojis),
            'hashtags': len(hashtags)
        })

    # Summary
    print("\n\n" + "="*100)
    print("📊 SUMMARY")
    print("="*100 + "\n")

    total_emojis = sum(r['emojis'] for r in results)
    total_hashtags = sum(r['hashtags'] for r in results)

    for r in results:
        status = "✅" if (r['emojis'] == 0 and r['hashtags'] == 0) else "⚠️"
        print(f"{status} {r['persona']:12} ({r['title']}): {r['emojis']} emojis, {r['hashtags']} hashtags")

    print(f"\nTOTAL: {total_emojis} emojis, {total_hashtags} hashtags")

    if total_emojis == 0 and total_hashtags == 0:
        print("\n🎉 PERFECT! 100% PERSONAL VOICE")

    print("\n" + "="*100 + "\n")


if __name__ == "__main__":
    asyncio.run(rewrite_5_posts())
