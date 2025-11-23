#!/usr/bin/env python3
import logging

logger = logging.getLogger(__name__)
"""
Media Analyzer for BEYONDLINES
Handles analysis of images, videos, and other media content
"""

import json
from typing import Any, Dict, List, Optional

import requests

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer  # type: ignore
except Exception:  # pragma: no cover
    logger.error(f"Error: {e}")
    sentiment_intensity_analyzer = None  # type: ignore
else:
    sentiment_intensity_analyzer = SentimentIntensityAnalyzer  # type: ignore


class MediaAnalyzer:
    """Analyzes media content using AI vision services"""

    def __init__(self, ai_service_manager):
        self.ai_service_manager = ai_service_manager
        self.sentiment_analyzer = (
            sentiment_intensity_analyzer() if sentiment_intensity_analyzer else None
        )

    def analyze_media_content(self, media_urls: List[str]) -> Dict[str, Any]:
        """Analyze multiple media items and return comprehensive insights"""
        if not media_urls:
            return {"media_analysis": [], "total_media": 0, "insights": []}

        media_analyses = []
        for media_url in media_urls:
            analysis = self._analyze_single_media(media_url)
            if analysis:
                media_analyses.append(analysis)

        return {
            "media_analysis": media_analyses,
            "total_media": len(media_urls),
            "insights": self._extract_media_insights(media_analyses),
        }

    def _analyze_single_media(self, media_url: str) -> Optional[Dict[str, Any]]:
        """Analyze a single media item"""
        try:
            # Skip non-image/video URLs
            if not any(
                ext in media_url.lower()
                for ext in [".jpg", ".jpeg", ".png", ".gif", ".mp4", ".webp"]
            ):
                return None

            # Try Gemini vision first
            if self.ai_service_manager.has_service("gemini"):
                return self._analyze_with_gemini_vision(media_url)

            # Fallback to basic analysis
            return {
                "url": media_url,
                "type": "image"
                if any(
                    ext in media_url.lower()
                    for ext in [".jpg", ".jpeg", ".png", ".gif", ".webp"]
                )
                else "video",
                "analysis": "Media detected but AI vision not available",
                "confidence": 0.3,
            }

        except Exception as e:
            logger.error(f"⚠️ Error analyzing media {media_url}: {e}")
            return None

    def _analyze_with_gemini_vision(self, media_url: str) -> Dict[str, Any]:
        """Analyze media using Gemini vision"""
        try:
            gemini_service = self.ai_service_manager.get_service_by_name("gemini")
            vision_model = gemini_service.get("vision_model")

            if not vision_model:
                return {
                    "url": media_url,
                    "analysis": "Vision model not available",
                    "confidence": 0.0,
                }

            # Download media content
            response = requests.get(media_url, timeout=10)
            if response.status_code != 200:
                return {
                    "url": media_url,
                    "analysis": "Failed to download media",
                    "confidence": 0.0,
                }

            # Analyze with Gemini
            prompt = """
            Analyze this image/video content and provide:
            1. What you see (objects, people, text, etc.)
            2. The context or situation
            3. Any text visible in the image
            4. The overall sentiment/mood
            5. Key insights or interesting details

            Be concise but thorough.
            """

            result = vision_model.generate_content([prompt, response.content])

            return {
                "url": media_url,
                "type": "image",
                "analysis": result.text,
                "confidence": 0.9,
                "ai_service": "gemini_vision",
            }

        except Exception as e:
            logger.error(f"⚠️ Gemini vision analysis failed: {e}")
            return {
                "url": media_url,
                "analysis": f"Analysis failed: {str(e)}",
                "confidence": 0.0,
            }

    def _extract_media_insights(
        self, media_analyses: List[Dict[str, Any]]
    ) -> List[str]:
        """Extract key insights from media analyses"""
        insights = []

        for analysis in media_analyses:
            if analysis.get("confidence", 0) > 0.5:
                content = analysis.get("analysis", "")
                if "text" in content.lower() or "writing" in content.lower():
                    insights.append("Contains readable text")
                if "person" in content.lower() or "people" in content.lower():
                    insights.append("Contains people")
                if "chart" in content.lower() or "graph" in content.lower():
                    insights.append("Contains data visualization")

        return list(set(insights))  # Remove duplicates
