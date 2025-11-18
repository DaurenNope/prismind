#!/usr/bin/env python3
import logging

logger = logging.getLogger(__name__)
"""
Trend Analysis for BEYONDLINES
Handles trend analysis for content
"""

from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List


class TrendAnalysis:
    """Handles trend analysis for content"""

    def __init__(self):
        pass

    def analyze_trending_topics(
        self, contents: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Analyze trending topics in content"""
        if not contents:
            return []

        # Extract topics from content
        topic_counts = Counter()
        topic_engagement = defaultdict(list)

        for content in contents:
            # Extract topics from various fields
            topics = []

            # From title
            title = content.get("title", "")
            if title:
                topics.extend(self._extract_keywords(title))

            # From content
            content_text = content.get("content", "")
            if content_text:
                topics.extend(self._extract_keywords(content_text))

            # From tags
            tags = content.get("tags", [])
            if isinstance(tags, list):
                topics.extend(tags)

            # From categories
            categories = content.get("categories", [])
            if isinstance(categories, list):
                topics.extend(categories)

            # Count topics and track engagement
            for topic in topics:
                if topic and len(topic.strip()) > 2:
                    topic_lower = topic.lower().strip()
                    topic_counts[topic_lower] += 1

                    # Track engagement for this topic
                    engagement = content.get("engagement", {})
                    total_engagement = (
                        engagement.get("likes", 0)
                        + engagement.get("retweets", 0)
                        + engagement.get("replies", 0)
                    )
                    topic_engagement[topic_lower].append(total_engagement)

        # Create trending topics list
        trending_topics = []
        for topic, count in topic_counts.most_common(20):
            avg_engagement = sum(topic_engagement[topic]) / len(topic_engagement[topic])
            trending_topics.append(
                {
                    "topic": topic,
                    "count": count,
                    "average_engagement": avg_engagement,
                    "total_engagement": sum(topic_engagement[topic]),
                }
            )

        return trending_topics

    def analyze_trending_authors(
        self, contents: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Analyze trending authors in content"""
        if not contents:
            return []

        author_counts = Counter()
        author_engagement = defaultdict(list)

        for content in contents:
            author = content.get("author", "")
            if author:
                author_counts[author] += 1

                # Track engagement for this author
                engagement = content.get("engagement", {})
                total_engagement = (
                    engagement.get("likes", 0)
                    + engagement.get("retweets", 0)
                    + engagement.get("replies", 0)
                )
                author_engagement[author].append(total_engagement)

        # Create trending authors list
        trending_authors = []
        for author, count in author_counts.most_common(15):
            avg_engagement = sum(author_engagement[author]) / len(
                author_engagement[author]
            )
            trending_authors.append(
                {
                    "author": author,
                    "post_count": count,
                    "average_engagement": avg_engagement,
                    "total_engagement": sum(author_engagement[author]),
                }
            )

        return trending_authors

    def analyze_platform_distribution(
        self, contents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze platform distribution of content"""
        if not contents:
            return {}

        platform_counts = Counter()
        platform_engagement = defaultdict(list)

        for content in contents:
            platform = content.get("platform", "unknown")
            platform_counts[platform] += 1

            # Track engagement by platform
            engagement = content.get("engagement", {})
            total_engagement = (
                engagement.get("likes", 0)
                + engagement.get("retweets", 0)
                + engagement.get("replies", 0)
            )
            platform_engagement[platform].append(total_engagement)

        # Create platform distribution
        platform_distribution = {}
        for platform, count in platform_counts.items():
            avg_engagement = sum(platform_engagement[platform]) / len(
                platform_engagement[platform]
            )
            platform_distribution[platform] = {
                "count": count,
                "percentage": (count / len(contents)) * 100,
                "average_engagement": avg_engagement,
            }

        return platform_distribution

    def analyze_sentiment_trends(
        self, contents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze sentiment trends in content"""
        if not contents:
            return {}

        sentiment_counts = Counter()
        sentiment_engagement = defaultdict(list)

        for content in contents:
            sentiment = content.get("sentiment", "neutral")
            sentiment_counts[sentiment] += 1

            # Track engagement by sentiment
            engagement = content.get("engagement", {})
            total_engagement = (
                engagement.get("likes", 0)
                + engagement.get("retweets", 0)
                + engagement.get("replies", 0)
            )
            sentiment_engagement[sentiment].append(total_engagement)

        # Create sentiment trends
        sentiment_trends = {}
        for sentiment, count in sentiment_counts.items():
            avg_engagement = sum(sentiment_engagement[sentiment]) / len(
                sentiment_engagement[sentiment]
            )
            sentiment_trends[sentiment] = {
                "count": count,
                "percentage": (count / len(contents)) * 100,
                "average_engagement": avg_engagement,
            }

        return sentiment_trends

    def analyze_engagement_trends(
        self, contents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze engagement trends in content"""
        if not contents:
            return {}

        engagement_data = []
        for content in contents:
            engagement = content.get("engagement", {})
            total_engagement = (
                engagement.get("likes", 0)
                + engagement.get("retweets", 0)
                + engagement.get("replies", 0)
            )
            engagement_data.append(total_engagement)

        if not engagement_data:
            return {}

        # Calculate engagement statistics
        avg_engagement = sum(engagement_data) / len(engagement_data)
        max_engagement = max(engagement_data)
        min_engagement = min(engagement_data)

        # Categorize engagement levels
        high_engagement = sum(1 for e in engagement_data if e > avg_engagement * 2)
        medium_engagement = sum(
            1 for e in engagement_data if avg_engagement <= e <= avg_engagement * 2
        )
        low_engagement = sum(1 for e in engagement_data if e < avg_engagement)

        return {
            "average_engagement": avg_engagement,
            "max_engagement": max_engagement,
            "min_engagement": min_engagement,
            "high_engagement_count": high_engagement,
            "medium_engagement_count": medium_engagement,
            "low_engagement_count": low_engagement,
            "total_content": len(engagement_data),
        }

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text"""
        if not text:
            return []

        # Simple keyword extraction
        words = text.lower().split()

        # Filter out common words
        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "this",
            "that",
            "these",
            "those",
            "i",
            "you",
            "he",
            "she",
            "it",
            "we",
            "they",
        }

        keywords = [word for word in words if word not in stop_words and len(word) > 2]

        # Remove duplicates and return
        return list(set(keywords))

    def _parse_date(self, date_str: str) -> datetime:
        """Parse date string to datetime object"""
        try:
            if isinstance(date_str, str):
                return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            elif isinstance(date_str, datetime):
                return date_str
            else:
                return datetime.now()
        except Exception as e:
            logger.error(f"Error: {e}")
            return datetime.now()
