#!/usr/bin/env python3
import logging

logger = logging.getLogger(__name__)
"""
Content Analyzer (Simplified)
=============================

Main orchestrator for content analysis using modular components.
"""

from typing import Any, Dict, List, Optional

from src.core.research.content_keyword_analyzer import ContentKeywordAnalyzer
from src.core.research.content_quality_analyzer import ContentQualityAnalyzer
from src.core.research.content_trend_analyzer import ContentTrendAnalyzer


class ContentAnalyzer:
    """Main content analyzer using modular components"""

    def __init__(self):
        self.keyword_analyzer = ContentKeywordAnalyzer()
        self.trend_analyzer = ContentTrendAnalyzer()
        self.quality_analyzer = ContentQualityAnalyzer()
        logger.info("📊 Content Analyzer initialized")

    def extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """Extract keywords from text"""
        return self.keyword_analyzer.extract_keywords(text, max_keywords)

    def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment of text"""
        return self.keyword_analyzer.analyze_sentiment(text)

    def categorize_content(self, content: Dict[str, Any]) -> str:
        """Categorize content based on analysis"""
        try:
            # Extract key information
            text = content.get("content", "") or content.get("title", "")
            platform = content.get("platform", "")
            key_concepts = content.get("key_concepts", [])

            if isinstance(key_concepts, str):
                key_concepts = []

            # Basic categorization logic
            text_lower = text.lower()

            # Technology category
            tech_keywords = [
                "programming",
                "code",
                "software",
                "ai",
                "machine learning",
                "data",
                "algorithm",
            ]
            if any(keyword in text_lower for keyword in tech_keywords):
                return "technology"

            # Business category
            business_keywords = [
                "business",
                "startup",
                "entrepreneur",
                "marketing",
                "sales",
                "finance",
            ]
            if any(keyword in text_lower for keyword in business_keywords):
                return "business"

            # Design category
            design_keywords = ["design", "ui", "ux", "graphic", "visual", "creative"]
            if any(keyword in text_lower for keyword in design_keywords):
                return "design"

            # Science category
            science_keywords = [
                "research",
                "study",
                "science",
                "experiment",
                "analysis",
            ]
            if any(keyword in text_lower for keyword in science_keywords):
                return "science"

            # Personal development
            personal_keywords = [
                "learning",
                "growth",
                "development",
                "mindset",
                "productivity",
            ]
            if any(keyword in text_lower for keyword in personal_keywords):
                return "personal_development"

            # Platform-based categorization
            if platform == "reddit":
                return "reddit_community"
            elif platform == "twitter":
                return "twitter_social"
            elif platform == "threads":
                return "threads_social"

            return "general"

        except Exception as e:
            logger.error(f"⚠️ Error categorizing content: {e}")
            return "uncategorized"

    def analyze_trends(
        self, contents: List[Dict[str, Any]], time_window_days: int = 30
    ) -> Dict[str, Any]:
        """Analyze trends in content over time"""
        return self.trend_analyzer.analyze_trends(contents, time_window_days)

    def find_content_gaps(
        self, contents: List[Dict[str, Any]], target_areas: List[str] = None
    ) -> Dict[str, Any]:
        """Find gaps in content coverage"""
        return self.trend_analyzer.find_content_gaps(contents, target_areas)

    def analyze_content_quality(self, contents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze overall content quality"""
        return self.quality_analyzer.analyze_content_quality(contents)

    def generate_content_insights(
        self, contents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate comprehensive content insights"""
        return self.quality_analyzer.generate_content_insights(contents)

    def analyze_content_collection(
        self, contents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Perform comprehensive analysis of content collection"""
        if not contents:
            return {
                "summary": "No content available for analysis",
                "recommendations": ["Add content to enable analysis"],
            }

        logger.info(f"📊 Analyzing collection of {len(contents)} items")

        # Perform various analyses
        quality_analysis = self.analyze_content_quality(contents)
        trend_analysis = self.analyze_trends(contents)
        gap_analysis = self.find_content_gaps(contents)
        insights = self.generate_content_insights(contents)

        # Generate summary
        summary = self._generate_collection_summary(
            quality_analysis, trend_analysis, gap_analysis, insights
        )

        # Generate recommendations
        recommendations = self._generate_collection_recommendations(
            quality_analysis, gap_analysis
        )

        return {
            "summary": summary,
            "quality_analysis": quality_analysis,
            "trend_analysis": trend_analysis,
            "gap_analysis": gap_analysis,
            "insights": insights,
            "recommendations": recommendations,
        }

    def _generate_collection_summary(
        self, quality_analysis, trend_analysis, gap_analysis, insights
    ) -> str:
        """Generate summary of content collection analysis"""
        total_content = quality_analysis.get("total_content", 0)
        avg_quality = quality_analysis.get("average_quality", 0)
        avg_value = quality_analysis.get("average_value", 0)

        summary_parts = [
            f"Analyzed {total_content} content items",
            f"Average quality: {avg_quality:.1f}/10",
            f"Average value: {avg_value:.1f}/10",
        ]

        # Add trending topics
        trending_topics = trend_analysis.get("trending_topics", [])
        if trending_topics:
            top_topic = trending_topics[0]["topic"] if trending_topics else "various"
            summary_parts.append(f"Top trending topic: {top_topic}")

        # Add improvement areas
        improvement_areas = gap_analysis.get("recommendations", [])
        if improvement_areas:
            summary_parts.append(
                f"{len(improvement_areas)} improvement recommendations"
            )

        return ". ".join(summary_parts) + "."

    def _generate_collection_recommendations(
        self, quality_analysis, gap_analysis
    ) -> List[str]:
        """Generate recommendations for content collection"""
        recommendations = []

        # Quality recommendations
        quality_recs = quality_analysis.get("recommendations", [])
        recommendations.extend(quality_recs)

        # Gap recommendations
        gap_recs = gap_analysis.get("recommendations", [])
        recommendations.extend(gap_recs)

        # Remove duplicates
        return list(set(recommendations))
