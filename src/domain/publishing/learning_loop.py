#!/usr/bin/env python3
"""
Learning Loop System for Persona Optimization

This module implements a learning loop that:
1. Tracks content performance metrics
2. Identifies patterns in successful content
3. Provides optimization suggestions
4. Automatically improves persona configurations
"""

import json
import logging
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class ContentPerformance:
    """Track performance metrics for generated content"""
    content_id: str
    persona_id: str
    topic: str
    platform: str
    generated_at: str
    content: str
    quality_metrics: Dict[str, float]

    # Performance metrics (to be updated after posting)
    likes: int = 0
    shares: int = 0
    comments: int = 0
    clicks: int = 0
    reach: int = 0

    # Engagement metrics
    engagement_rate: float = 0.0
    virality_score: float = 0.0

    # Learning metrics
    success_score: float = 0.0
    optimization_suggestions: List[str] = None

    def __post_init__(self):
        if self.optimization_suggestions is None:
            self.optimization_suggestions = []


@dataclass
class PersonaOptimization:
    """Optimization data for a persona"""
    persona_id: str
    last_optimization: str
    optimization_history: List[Dict[str, Any]]
    performance_trends: Dict[str, List[float]]
    success_patterns: List[Dict[str, Any]]
    optimization_suggestions: List[str]

    def __post_init__(self):
        if not self.optimization_history:
            self.optimization_history = []
        if not self.performance_trends:
            self.performance_trends = {
                'engagement_rate': [],
                'virality_score': [],
                'success_score': []
            }
        if not self.success_patterns:
            self.success_patterns = []
        if not self.optimization_suggestions:
            self.optimization_suggestions = []


