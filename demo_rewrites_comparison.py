#!/usr/bin/env python3
"""
Demo: Show Original vs Rewritten Content
Side-by-side comparison of authentic voice rewrites
"""

import asyncio
from src.publishing.rewriter import ContentRewriter


async def show_rewrites():
    """Show original vs rewritten content for all 3 profiles"""

    rewriter = ContentRewriter()

    print("\n" + "=" * 100)
    print("ORIGINAL vs REWRITTEN - SIDE-BY-SIDE COMPARISON")
    print("=" * 100 + "\n")

    # Test Case 1: Crypto Airdrop (for Claimzilla)
    print("=" * 100)
    print("TEST 1: CRYPTO AIRDROP CONTENT → CLAIMZILLA")
    print("=" * 100 + "\n")

    crypto_original = {
        'content': 'New Base Layer 2 protocol launching airdrop. Early adopters who stake USDC and interact with the protocol will be eligible for rewards. Estimated allocation up to $2000 per wallet.',
        'summary': 'Base L2 airdrop for early users',
        'category': 'Crypto',
        'topics': ['crypto', 'airdrop', 'base', 'l2', 'defi'],
        'key_concepts': ['airdrop', 'layer2', 'staking', 'rewards'],
        'complexity': 'Intermediate',
        'discovery_signals': {'viral_potential': 75},
        'rewrite_angles': [{
            'persona': 'claimzilla',
            'angle': 'Alpha drop with actionable farming strategy',
            'hook': 'Alpha alert: Base L2 airdrop confirmed',
            'key_points': ['How to qualify', 'Expected rewards', 'Time commitment'],
            'tone': 'helpful, engaging, technical',
            'call_to_action': 'DYOR and start farming',
            'platform_fit': 'twitter_thread'
        }]
    }

    print("📝 ORIGINAL CONTENT:")
    print("-" * 100)
    print(crypto_original['content'])
    print("-" * 100)
    print()

    result1 = await rewriter.rewrite_analyzed_post(crypto_original, 'claimzilla', 'twitter')

    print("✍️  CLAIMZILLA REWRITE (Crypto Reply Guy Voice):")
    print("-" * 100)
    print(result1['rewritten_content'])
    print("-" * 100)
    print(f"\nPersona: {result1['persona_emoji']} {result1['persona_name']}")
    print(f"Language: English")
    print(f"Voice markers: Alpha drops, DYOR, specific numbers, emojis, numbered format")
    print()

    # Test Case 2: Dating/Personal Story (for Aspandead)
    print("\n" + "=" * 100)
    print("TEST 2: DATING/RELATIONSHIP CONTENT → ASPANDEAD")
    print("=" * 100 + "\n")

    dating_original = {
        'content': 'Had an interesting conversation on a date last night. We talked about vulnerability and how hard it is to be truly open with someone new. Made me think about how we all wear masks to protect ourselves.',
        'summary': 'Reflection on vulnerability in dating',
        'category': 'Personal',
        'topics': ['dating', 'relationship', 'vulnerability', 'personal'],
        'key_concepts': ['vulnerability', 'authenticity', 'connection', 'self-protection'],
        'complexity': 'Advanced',
        'discovery_signals': {'viral_potential': 55},
        'rewrite_angles': [{
            'persona': 'aspandead',
            'angle': 'Deep dive into vulnerability and authentic connection',
            'hook': 'There\'s something about vulnerability that changes everything',
            'key_points': ['The mask we wear', 'What true openness requires', 'The cost of protection'],
            'tone': 'raw, vulnerable, literary',
            'call_to_action': 'Sit with this',
            'platform_fit': 'twitter_thread'
        }]
    }

    print("📝 ORIGINAL CONTENT:")
    print("-" * 100)
    print(dating_original['content'])
    print("-" * 100)
    print()

    result2 = await rewriter.rewrite_analyzed_post(dating_original, 'aspandead', 'twitter')

    print("✍️  ASPANDEAD REWRITE (Deep Writer Voice):")
    print("-" * 100)
    print(result2['rewritten_content'])
    print("-" * 100)
    print(f"\nPersona: {result2['persona_emoji']} {result2['persona_name']}")
    print(f"Language: English")
    print(f"Voice markers: Literary metaphors, emotional depth, vulnerable tone, poetic rhythm")
    print()

    # Test Case 3: Tech/Career Advice (for Qronoya)
    print("\n" + "=" * 100)
    print("TEST 3: TECH/CAREER CONTENT → QRONOYA")
    print("=" * 100 + "\n")

    tech_original = {
        'content': 'Many developers ask how to transition into senior roles. Here are the key things: take ownership of projects, mentor juniors, think about architecture not just code, communicate effectively with non-technical stakeholders.',
        'summary': 'Career growth advice for developers',
        'category': 'Career',
        'topics': ['career', 'tech', 'developer', 'professional', 'growth'],
        'key_concepts': ['leadership', 'mentorship', 'architecture', 'communication'],
        'complexity': 'Intermediate',
        'discovery_signals': {'viral_potential': 60},
        'rewrite_angles': [{
            'persona': 'qronoya',
            'angle': 'Practical advice for career growth',
            'hook': 'How to grow from developer to senior',
            'key_points': ['Take ownership', 'Mentor others', 'Think bigger', 'Communicate well'],
            'tone': 'professional, approachable, practical',
            'call_to_action': 'Start applying this today',
            'platform_fit': 'twitter_thread'
        }]
    }

    print("📝 ORIGINAL CONTENT:")
    print("-" * 100)
    print(tech_original['content'])
    print("-" * 100)
    print()

    result3 = await rewriter.rewrite_analyzed_post(tech_original, 'qronoya', 'twitter')

    print("✍️  QRONOYA REWRITE (Russian Tech Professional Voice):")
    print("-" * 100)
    print(result3['rewritten_content'])
    print("-" * 100)
    print(f"\nPersona: {result3['persona_emoji']} {result3['persona_name']}")
    print(f"Language: RUSSIAN (Cyrillic)")
    print(f"Voice markers: Practical advice, professional but approachable, Russian language")
    print()

    # Summary comparison
    print("\n" + "=" * 100)
    print("VOICE TRANSFORMATION SUMMARY")
    print("=" * 100 + "\n")

    print("🎯 ORIGINAL → CLAIMZILLA:")
    print("   Generic crypto announcement → Authentic crypto reply guy with alpha, steps, DYOR")
    print()

    print("🖤 ORIGINAL → ASPANDEAD:")
    print("   Simple dating reflection → Deep, vulnerable, literary exploration of masks and truth")
    print()

    print("💡 ORIGINAL → QRONOYA:")
    print("   Generic career advice → Natural Russian professional guidance with practical steps")
    print()

    print("=" * 100)
    print("KEY INSIGHT: Same idea, completely different voices!")
    print("Each rewrite sounds like it was written by the actual persona.")
    print("=" * 100 + "\n")


if __name__ == "__main__":
    asyncio.run(show_rewrites())
