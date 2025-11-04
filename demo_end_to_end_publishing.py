#!/usr/bin/env python3
"""
DEMO: Complete PrisMind Publishing Pipeline
============================================

End-to-End Flow:
1. Analyze post (with enhanced analyzer)
2. Rewrite for multiple personas (with all metadata)
3. Schedule intelligently (based on viral_potential, time_sensitivity)
4. Ready for publishing (via worker + threads_playwright)

Shows how enhanced metadata flows through the entire pipeline.
"""

import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from src.core.analysis.intelligent_content_analyzer import IntelligentContentAnalyzer
from src.core.extraction.social_extractor_base import SocialPost
from src.publishing.rewriter import ContentRewriter
from src.publishing.scheduler import PublishingScheduler


async def demo_end_to_end():
    """Demonstrate complete publishing pipeline"""

    print("=" * 80)
    print("PRISMIND END-TO-END PUBLISHING DEMO")
    print("Analyze → Rewrite → Schedule → Publish (Ready)")
    print("=" * 80)
    print()

    # =========================================================================
    # STEP 1: COLLECT & ANALYZE
    # =========================================================================

    print("📊 STEP 1: ANALYZING POST")
    print("-" * 80)

    analyzer = IntelligentContentAnalyzer()

    # Example: Viral AI breakthrough announcement
    test_post = SocialPost(
        post_id="ai_breakthrough_2025",
        platform="twitter",
        content="""BREAKING: New AI model just achieved AGI-level reasoning.

Key capabilities:
• Solves complex math proofs
• Writes production code with 99% accuracy
• Reasons about novel problems
• Self-corrects errors in real-time

This is the biggest leap since GPT-4. The AI landscape just shifted.

Paper: [link]
Demo: [link]

#AI #AGI #MachineLearning""",
        author="AI Research Lab",
        author_handle="@ailab",
        url="https://twitter.com/ailab/status/123456",
        created_at=datetime.now().isoformat(),
        hashtags=["AI", "AGI", "MachineLearning", "Research"],
        engagement={
            "likes": 8900,
            "replies": 1200,
            "retweets": 3400
        },
        media_urls=[],
        post_type="text"
    )

    print(f"📄 Post: {test_post.content[:80]}...")
    print(f"📈 Engagement: {test_post.engagement['likes']:,} likes, {test_post.engagement['replies']:,} replies")
    print()

    # Analyze (with enhanced metadata)
    analysis = analyzer.analyze_bookmark(test_post, include_comments=False, include_media=False)

    print("✅ ANALYSIS COMPLETE")
    print()
    print(f"   Category: {analysis.get('category')}")
    print(f"   Value Score: {analysis.get('intelligent_value_score'):.1f}/10")
    print(f"   Quality Score: {analysis.get('content_quality_score'):.1f}/10")
    print()

    # Show enhanced discovery signals
    discovery_signals = analysis.get('discovery_signals', {})
    print("🔍 Discovery Signals (Enhanced):")
    print(f"   • Viral Potential: {discovery_signals.get('viral_potential')}/100 🔥")
    print(f"   • Author Authority: {discovery_signals.get('author_authority')}")
    print(f"   • Trend Relevance: {discovery_signals.get('trend_relevance')}")
    print(f"   • Discussion Quality: {discovery_signals.get('discussion_quality')}")
    print(f"   • Unique Perspective: {discovery_signals.get('unique_perspective')}")
    print()

    # Show content freshness
    content_freshness = analysis.get('content_freshness', {})
    print(f"⏰ Content Freshness:")
    print(f"   • Time Sensitivity: {content_freshness.get('time_sensitivity')} ⚡")
    print(f"   • Relevance Window: {content_freshness.get('relevance_window')}")
    print()

    print("-" * 80)
    print()

    # =========================================================================
    # STEP 2: REWRITE FOR PERSONAS
    # =========================================================================

    print("✍️  STEP 2: REWRITING FOR PERSONAS")
    print("-" * 80)
    print()

    rewriter = ContentRewriter()

    # Rewrite for 3 personas to show variety
    personas_to_test = ['technical', 'builder', 'trendsetter']

    rewrites = []
    for persona in personas_to_test:
        print(f"🎭 Rewriting as: {persona.upper()}")

        try:
            rewritten = await rewriter.rewrite_analyzed_post(
                analyzed_content=analysis,
                persona=persona,
                platform="auto"  # Uses platform_fit from angle
            )

            if 'error' not in rewritten:
                rewrites.append(rewritten)

                print(f"   ✅ Complete!")
                print(f"   Platform: {rewritten.get('platform')} (fit: {rewritten.get('platform_fit')})")
                print(f"   Tone: {rewritten.get('tone_used')}")
                print(f"   Viral Potential: {rewritten.get('viral_potential')}/100")
                print(f"   Time Sensitivity: {rewritten.get('time_sensitivity')}")
                print()
                print(f"   Rewritten Preview:")
                print(f"   {rewritten.get('rewritten_content')[:150]}...")
                print()
            else:
                print(f"   ❌ Error: {rewritten['error']}")
                print()

        except Exception as e:
            print(f"   ❌ Error: {e}")
            print()

    print("-" * 80)
    print()

    # =========================================================================
    # STEP 3: INTELLIGENT SCHEDULING
    # =========================================================================

    print("📅 STEP 3: INTELLIGENT SCHEDULING")
    print("-" * 80)
    print()

    scheduler = PublishingScheduler()

    print("Analyzing each rewrite and calculating optimal posting time...\n")

    schedule_decisions = []
    for rewritten in rewrites:
        decision = scheduler.schedule_rewritten_post(rewritten)
        schedule_decisions.append((rewritten, decision))

        persona_name = rewritten.get('persona_name', rewritten.get('persona'))
        print(f"{rewritten.get('persona_emoji')} {persona_name}")
        print(f"   Priority: {decision.priority}/100")
        print(f"   Post at: {decision.when.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Platform: {decision.platform}")
        print(f"   Reason: {decision.reason}")
        print()

    print("-" * 80)
    print()

    # =========================================================================
    # STEP 4: PUBLISHING QUEUE
    # =========================================================================

    print("🚀 STEP 4: PUBLISHING QUEUE (Priority Order)")
    print("-" * 80)
    print()

    # Sort by priority (highest first)
    sorted_decisions = sorted(
        schedule_decisions,
        key=lambda x: x[1].priority,
        reverse=True
    )

    print("Queue sorted by priority (highest posts first):\n")

    for i, (rewritten, decision) in enumerate(sorted_decisions, 1):
        priority_emoji = "🔴" if decision.priority >= 80 else "🟡" if decision.priority >= 50 else "🟢"
        persona_name = rewritten.get('persona_name', rewritten.get('persona'))

        print(f"{i}. {priority_emoji} PRIORITY {decision.priority} - {rewritten.get('persona_emoji')} {persona_name}")
        print(f"   Post to: {decision.platform}")
        print(f"   When: {decision.when.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Viral Potential: {rewritten.get('viral_potential')}/100")
        print(f"   Time Sensitivity: {rewritten.get('time_sensitivity')}")
        print(f"   Trend: {rewritten.get('trend_relevance')}")
        print()

    print("-" * 80)
    print()

    # =========================================================================
    # STEP 5: READY FOR PUBLISHING
    # =========================================================================

    print("🎯 STEP 5: READY FOR PUBLISHING")
    print("-" * 80)
    print()

    print("Publishing Flow:")
    print()
    print("1. Insert to Database:")
    print("   → scheduled_posts table (with priority, scheduled_for)")
    print()
    print("2. PublisherWorker picks up due posts:")
    print("   → Checks every 15 seconds for due posts")
    print("   → Routes to correct platform (Twitter/Threads/Telegram)")
    print()
    print("3. Platform posting:")
    print("   → post_to_threads_playwright() for Threads")
    print("   → post_to_twitter_direct() for Twitter")
    print("   → Uses browser automation (Playwright)")
    print()
    print("4. Post confirmation:")
    print("   → Returns {success, post_id, url}")
    print("   → Updates database with platform_post_id")
    print()

    # Show example database insert
    print("Example Database Insert:")
    print()
    print("```python")
    print("db.schedule_post(")
    print(f"    content=\"{sorted_decisions[0][1].content[:50]}...\",")
    print(f"    platform=\"{sorted_decisions[0][1].platform}\",")
    print(f"    scheduled_for=\"{sorted_decisions[0][1].when.isoformat()}\",")
    print(f"    metadata={{")
    print(f"        'priority': {sorted_decisions[0][1].priority},")
    print(f"        'viral_potential': {sorted_decisions[0][0].get('viral_potential')},")
    print(f"        'time_sensitivity': '{sorted_decisions[0][0].get('time_sensitivity')}',")
    print(f"        'persona': '{sorted_decisions[0][0].get('persona')}'")
    print("    }")
    print(")")
    print("```")
    print()

    print("-" * 80)
    print()

    # =========================================================================
    # SUMMARY
    # =========================================================================

    print("=" * 80)
    print("📊 PIPELINE SUMMARY")
    print("=" * 80)
    print()

    print("✅ COMPLETE END-TO-END FLOW:")
    print()
    print("1. ✅ ANALYZER")
    print("   • Enhanced discovery signals (no unknowns)")
    print("   • Intelligent value scoring (wider distribution)")
    print("   • Rewrite angles with tone, CTA, platform_fit")
    print()

    print("2. ✅ REWRITER")
    print("   • Uses angle-specific tone and guidance")
    print("   • Auto-selects platform based on platform_fit")
    print("   • Preserves all metadata (viral_potential, time_sensitivity)")
    print()

    print("3. ✅ SCHEDULER")
    print("   • Calculates priority from viral_potential + time_sensitivity")
    print("   • Determines optimal posting time")
    print("   • Prioritizes urgent/breaking content")
    print()

    print("4. ✅ PUBLISHING")
    print("   • PublisherWorker picks up due posts")
    print("   • Routes to correct platform (Threads/Twitter/Telegram)")
    print("   • Uses Playwright for browser automation")
    print()

    print("🎉 COMPLETE PIPELINE READY FOR PRODUCTION!")
    print()

    # Save results for inspection
    results = {
        "original_post": {
            "content": test_post.content,
            "engagement": test_post.engagement,
            "platform": test_post.platform
        },
        "analysis": {
            "category": analysis.get('category'),
            "value_score": analysis.get('intelligent_value_score'),
            "quality_score": analysis.get('content_quality_score'),
            "discovery_signals": discovery_signals,
            "content_freshness": content_freshness
        },
        "rewrites": [
            {
                "persona": r.get('persona'),
                "persona_name": r.get('persona_name'),
                "platform": r.get('platform'),
                "viral_potential": r.get('viral_potential'),
                "time_sensitivity": r.get('time_sensitivity'),
                "content_preview": r.get('rewritten_content', '')[:200]
            }
            for r in rewrites
        ],
        "schedule": [
            {
                "persona": rewrites[i].get('persona'),
                "priority": decision.priority,
                "scheduled_for": decision.when.isoformat(),
                "reason": decision.reason
            }
            for i, (_, decision) in enumerate(sorted_decisions)
        ]
    }

    output_file = 'demo_end_to_end_results.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"📄 Results saved to: {output_file}")
    print()

    print("Next Steps:")
    print("  1. Set up Supabase scheduled_posts table")
    print("  2. Start PublisherWorker background service")
    print("  3. Configure Threads/Twitter credentials (.env)")
    print("  4. Insert scheduled posts → Worker publishes automatically")
    print()


if __name__ == "__main__":
    asyncio.run(demo_end_to_end())
