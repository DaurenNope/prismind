#!/usr/bin/env python3
"""
Publishing Scheduler - Intelligent Post Scheduling
Leverages enhanced analyzer metadata for optimal timing and prioritization
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SchedulingDecision:
    """Decision made by the scheduler"""
    when: datetime
    priority: int  # 1-100
    reason: str
    platform: str
    content: str


class PublishingScheduler:
    """
    Intelligent publishing scheduler that uses enhanced analyzer metadata.

    Leverages:
    - viral_potential (0-100) - How likely to go viral
    - time_sensitivity (breaking/trending/timely/evergreen) - Urgency
    - trend_relevance (emerging/mainstream/declining) - Trend status
    - author_authority (high/medium/low) - Source credibility

    Scheduling Logic:
    - breaking: Post immediately (0-5 min delay)
    - trending: Post within 1 hour
    - timely: Post within 24 hours
    - evergreen: Post anytime (can be scheduled days out)

    Prioritization:
    - High viral potential + emerging trend = URGENT (priority 90-100)
    - Medium viral + mainstream = NORMAL (priority 50-70)
    - Low viral + declining trend = LOW (priority 10-30)
    """

    def __init__(self):
        self.time_windows = {
            'breaking': (0, 5),      # 0-5 minutes
            'trending': (10, 60),    # 10-60 minutes
            'timely': (120, 480),    # 2-8 hours
            'evergreen': (480, 1440) # 8-24 hours
        }

    def schedule_rewritten_post(
        self,
        rewritten_content: Dict[str, Any],
        platform_override: Optional[str] = None
    ) -> SchedulingDecision:
        """
        Schedule a post based on enhanced analyzer metadata.

        Args:
            rewritten_content: Output from ContentRewriter.rewrite_analyzed_post()
            platform_override: Override the platform from rewritten_content

        Returns:
            SchedulingDecision with when to post, priority, and reasoning
        """

        # Extract metadata from rewritten content
        viral_potential = rewritten_content.get('viral_potential', 0)
        time_sensitivity = rewritten_content.get('time_sensitivity', 'evergreen')
        trend_relevance = rewritten_content.get('trend_relevance', 'mainstream')
        author_authority = rewritten_content.get('author_authority', 'medium')
        platform = platform_override or rewritten_content.get('platform', 'twitter')
        content = rewritten_content.get('rewritten_content', '')

        # Calculate priority (0-100)
        priority = self._calculate_priority(
            viral_potential=viral_potential,
            time_sensitivity=time_sensitivity,
            trend_relevance=trend_relevance,
            author_authority=author_authority
        )

        # Calculate optimal posting time
        when, reason = self._calculate_posting_time(
            time_sensitivity=time_sensitivity,
            priority=priority,
            viral_potential=viral_potential
        )

        logger.info(f"📅 Scheduled for {when.strftime('%Y-%m-%d %H:%M')} (priority: {priority})")
        logger.info(f"   Reason: {reason}")

        return SchedulingDecision(
            when=when,
            priority=priority,
            reason=reason,
            platform=platform,
            content=content
        )

    def _calculate_priority(
        self,
        viral_potential: int,
        time_sensitivity: str,
        trend_relevance: str,
        author_authority: str
    ) -> int:
        """
        Calculate post priority (0-100) based on multiple signals.

        Priority Formula:
        - Base from viral_potential (0-100)
        - Boost for breaking/trending (up to +20)
        - Boost for emerging trends (+15)
        - Boost for high authority (+10)
        """

        # Start with viral potential as base
        priority = viral_potential

        # Time sensitivity boost
        sensitivity_boost = {
            'breaking': 20,
            'trending': 15,
            'timely': 5,
            'evergreen': 0
        }
        priority += sensitivity_boost.get(time_sensitivity, 0)

        # Trend relevance boost
        trend_boost = {
            'emerging': 15,
            'mainstream': 5,
            'declining': -10
        }
        priority += trend_boost.get(trend_relevance, 0)

        # Authority boost
        authority_boost = {
            'high': 10,
            'medium': 5,
            'low': 0
        }
        priority += authority_boost.get(author_authority, 0)

        # Cap at 100
        return min(max(priority, 0), 100)

    def _calculate_posting_time(
        self,
        time_sensitivity: str,
        priority: int,
        viral_potential: int
    ) -> tuple[datetime, str]:
        """
        Calculate optimal posting time based on sensitivity and priority.

        Returns:
            (posting_time, reason)
        """

        now = datetime.now()

        # Get time window for this sensitivity level
        min_minutes, max_minutes = self.time_windows.get(
            time_sensitivity,
            (480, 1440)  # Default: evergreen
        )

        # For high priority/viral content, post at the START of the window
        # For lower priority, post later in the window
        if priority >= 80 or viral_potential >= 80:
            # High priority: post at earliest opportunity
            delay_minutes = min_minutes
            reason = f"High priority ({priority}) - posting at earliest opportunity"
        elif priority >= 50:
            # Medium priority: post in middle of window
            delay_minutes = (min_minutes + max_minutes) // 2
            reason = f"Medium priority ({priority}) - scheduling in optimal window"
        else:
            # Low priority: post at end of window
            delay_minutes = max_minutes
            reason = f"Lower priority ({priority}) - scheduling for later"

        # Add time sensitivity context to reason
        sensitivity_reasons = {
            'breaking': "URGENT: Breaking news",
            'trending': "Time-sensitive: Trending topic",
            'timely': "Timely content",
            'evergreen': "Evergreen content"
        }
        reason = f"{sensitivity_reasons.get(time_sensitivity, 'Standard')}: {reason}"

        posting_time = now + timedelta(minutes=delay_minutes)

        return posting_time, reason

    def schedule_all_persona_versions(
        self,
        analyzed_content: Dict[str, Any],
        rewriter,
        personas: List[str] = None
    ) -> List[SchedulingDecision]:
        """
        Generate and schedule versions for multiple personas.

        Args:
            analyzed_content: Full analysis from IntelligentContentAnalyzer
            rewriter: ContentRewriter instance
            personas: List of persona IDs (default: all 5)

        Returns:
            List of SchedulingDecisions, sorted by priority
        """

        if personas is None:
            personas = ['technical', 'builder', 'learner', 'trendsetter', 'thought_leader']

        decisions = []

        logger.info(f"📋 Scheduling {len(personas)} persona versions...")

        for persona in personas:
            try:
                # Rewrite for this persona
                import asyncio
                rewritten = asyncio.run(
                    rewriter.rewrite_analyzed_post(
                        analyzed_content=analyzed_content,
                        persona=persona,
                        platform="auto"
                    )
                )

                if 'error' in rewritten:
                    logger.warning(f"⚠️  Skipping {persona}: {rewritten['error']}")
                    continue

                # Schedule this version
                decision = self.schedule_rewritten_post(rewritten)
                decisions.append(decision)

                logger.info(f"   ✅ {persona}: priority {decision.priority}, post at {decision.when.strftime('%H:%M')}")

            except Exception as e:
                logger.error(f"❌ Failed to schedule {persona}: {e}")

        # Sort by priority (highest first)
        decisions.sort(key=lambda d: d.priority, reverse=True)

        return decisions

    def insert_to_database(
        self,
        decision: SchedulingDecision,
        db_manager,
        additional_metadata: Dict[str, Any] = None
    ) -> bool:
        """
        Insert scheduled post into database for PublisherWorker to pick up.

        Args:
            decision: SchedulingDecision with posting details
            db_manager: Database manager (e.g., MimesisDB)
            additional_metadata: Extra metadata to store

        Returns:
            True if inserted successfully
        """

        try:
            # Prepare metadata
            metadata = {
                'priority': decision.priority,
                'scheduling_reason': decision.reason,
                'scheduled_by': 'PublishingScheduler',
                'scheduled_at': datetime.now().isoformat()
            }

            if additional_metadata:
                metadata.update(additional_metadata)

            # Insert using database manager
            # (Assuming db_manager has a schedule_post method)
            result = db_manager.schedule_post(
                content=decision.content,
                platform=decision.platform,
                scheduled_for=decision.when,
                metadata=metadata
            )

            logger.info(f"✅ Inserted to database: {decision.platform} at {decision.when.strftime('%Y-%m-%d %H:%M')}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to insert to database: {e}")
            return False


# Singleton
_scheduler = None


def get_scheduler() -> PublishingScheduler:
    """Get global scheduler instance"""
    global _scheduler
    if _scheduler is None:
        _scheduler = PublishingScheduler()
    return _scheduler


def demo_scheduler():
    """Demo the scheduler with sample data"""

    print("🧪 Testing Publishing Scheduler\n")

    scheduler = get_scheduler()

    # Test cases with different metadata
    test_cases = [
        {
            'name': 'Viral Breaking News',
            'rewritten_content': {
                'rewritten_content': 'GPT-5 just dropped! 🔥 Here\'s what you need to know...',
                'viral_potential': 95,
                'time_sensitivity': 'breaking',
                'trend_relevance': 'emerging',
                'author_authority': 'high',
                'platform': 'twitter'
            }
        },
        {
            'name': 'Trending Tutorial',
            'rewritten_content': {
                'rewritten_content': 'How to build with the new AI SDK (step-by-step guide)',
                'viral_potential': 60,
                'time_sensitivity': 'trending',
                'trend_relevance': 'mainstream',
                'author_authority': 'medium',
                'platform': 'twitter'
            }
        },
        {
            'name': 'Evergreen Guide',
            'rewritten_content': {
                'rewritten_content': 'Python best practices for clean code',
                'viral_potential': 30,
                'time_sensitivity': 'evergreen',
                'trend_relevance': 'mainstream',
                'author_authority': 'medium',
                'platform': 'linkedin'
            }
        },
        {
            'name': 'Declining Topic',
            'rewritten_content': {
                'rewritten_content': 'Legacy framework comparison',
                'viral_potential': 20,
                'time_sensitivity': 'evergreen',
                'trend_relevance': 'declining',
                'author_authority': 'low',
                'platform': 'twitter'
            }
        }
    ]

    print("=" * 80)
    print("SCHEDULING DECISIONS")
    print("=" * 80)
    print()

    decisions = []
    for test_case in test_cases:
        print(f"📝 {test_case['name']}")
        print("-" * 80)

        decision = scheduler.schedule_rewritten_post(test_case['rewritten_content'])
        decisions.append((test_case['name'], decision))

        print(f"   Content: {decision.content[:60]}...")
        print(f"   Platform: {decision.platform}")
        print(f"   Priority: {decision.priority}/100")
        print(f"   Scheduled: {decision.when.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Reason: {decision.reason}")
        print()

    print("=" * 80)
    print("PRIORITY QUEUE (sorted by priority)")
    print("=" * 80)
    print()

    # Sort by priority
    sorted_decisions = sorted(decisions, key=lambda x: x[1].priority, reverse=True)

    for i, (name, decision) in enumerate(sorted_decisions, 1):
        priority_label = "🔴 URGENT" if decision.priority >= 80 else "🟡 MEDIUM" if decision.priority >= 50 else "🟢 LOW"
        print(f"{i}. {priority_label} [{decision.priority}] {name}")
        print(f"   Post at: {decision.when.strftime('%H:%M:%S')}")
        print()

    print("✅ Scheduler working!")


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    demo_scheduler()
