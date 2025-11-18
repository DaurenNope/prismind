#!/usr/bin/env python3
import logging

logger = logging.getLogger(__name__)
"""
Thread Summarizer Parser
Handles parsing and basic summarization functionality
"""

import re
from typing import Any, Dict, List

from src.core.analysis.thread_summary import ThreadSummary


class ThreadSummarizerParser:
    """Handles parsing and basic summarization"""

    def __init__(self):
        pass

    def parse_structured_response(self, response: str, content: str) -> ThreadSummary:
        """Parse structured response from AI services"""
        try:
            # Extract sections using regex
            main_topic = self._extract_section(
                response, r"main.topic[:\s]*([^\n]+)", "Content Analysis"
            )
            key_points = self._extract_list_section(
                response, r"key.points?[:\s]*\n?(.*?)(?=\n\n|\n[A-Z]|$)", []
            )
            insights = self._extract_list_section(
                response, r"insights?[:\s]*\n?(.*?)(?=\n\n|\n[A-Z]|$)", []
            )
            sentiment = self._extract_section(
                response, r"sentiment[:\s]*([^\n]+)", "neutral"
            )
            action_items = self._extract_list_section(
                response, r"action.items?[:\s]*\n?(.*?)(?=\n\n|\n[A-Z]|$)", []
            )
            summary = self._extract_section(
                response,
                r"summary[:\s]*([^\n]+)",
                content[:100] + "..." if len(content) > 100 else content,
            )

            return ThreadSummary(
                main_topic=main_topic,
                key_points=key_points,
                insights=insights,
                sentiment=sentiment.lower(),
                action_items=action_items,
                summary=summary,
                confidence=0.8,
                ai_service_used="parsed",
            )

        except Exception as e:
            logger.error(f"⚠️ Error parsing structured response: {e}")
            return self._create_basic_summary(content)

    def parse_ai_response(
        self, ai_response: str, original_content: str
    ) -> ThreadSummary:
        """Parse AI response with fallback strategies"""
        try:
            # Try structured parsing first
            if self._has_structured_format(ai_response):
                return self.parse_structured_response(ai_response, original_content)

            # Try to extract key information
            main_topic = self._extract_topic_from_response(ai_response)
            key_points = self._extract_points_from_response(ai_response)
            summary = self._extract_summary_from_response(ai_response, original_content)

            return ThreadSummary(
                main_topic=main_topic,
                key_points=key_points,
                insights=[summary],
                sentiment="neutral",
                action_items=[],
                summary=summary,
                confidence=0.6,
                ai_service_used="parsed",
            )

        except Exception as e:
            logger.error(f"⚠️ Error parsing AI response: {e}")
            return self._create_basic_summary(original_content)

    def basic_summarize(
        self, content: str, author: str, platform: str
    ) -> ThreadSummary:
        """Create basic summary without AI"""
        # Simple text analysis
        words = content.lower().split()
        common_words = {
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
            "may",
            "might",
            "can",
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

        # Extract keywords
        keywords = [
            word for word in words if len(word) > 3 and word not in common_words
        ]
        unique_keywords = list(set(keywords))[:5]

        # Basic summary
        if len(content) > 200:
            summary = content[:200] + "..."
        else:
            summary = content

        return ThreadSummary(
            main_topic=f"{platform} content by {author}",
            key_points=unique_keywords,
            insights=["Basic analysis completed"],
            sentiment="neutral",
            action_items=[],
            summary=summary,
            confidence=0.3,
            ai_service_used="basic",
        )

    def _extract_section(self, text: str, pattern: str, default: str) -> str:
        """Extract a section from text using regex"""
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()
        return default

    def _extract_list_section(
        self, text: str, pattern: str, default: List[str]
    ) -> List[str]:
        """Extract a list section from text"""
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            content = match.group(1).strip()
            # Split by lines and clean up
            items = [
                line.strip("- *").strip()
                for line in content.split("\n")
                if line.strip()
            ]
            return [item for item in items if item]
        return default

    def _has_structured_format(self, text: str) -> bool:
        """Check if text has structured format"""
        structured_indicators = [
            "main topic",
            "key points",
            "insights",
            "sentiment",
            "action items",
        ]
        text_lower = text.lower()
        return (
            sum(1 for indicator in structured_indicators if indicator in text_lower)
            >= 3
        )

    def _extract_topic_from_response(self, response: str) -> str:
        """Extract main topic from response"""
        # Look for topic indicators
        topic_patterns = [
            r"topic[:\s]*([^\n]+)",
            r"subject[:\s]*([^\n]+)",
            r"about[:\s]*([^\n]+)",
            r"regarding[:\s]*([^\n]+)",
        ]

        for pattern in topic_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        # Fallback: first sentence
        sentences = response.split(".")
        if sentences:
            return sentences[0].strip()

        return "Content Analysis"

    def _extract_points_from_response(self, response: str) -> List[str]:
        """Extract key points from response"""
        # Look for bullet points or numbered lists
        bullet_pattern = r"[-*•]\s*([^\n]+)"
        numbered_pattern = r"\d+\.\s*([^\n]+)"

        points = []
        for pattern in [bullet_pattern, numbered_pattern]:
            matches = re.findall(pattern, response)
            points.extend([match.strip() for match in matches])

        return points[:5]  # Limit to 5 points

    def _extract_summary_from_response(
        self, response: str, original_content: str
    ) -> str:
        """Extract summary from response"""
        # Look for summary indicators
        summary_patterns = [
            r"summary[:\s]*([^\n]+)",
            r"overview[:\s]*([^\n]+)",
            r"in summary[:\s]*([^\n]+)",
        ]

        for pattern in summary_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        # Fallback: first paragraph
        paragraphs = response.split("\n\n")
        if paragraphs:
            return paragraphs[0].strip()

        # Final fallback: original content snippet
        return (
            original_content[:100] + "..."
            if len(original_content) > 100
            else original_content
        )

    def _create_basic_summary(self, content: str) -> ThreadSummary:
        """Create basic summary as fallback"""
        return self.basic_summarize(content, "", "")
