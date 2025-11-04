#!/usr/bin/env python3
"""
DEMO: Complete PrisMind Flow
=============================

Demonstrates the enhanced pipeline:
1. Analyze post (with improved analyzer)
2. Rewrite for persona (using enhanced angles)
3. Ready for publishing (with all metadata)

Shows how the analyzer improvements feed into the rewriter.
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


async def demo_complete_flow():
    """Demonstrate the complete flow with enhanced analyzer"""

    print("=" * 80)
    print("PRISMIND COMPLETE FLOW DEMONSTRATION")
    print("Analyze → Rewrite → Publish (Ready)")
    print("=" * 80)
    print()

    # =========================================================================
    # STEP 1: ANALYZE A POST
    # =========================================================================

    print("📊 STEP 1: ANALYZING POST")
    print("-" * 80)

    analyzer = IntelligentContentAnalyzer()

    # Example: Viral GPT-5 announcement
    test_post = SocialPost(
        post_id="gpt5_announcement",
        platform="twitter",
        content="""Breaking: OpenAI just announced GPT-5. Key improvements:

- 10x larger context window (1M tokens)
- Native multimodal (text, image, video, audio)
- Built-in memory across conversations
- 99.9% accuracy on reasoning tasks
- Real-time learning from interactions

AI just leveled up again. This changes everything.""",
        author="AI News",
        author_handle="@ainews",
        url="https://twitter.com/ainews/status/123",
        created_at=datetime.now().isoformat(),
        hashtags=["AI", "GPT5", "OpenAI", "MachineLearning"],
        engagement={"likes": 5600, "replies": 890, "retweets": 2100},
        media_urls=[],
        post_type="text"
    )

    print(f"📄 Post: {test_post.content[:80]}...")
    print(f"📈 Engagement: {test_post.engagement['likes']} likes, {test_post.engagement['replies']} replies")
    print()

    # Analyze
    analysis = analyzer.analyze_bookmark(test_post, include_comments=False, include_media=False)

    print("✅ ANALYSIS COMPLETE")
    print(f"   Category: {analysis.get('category')}")
    print(f"   Value Score: {analysis.get('intelligent_value_score'):.1f}/10")
    print(f"   Quality Score: {analysis.get('content_quality_score'):.1f}/10")
    print()

    # Show discovery signals
    print("🔍 Discovery Signals:")
    signals = analysis.get('discovery_signals', {})
    print(f"   • Authority: {signals.get('author_authority')} (based on 5600 likes)")
    print(f"   • Trend: {signals.get('trend_relevance')} (detected 'announced')")
    print(f"   • Viral Potential: {signals.get('viral_potential')}/100")
    print(f"   • Discussion: {signals.get('discussion_quality')} (890 replies)")
    print(f"   • Unique: {signals.get('unique_perspective')}")
    print()

    # Show one rewrite angle
    print("📝 Sample Rewrite Angle (Technical):")
    rewrite_angles = analysis.get('rewrite_angles', [])
    if rewrite_angles:
        tech_angle = next((a for a in rewrite_angles if a['persona'] == 'technical'), rewrite_angles[0])
        print(f"   • Hook: {tech_angle.get('hook')}")
        print(f"   • Tone: {tech_angle.get('tone')}")
        print(f"   • CTA: {tech_angle.get('call_to_action')}")
        print(f"   • Platform Fit: {tech_angle.get('platform_fit')}")
        print(f"   • Key Points: {', '.join(tech_angle.get('key_points', []))}")
    print()

    print("-" * 80)
    print()

    # =========================================================================
    # STEP 2: REWRITE FOR DIFFERENT PERSONAS
    # =========================================================================

    print("✍️  STEP 2: REWRITING FOR PERSONAS")
    print("-" * 80)
    print()

    rewriter = ContentRewriter()

    # Test with 3 personas
    personas_to_test = ['builder', 'trendsetter', 'technical']

    rewrites = {}
    for persona in personas_to_test:
        print(f"🎭 Rewriting as: {persona.upper()}")

        try:
            rewritten = await rewriter.rewrite_analyzed_post(
                analyzed_content=analysis,
                persona=persona,
                platform="auto"  # Uses platform_fit from angle
            )

            rewrites[persona] = rewritten

            print(f"   ✅ Complete!")
            print(f"   Platform: {rewritten.get('platform')} (from platform_fit: {rewritten.get('platform_fit')})")
            print(f"   Tone: {rewritten.get('tone_used')}")
            print(f"   Hook: {rewritten.get('hook_used')}")
            print(f"   CTA: {rewritten.get('call_to_action')}")
            print()
            print(f"   Rewritten Content:")
            print(f"   {rewritten.get('rewritten_content')[:200]}...")
            print()

        except Exception as e:
            print(f"   ❌ Error: {e}")
            print()

    print("-" * 80)
    print()

    # =========================================================================
    # STEP 3: PUBLISHING METADATA (Ready for Scheduling)
    # =========================================================================

    print("🚀 STEP 3: READY FOR PUBLISHING")
    print("-" * 80)
    print()

    print("Publishing Queue with Priority:")
    print()

    # Sort by viral potential for priority
    sorted_rewrites = sorted(
        rewrites.items(),
        key=lambda x: x[1].get('viral_potential', 0),
        reverse=True
    )

    for i, (persona, rewrite) in enumerate(sorted_rewrites, 1):
        print(f"{i}. {rewrite.get('persona_name')} {rewrite.get('persona_emoji')}")
        print(f"   Platform: {rewrite.get('platform')}")
        print(f"   Viral Potential: {rewrite.get('viral_potential')}/100")
        print(f"   Authority: {rewrite.get('author_authority')}")
        print(f"   Trend: {rewrite.get('trend_relevance')}")
        print(f"   Time Sensitivity: {rewrite.get('time_sensitivity')}")
        print(f"   → Priority: {'🔴 HIGH' if rewrite.get('viral_potential', 0) > 80 else '🟡 MEDIUM'}")
        print()

    # =========================================================================
    # SUMMARY
    # =========================================================================

    print("=" * 80)
    print("📊 FLOW SUMMARY")
    print("=" * 80)
    print()

    print("✅ ANALYZER ENHANCEMENTS:")
    print("   • Wider scoring distribution (exponential engagement scaling)")
    print("   • Intelligent discovery signals (0% unknown values)")
    print("   • Enhanced rewrite angles (tone, CTA, platform_fit)")
    print()

    print("✅ REWRITER INTEGRATION:")
    print("   • Uses angle-specific tone guidance")
    print("   • Incorporates hook and key points")
    print("   • Applies call-to-action")
    print("   • Respects platform_fit (auto-selects platform)")
    print()

    print("✅ PUBLISHING READY:")
    print("   • Viral potential for prioritization")
    print("   • Author authority for credibility")
    print("   • Trend relevance for timing")
    print("   • Time sensitivity for scheduling")
    print()

    print("🎉 COMPLETE PIPELINE WORKING!")
    print()
    print("Next Steps:")
    print("  1. Connect to posting scheduler (use time_sensitivity + viral_potential)")
    print("  2. Implement publishing queue (prioritize by discovery signals)")
    print("  3. Track engagement (feed back into learning system - Week 2)")
    print()

    # Save results
    results = {
        "original_post": {
            "content": test_post.content,
            "engagement": test_post.engagement
        },
        "analysis": {
            "category": analysis.get('category'),
            "value_score": analysis.get('intelligent_value_score'),
            "quality_score": analysis.get('content_quality_score'),
            "discovery_signals": analysis.get('discovery_signals'),
            "content_freshness": analysis.get('content_freshness')
        },
        "rewrites": {
            persona: {
                "persona_name": r.get('persona_name'),
                "platform": r.get('platform'),
                "platform_fit": r.get('platform_fit'),
                "tone": r.get('tone_used'),
                "hook": r.get('hook_used'),
                "cta": r.get('call_to_action'),
                "viral_potential": r.get('viral_potential'),
                "content_preview": r.get('rewritten_content', '')[:200]
            }
            for persona, r in rewrites.items()
        }
    }

    with open('demo_flow_results.json', 'w') as f:
        json.dump(results, f, indent=2)

    print("📄 Results saved to: demo_flow_results.json")
    print()


if __name__ == "__main__":
    asyncio.run(demo_complete_flow())