class LearningLoopAnalyzer:
    """Analyzes content performance and generates optimizations"""

    def __init__(self, storage_path: str = "data/learning_loop"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Performance tracking
        self.content_performance: Dict[str, ContentPerformance] = {}
        self.persona_optimizations: Dict[str, PersonaOptimization] = {}

        # Load existing data
        self._load_performance_data()
        self._load_optimization_data()

        logger.info("✅ Learning Loop Analyzer initialized")

    def _load_performance_data(self):
        """Load content performance data from storage"""
        try:
            performance_file = self.storage_path / "content_performance.json"
            if performance_file.exists():
                with open(performance_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                for content_id, content_data in data.get('performances', {}).items():
                    self.content_performance[content_id] = ContentPerformance(**content_data)

                logger.info(f"Loaded {len(self.content_performance)} content performance records")
        except Exception as e:
            logger.error(f"Failed to load performance data: {e}")

    def _load_optimization_data(self):
        """Load persona optimization data from storage"""
        try:
            optimization_file = self.storage_path / "persona_optimizations.json"
            if optimization_file.exists():
                with open(optimization_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                for persona_id, opt_data in data.get('optimizations', {}).items():
                    self.persona_optimizations[persona_id] = PersonaOptimization(**opt_data)

                logger.info(f"Loaded {len(self.persona_optimizations)} persona optimization records")
        except Exception as e:
            logger.error(f"Failed to load optimization data: {e}")

    def _save_performance_data(self):
        """Save content performance data to storage"""
        try:
            performance_file = self.storage_path / "content_performance.json"
            data = {
                'performances': {content_id: asdict(perf) for content_id, perf in self.content_performance.items()},
                'last_updated': datetime.now().isoformat()
            }

            with open(performance_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            logger.error(f"Failed to save performance data: {e}")

    def _save_optimization_data(self):
        """Save persona optimization data to storage"""
        try:
            optimization_file = self.storage_path / "persona_optimizations.json"
            data = {
                'optimizations': {persona_id: asdict(opt) for persona_id, opt in self.persona_optimizations.items()},
                'last_updated': datetime.now().isoformat()
            }

            with open(optimization_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            logger.error(f"Failed to save optimization data: {e}")

    def track_content_performance(self, content_data: Dict[str, Any]) -> str:
        """Track performance of generated content"""
        try:
            content_id = content_data.get('content_id') or f"content_{datetime.now().timestamp()}"

            performance = ContentPerformance(
                content_id=content_id,
                persona_id=content_data['persona_id'],
                topic=content_data['topic'],
                platform=content_data['platform'],
                generated_at=content_data.get('generated_at', datetime.now().isoformat()),
                content=content_data['content'],
                quality_metrics=content_data.get('quality_metrics', {})
            )

            # Calculate initial success score based on quality metrics
            quality_metrics = performance.quality_metrics
            initial_score = (
                quality_metrics.get('overall_quality', 0) * 0.4 +
                quality_metrics.get('authenticity_prediction', 0) * 0.3 +
                quality_metrics.get('engagement_potential', 0) * 0.3
            )
            performance.success_score = initial_score

            self.content_performance[content_id] = performance
            self._save_performance_data()

            logger.info(f"Tracked performance for content {content_id}")
            return content_id

        except Exception as e:
            logger.error(f"Failed to track content performance: {e}")
            return None

    def update_engagement_metrics(self, content_id: str, metrics: Dict[str, int]):
        """Update engagement metrics for a content piece"""
        try:
            if content_id not in self.content_performance:
                logger.warning(f"Content {content_id} not found in performance tracking")
                return

            performance = self.content_performance[content_id]

            # Update metrics
            performance.likes = metrics.get('likes', 0)
            performance.shares = metrics.get('shares', 0)
            performance.comments = metrics.get('comments', 0)
            performance.clicks = metrics.get('clicks', 0)
            performance.reach = metrics.get('reach', 0)

            # Calculate engagement rate (engagement / reach)
            if performance.reach > 0:
                total_engagement = performance.likes + performance.shares + performance.comments
                performance.engagement_rate = total_engagement / performance.reach

            # Calculate virality score
            performance.virality_score = self._calculate_virality_score(performance)

            # Update success score
            performance.success_score = self._calculate_success_score(performance)

            self._save_performance_data()
            logger.info(f"Updated engagement metrics for content {content_id}")

        except Exception as e:
            logger.error(f"Failed to update engagement metrics: {e}")

    def _calculate_virality_score(self, performance: ContentPerformance) -> float:
        """Calculate virality score based on engagement patterns"""
        try:
            # Weight different engagement types
            like_weight = 1.0
            share_weight = 3.0  # Shares are more valuable
            comment_weight = 2.0  # Comments indicate deep engagement

            engagement_score = (
                performance.likes * like_weight +
                performance.shares * share_weight +
                performance.comments * comment_weight
            )

            # Normalize by reach (with minimum threshold)
            normalized_reach = max(performance.reach, 1)
            virality_score = engagement_score / normalized_reach

            # Apply logarithmic scaling to prevent extreme values
            virality_score = min(virality_score * 10, 1.0)

            return virality_score

        except Exception as e:
            logger.warning(f"Failed to calculate virality score: {e}")
            return 0.0

    def _calculate_success_score(self, performance: ContentPerformance) -> float:
        """Calculate overall success score"""
        try:
            # Combine quality score with actual performance
            quality_score = (
                performance.quality_metrics.get('overall_quality', 0) * 0.3 +
                performance.quality_metrics.get('authenticity_prediction', 0) * 0.2 +
                performance.quality_metrics.get('engagement_potential', 0) * 0.2
            )

            # Combine with actual engagement performance
            performance_score = (
                performance.engagement_rate * 0.4 +
                performance.virality_score * 0.6
            )

            # Weight quality and performance
            overall_score = quality_score * 0.3 + performance_score * 0.7

            return min(overall_score, 1.0)

        except Exception as e:
            logger.warning(f"Failed to calculate success score: {e}")
            return 0.0

    def analyze_persona_performance(self, persona_id: str) -> Dict[str, Any]:
        """Analyze performance patterns for a specific persona"""
        try:
            # Get all content for this persona
            persona_contents = [
                perf for perf in self.content_performance.values()
                if perf.persona_id == persona_id
            ]

            if not persona_contents:
                return {
                    'persona_id': persona_id,
                    'total_content': 0,
                    'analysis': 'No content performance data available'
                }

            # Calculate metrics
            total_content = len(persona_contents)
            avg_engagement = np.mean([perf.engagement_rate for perf in persona_contents])
            avg_virality = np.mean([perf.virality_score for perf in persona_contents])
            avg_success = np.mean([perf.success_score for perf in persona_contents])
            best_content = max(persona_contents, key=lambda x: x.success_score)

            # Identify successful patterns
            successful_content = [perf for perf in persona_contents if perf.success_score >= 0.7]
            failed_content = [perf for perf in persona_contents if perf.success_score < 0.3]

            success_patterns = self._identify_success_patterns(successful_content, failed_content)

            # Generate optimization suggestions
            suggestions = self._generate_optimization_suggestions(persona_id, success_patterns)

            # Get optimization data
            optimization_data = self.persona_optimizations.get(persona_id, PersonaOptimization(
                persona_id=persona_id,
                last_optimization=datetime.now().isoformat(),
                optimization_history=[],
                performance_trends={},
                success_patterns=[],
                optimization_suggestions=[]
            ))

            return {
                'persona_id': persona_id,
                'total_content': total_content,
                'performance_metrics': {
                    'avg_engagement_rate': round(avg_engagement, 3),
                    'avg_virality_score': round(avg_virality, 3),
                    'avg_success_score': round(avg_success, 3),
                    'best_content_score': round(best_content.success_score, 3)
                },
                'success_rate': len(successful_content) / total_content,
                'failure_rate': len(failed_content) / total_content,
                'success_patterns': success_patterns,
                'optimization_suggestions': suggestions,
                'last_optimization': optimization_data.last_optimization,
                'optimization_history_count': len(optimization_data.optimization_history)
            }

        except Exception as e:
            logger.error(f"Failed to analyze persona performance: {e}")
            return {'error': str(e), 'persona_id': persona_id}

    def _identify_success_patterns(self, successful_content: List[ContentPerformance],
                                 failed_content: List[ContentPerformance]) -> List[Dict[str, Any]]:
        """Identify patterns in successful vs failed content"""
        patterns = []

        try:
            # Analyze topic patterns
            successful_topics = [perf.topic.lower() for perf in successful_content]
            failed_topics = [perf.topic.lower() for perf in failed_content]

            # Find topics that perform well
            topic_performance = {}
            all_topics = set(successful_topics + failed_topics)
            for topic in all_topics:
                success_count = successful_topics.count(topic)
                fail_count = failed_topics.count(topic)
                total = success_count + fail_count
                if total > 0:
                    topic_performance[topic] = success_count / total

            best_topics = sorted(topic_performance.items(), key=lambda x: x[1], reverse=True)[:5]
            if best_topics:
                patterns.append({
                    'type': 'topic_performance',
                    'pattern': 'High-performing topics',
                    'details': best_topics
                })

            # Analyze content length patterns
            successful_lengths = [len(perf.content) for perf in successful_content]
            failed_lengths = [len(perf.content) for perf in failed_content]

            if successful_lengths and failed_lengths:
                avg_success_length = np.mean(successful_lengths)
                avg_failed_length = np.mean(failed_lengths)

                if abs(avg_success_length - avg_failed_length) > 50:
                    optimal_length = avg_success_length if avg_success_length > avg_failed_length else avg_failed_length
                    patterns.append({
                        'type': 'content_length',
                        'pattern': f'Optimal content length around {int(optimal_length)} characters',
                        'details': {
                            'successful_avg': int(avg_success_length),
                            'failed_avg': int(avg_failed_length),
                            'recommendation': optimal_length
                        }
                    })

        except Exception as e:
            logger.warning(f"Failed to identify success patterns: {e}")

        return patterns

    def _generate_optimization_suggestions(self, persona_id: str, patterns: List[Dict[str, Any]]) -> List[str]:
        """Generate optimization suggestions based on performance patterns"""
        suggestions = []

        try:
            # Topic-based suggestions
            for pattern in patterns:
                if pattern['type'] == 'topic_performance':
                    best_topics = [topic for topic, score in pattern['details'].get('details', []) if score > 0.7]
                    if best_topics:
                        suggestions.append(f"Focus on topics like: {', '.join(best_topics[:3])}")

                elif pattern['type'] == 'content_length':
                    recommendations = pattern['details'].get('recommendation')
                    if recommendations:
                        suggestions.append(f"Optimal content length: ~{recommendations} characters")

            # General suggestions based on common patterns
            if len(patterns) == 0:
                suggestions.extend([
                    "Add more specific details and personal experiences",
                    "Include questions to encourage engagement",
                    "Use storytelling elements for better connection",
                    "Maintain consistent posting schedule"
                ])

        except Exception as e:
            logger.warning(f"Failed to generate optimization suggestions: {e}")
            suggestions = ["Focus on authenticity and engagement"]

        return suggestions

    def get_learning_stats(self) -> Dict[str, Any]:
        """Get overall learning loop statistics"""
        try:
            total_content = len(self.content_performance)
            total_personas = len(self.persona_optimizations)

            # Calculate overall metrics
            if self.content_performance:
                all_scores = [perf.success_score for perf in self.content_performance.values()]
                avg_success = np.mean(all_scores)
                best_score = max(all_scores)
                worst_score = min(all_scores)
            else:
                avg_success = best_score = worst_score = 0.0

            return {
                'total_content_tracked': total_content,
                'total_personas_optimized': total_personas,
                'overall_success_rate': round(avg_success, 3),
                'best_content_score': round(best_score, 3),
                'worst_content_score': round(worst_score, 3),
                'learning_loop_active': True,
                'storage_path': str(self.storage_path)
            }

        except Exception as e:
            logger.error(f"Failed to get learning stats: {e}")
            return {'error': str(e)}


# Global learning loop analyzer instance
learning_analyzer = LearningLoopAnalyzer()