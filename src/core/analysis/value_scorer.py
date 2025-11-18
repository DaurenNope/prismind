#!/usr/bin/env python3
import logging

logger = logging.getLogger(__name__)
"""
Unified Value Scorer for BEYONDLINES
Combines sophisticated scoring with intelligent analysis
"""

import re
from datetime import datetime
from typing import Any, Dict, List

from src.core.extraction.social_extractor_base import SocialPost

from .value_scorer_patterns import ValueScorerPatterns


class ValueScorer:
    """Unified value scoring system for social media content"""

    def __init__(self):
        self.patterns = ValueScorerPatterns()

    def calculate_value_score(self, post_data: Dict[str, Any]) -> float:
        """Calculate comprehensive value score for a post"""
        try:
            # Base scoring components
            content_quality = self._analyze_content_quality(post_data)
            engagement_quality = self._analyze_engagement_quality(post_data)
            learning_potential = self._analyze_learning_potential(post_data)
            recency_relevance = self._analyze_recency_relevance(post_data)
            platform_factors = self._analyze_platform_factors(post_data)

            # Calculate penalties
            penalties = self._calculate_penalties(post_data)

            # Weighted combination
            weights = {
                "content_quality": 0.35,
                "engagement_quality": 0.25,
                "learning_potential": 0.20,
                "recency_relevance": 0.10,
                "platform_factors": 0.10,
            }

            base_score = (
                content_quality * weights["content_quality"]
                + engagement_quality * weights["engagement_quality"]
                + learning_potential * weights["learning_potential"]
                + recency_relevance * weights["recency_relevance"]
                + platform_factors * weights["platform_factors"]
            )

            # Apply penalties
            final_score = max(0.0, base_score - penalties)

            return min(1.0, final_score)

        except Exception as e:
            logger.error(f"Error calculating value score: {e}")
            return 0.0

    def calculate_intelligent_value_score(
        self, analysis: Dict, post: SocialPost
    ) -> float:
        """Calculate intelligent value score using AI analysis"""
        try:
            # Base score from traditional analysis
            base_score = self.calculate_value_score(post.to_dict())

            # AI analysis factors
            ai_quality = analysis.get("quality_score", 0.5)
            ai_relevance = analysis.get("relevance_score", 0.5)
            ai_engagement = analysis.get("engagement_score", 0.5)

            # Combine with AI insights
            ai_score = (ai_quality + ai_relevance + ai_engagement) / 3

            # Weighted combination
            final_score = (base_score * 0.6) + (ai_score * 0.4)

            return min(1.0, final_score)

        except Exception as e:
            logger.error(f"Error calculating intelligent value score: {e}")
            return 0.0

    def _analyze_content_quality(self, post_data: Dict[str, Any]) -> float:
        """Analyze content quality"""
        content = post_data.get("content", "")
        if not content:
            return 0.0

        # Use patterns to analyze content
        quality_analysis = self.patterns.analyze_content_quality(content)

        # Additional quality checks
        quality_score = quality_analysis["score"]

        # Length factor
        content_length = len(content)
        if content_length < 50:
            quality_score *= 0.7
        elif content_length > 1000:
            quality_score *= 1.1

        # Structure factor
        if self.patterns.has_good_structure(content):
            quality_score *= 1.2

        # Technical depth factor
        if self.patterns.has_technical_depth(content):
            quality_score *= 1.3

        return min(1.0, quality_score)

    def _analyze_engagement_quality(self, post_data: Dict[str, Any]) -> float:
        """Analyze engagement quality"""
        engagement = post_data.get("engagement", {})
        if not engagement:
            return 0.5

        likes = engagement.get("likes", 0)
        retweets = engagement.get("retweets", 0)
        replies = engagement.get("replies", 0)

        # Calculate engagement score
        total_engagement = likes + (retweets * 2) + (replies * 3)

        # Normalize based on platform and content age
        platform = post_data.get("platform", "unknown")
        if platform == "twitter":
            if total_engagement > 100:
                return 1.0
            elif total_engagement > 50:
                return 0.8
            elif total_engagement > 20:
                return 0.6
            else:
                return 0.4
        elif platform == "reddit":
            if total_engagement > 50:
                return 1.0
            elif total_engagement > 20:
                return 0.8
            elif total_engagement > 10:
                return 0.6
            else:
                return 0.4
        else:
            # Generic scoring
            if total_engagement > 30:
                return 1.0
            elif total_engagement > 15:
                return 0.8
            elif total_engagement > 5:
                return 0.6
            else:
                return 0.4

    def _analyze_learning_potential(self, post_data: Dict[str, Any]) -> float:
        """Analyze learning potential"""
        content = post_data.get("content", "")
        if not content:
            return 0.0

        content_lower = content.lower()
        learning_score = 0.0

        # Check for learning keywords
        learning_keywords = self.patterns.learning_keywords
        learning_count = sum(
            1 for keyword in learning_keywords if keyword in content_lower
        )

        if learning_count > 0:
            learning_score = min(learning_count * 0.1, 0.8)

        # Check for educational content indicators
        educational_indicators = [
            "tutorial",
            "guide",
            "how to",
            "explanation",
            "example",
            "step by step",
            "process",
            "method",
            "technique",
            "approach",
        ]

        educational_count = sum(
            1 for indicator in educational_indicators if indicator in content_lower
        )
        if educational_count > 0:
            learning_score += min(educational_count * 0.15, 0.2)

        # Check for technical content
        if self.patterns.has_technical_depth(content):
            learning_score += 0.3

        return min(1.0, learning_score)

    def _analyze_recency_relevance(self, post_data: Dict[str, Any]) -> float:
        """Analyze recency and relevance"""
        created_at = post_data.get("created_at")
        if not created_at:
            return 0.5

        try:
            if isinstance(created_at, str):
                post_time = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            else:
                post_time = created_at

            now = datetime.now(post_time.tzinfo) if post_time.tzinfo else datetime.now()
            age_hours = (now - post_time).total_seconds() / 3600

            # Recency scoring
            if age_hours < 24:
                return 1.0
            elif age_hours < 168:  # 1 week
                return 0.8
            elif age_hours < 720:  # 1 month
                return 0.6
            elif age_hours < 2160:  # 3 months
                return 0.4
            else:
                return 0.2

        except Exception as e:
            logger.error(f"Error: {e}")
            return 0.5

    def _analyze_platform_factors(self, post_data: Dict[str, Any]) -> float:
        """Analyze platform-specific factors"""
        platform = post_data.get("platform", "unknown")

        # Platform-specific scoring
        platform_scores = {
            "twitter": 0.8,
            "reddit": 0.9,
            "threads": 0.7,
            "linkedin": 0.9,
            "github": 1.0,
            "medium": 0.9,
            "dev.to": 0.9,
            "hackernews": 0.9,
        }

        return platform_scores.get(platform, 0.5)

    def _calculate_penalties(self, post_data: Dict[str, Any]) -> float:
        """Calculate penalties for low-quality content"""
        penalties = 0.0
        content = post_data.get("content", "")

        if not content:
            return 0.5

        # Spam penalties
        content_lower = content.lower()
        spam_count = sum(
            1 for spam in self.patterns.spam_indicators if spam in content_lower
        )
        if spam_count > 0:
            penalties += min(spam_count * 0.1, 0.4)

        # Low-quality content penalties
        if len(content) < 20:
            penalties += 0.3

        # Repetitive content penalties
        words = content.split()
        if len(words) > 10:
            unique_words = set(words)
            if len(unique_words) / len(words) < 0.5:
                penalties += 0.2

        # Excessive punctuation penalties
        if content.count("!") > 5 or content.count("?") > 5:
            penalties += 0.1

        return min(0.5, penalties)

    def determine_rewrite_candidate(
        self, analysis: Dict[str, Any], post: "SocialPost", quality_score: float
    ) -> bool:
        """Determine if a post is a good candidate for rewriting"""
        # Simple logic for rewrite candidates
        if quality_score < 0.3:
            return True

        # Check for specific indicators
        content = post.content or ""
        if len(content) < 50:
            return True

        if analysis.get("sentiment", {}).get("overall", "neutral") == "negative":
            return True

        return False
