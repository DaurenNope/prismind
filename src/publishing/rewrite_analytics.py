#!/usr/bin/env python3
"""
Rewrite Analytics & Learning System
Tracks what works and helps improve rewriter over time
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
from collections import defaultdict, Counter

logger = logging.getLogger(__name__)


class RewriteAnalytics:
    """Track and analyze rewrite performance"""

    def __init__(self, analytics_dir: str = "data/analytics"):
        self.analytics_dir = Path(analytics_dir)
        self.analytics_dir.mkdir(parents=True, exist_ok=True)

        self.rewrite_log = self.analytics_dir / "rewrite_log.jsonl"
        self.stats_file = self.analytics_dir / "rewrite_stats.json"

    def log_rewrite(self, rewrite_data: Dict[str, Any]):
        """
        Log a rewrite event

        Args:
            rewrite_data: Dict with rewrite details
                - persona
                - platform
                - content_type
                - quality_score
                - length_valid
                - examples_used
                - tone_detected
                - timestamp
                - success (bool)
        """
        try:
            with open(self.rewrite_log, 'a', encoding='utf-8') as f:
                f.write(json.dumps(rewrite_data, ensure_ascii=False) + '\n')
            logger.debug(f"📊 Logged rewrite: {rewrite_data['persona']} / {rewrite_data.get('content_type')}")
        except Exception as e:
            logger.error(f"Failed to log rewrite: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """
        Calculate statistics from rewrite log

        Returns:
            Dict with stats:
            - total_rewrites
            - by_persona
            - by_content_type
            - avg_quality_score
            - success_rate
            - best_performing_examples
        """
        if not self.rewrite_log.exists():
            return {
                "total_rewrites": 0,
                "message": "No rewrites logged yet"
            }

        # Load all rewrite events
        rewrites = []
        try:
            with open(self.rewrite_log, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        rewrites.append(json.loads(line))
        except Exception as e:
            logger.error(f"Error loading rewrite log: {e}")
            return {"error": str(e)}

        # Calculate stats
        total = len(rewrites)
        successful = sum(1 for r in rewrites if r.get('success', True))

        # By persona
        by_persona = defaultdict(lambda: {"count": 0, "quality_scores": []})
        for r in rewrites:
            persona = r.get('persona', 'unknown')
            by_persona[persona]['count'] += 1
            if 'quality_score' in r:
                by_persona[persona]['quality_scores'].append(r['quality_score'])

        # By content type
        content_types = Counter(r.get('content_type', 'unknown') for r in rewrites)

        # Average quality scores
        all_quality_scores = [r['quality_score'] for r in rewrites if 'quality_score' in r]
        avg_quality = sum(all_quality_scores) / len(all_quality_scores) if all_quality_scores else 0

        # Example usage tracking (which examples lead to best results)
        example_performance = defaultdict(lambda: {"uses": 0, "avg_quality": 0, "qualities": []})
        for r in rewrites:
            examples_used = r.get('examples_used', [])
            quality = r.get('quality_score', 0)
            for ex_id in examples_used:
                example_performance[ex_id]['uses'] += 1
                example_performance[ex_id]['qualities'].append(quality)

        # Calculate avg quality per example
        for ex_id, data in example_performance.items():
            if data['qualities']:
                data['avg_quality'] = sum(data['qualities']) / len(data['qualities'])

        # Sort examples by performance
        best_examples = sorted(
            example_performance.items(),
            key=lambda x: (x[1]['avg_quality'], x[1]['uses']),
            reverse=True
        )[:10]

        return {
            "total_rewrites": total,
            "successful_rewrites": successful,
            "success_rate": successful / total if total > 0 else 0,
            "avg_quality_score": round(avg_quality, 2),
            "by_persona": {
                persona: {
                    "count": data['count'],
                    "avg_quality": round(sum(data['quality_scores']) / len(data['quality_scores']), 2) if data['quality_scores'] else 0
                }
                for persona, data in by_persona.items()
            },
            "top_content_types": dict(content_types.most_common(10)),
            "best_performing_examples": [
                {
                    "example_id": ex_id,
                    "uses": data['uses'],
                    "avg_quality": round(data['avg_quality'], 2)
                }
                for ex_id, data in best_examples
            ],
            "last_updated": datetime.now().isoformat()
        }

    def save_stats(self):
        """Save current stats to file"""
        stats = self.get_stats()
        try:
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats, f, ensure_ascii=False, indent=2)
            logger.info(f"📊 Saved analytics stats: {stats.get('total_rewrites')} rewrites")
        except Exception as e:
            logger.error(f"Failed to save stats: {e}")

    def get_recommendations(self, persona: str, content_type: str) -> Dict[str, Any]:
        """
        Get recommendations for improving rewrite quality

        Args:
            persona: Persona to analyze
            content_type: Content type to analyze

        Returns:
            Dict with recommendations
        """
        stats = self.get_stats()

        recommendations = {
            "persona": persona,
            "content_type": content_type,
            "suggestions": []
        }

        # Check if this persona has low quality scores
        persona_stats = stats.get('by_persona', {}).get(persona, {})
        persona_quality = persona_stats.get('avg_quality', 0)

        if persona_quality < 80:
            recommendations['suggestions'].append({
                "type": "quality_improvement",
                "message": f"Average quality for {persona} is {persona_quality}/100. Consider adding more diverse examples."
            })

        # Check if this content type is underperforming
        content_type_count = stats.get('top_content_types', {}).get(content_type, 0)
        if content_type_count < 5:
            recommendations['suggestions'].append({
                "type": "content_type_coverage",
                "message": f"Only {content_type_count} rewrites for {content_type}. Consider testing more with this content type."
            })

        # Recommend best examples
        best_examples = stats.get('best_performing_examples', [])[:3]
        if best_examples:
            recommendations['best_examples'] = best_examples

        return recommendations


# Singleton
_analytics = None


def get_analytics() -> RewriteAnalytics:
    """Get global analytics instance"""
    global _analytics
    if _analytics is None:
        _analytics = RewriteAnalytics()
    return _analytics


if __name__ == "__main__":
    # Test analytics
    import logging
    logging.basicConfig(level=logging.INFO)

    analytics = get_analytics()

    # Simulate some rewrites
    for i in range(10):
        analytics.log_rewrite({
            "persona": "qronoya" if i % 2 == 0 else "aspandead",
            "platform": "twitter",
            "content_type": "tech_opinion" if i % 2 == 0 else "dating_story",
            "quality_score": 85 + (i % 15),
            "length_valid": True,
            "examples_used": [1, 3, 5] if i % 2 == 0 else [2, 4, 7],
            "tone_detected": "analytical" if i % 2 == 0 else "vulnerable",
            "timestamp": datetime.now().isoformat(),
            "success": True
        })

    # Get and print stats
    stats = analytics.get_stats()
    print("\n📊 Analytics Stats:")
    print(json.dumps(stats, indent=2, ensure_ascii=False))

    analytics.save_stats()
    print("\n✅ Stats saved to data/analytics/rewrite_stats.json")
