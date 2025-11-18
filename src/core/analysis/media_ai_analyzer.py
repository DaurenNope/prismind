#!/usr/bin/env python3
"""
Media AI Analyzer for BEYONDLINES
Handles AI analysis and value calculation for media content
"""

import logging
import re
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class MediaAIAnalyzer:
    """Handles AI analysis and value calculation for media content"""

    def __init__(self, ollama_url: str = "http://localhost:11434"):
        self.ollama_url = ollama_url

    def analyze_text_with_ai(self, text: str) -> Dict:
        """Analyze extracted text using local AI"""
        if not text or len(text.strip()) < 10:
            return {
                "content_type": "unknown",
                "relevance_score": 0.0,
                "key_topics": [],
                "sentiment": "neutral",
                "value_indicators": [],
                "ai_analysis": "No meaningful text to analyze",
            }

        try:
            # Prepare prompt for AI analysis
            prompt = f"""
            Analyze this text extracted from a social media image:

            "{text}"

            Provide analysis in this format:
            CONTENT_TYPE: [educational/technical/promotional/informational/other]
            RELEVANCE: [0.0-1.0 score]
            TOPICS: [comma-separated key topics]
            SENTIMENT: [positive/negative/neutral]
            VALUE: [comma-separated value indicators]
            ANALYSIS: [brief explanation]
            """

            # For now, return basic analysis without AI
            # In a real implementation, this would call Ollama or another AI service
            analysis = self._parse_ai_response(self._mock_ai_analysis(text))

            return analysis

        except Exception as e:
            logger.error(f"Error in AI analysis: {e}")
            return self._get_default_analysis()

    def _mock_ai_analysis(self, text: str) -> str:
        """Mock AI analysis for testing (replace with real AI call)"""
        # Simple keyword-based analysis
        text_lower = text.lower()

        content_type = "informational"
        if any(word in text_lower for word in ["tutorial", "guide", "how to", "learn"]):
            content_type = "educational"
        elif any(
            word in text_lower for word in ["code", "programming", "api", "function"]
        ):
            content_type = "technical"
        elif any(word in text_lower for word in ["buy", "sale", "discount", "offer"]):
            content_type = "promotional"

        relevance = 0.7
        if len(text) > 100:
            relevance = 0.8
        elif len(text) < 50:
            relevance = 0.5

        topics = []
        if "python" in text_lower:
            topics.append("python")
        if "javascript" in text_lower:
            topics.append("javascript")
        if "ai" in text_lower or "artificial intelligence" in text_lower:
            topics.append("artificial intelligence")
        if "web" in text_lower:
            topics.append("web development")

        sentiment = "neutral"
        if any(
            word in text_lower for word in ["great", "awesome", "excellent", "amazing"]
        ):
            sentiment = "positive"
        elif any(
            word in text_lower for word in ["bad", "terrible", "awful", "horrible"]
        ):
            sentiment = "negative"

        value_indicators = []
        if "tutorial" in text_lower:
            value_indicators.append("educational content")
        if "code" in text_lower:
            value_indicators.append("technical value")
        if len(text) > 200:
            value_indicators.append("detailed information")

        return f"""
        CONTENT_TYPE: {content_type}
        RELEVANCE: {relevance}
        TOPICS: {', '.join(topics) if topics else 'general'}
        SENTIMENT: {sentiment}
        VALUE: {', '.join(value_indicators) if value_indicators else 'basic information'}
        ANALYSIS: Text analysis based on keyword detection and length
        """

    def _parse_ai_response(self, response: str) -> Dict:
        """Parse AI response into structured format"""
        try:
            analysis = {
                "content_type": "unknown",
                "relevance_score": 0.5,
                "key_topics": [],
                "sentiment": "neutral",
                "value_indicators": [],
                "ai_analysis": "Analysis completed",
            }

            lines = response.strip().split("\n")
            for line in lines:
                line = line.strip()
                if line.startswith("CONTENT_TYPE:"):
                    analysis["content_type"] = line.split(":", 1)[1].strip()
                elif line.startswith("RELEVANCE:"):
                    try:
                        analysis["relevance_score"] = float(
                            line.split(":", 1)[1].strip()
                        )
                    except Exception as e:
                        logger.error(f"Error: {e}")
                        analysis["relevance_score"] = 0.5
                elif line.startswith("TOPICS:"):
                    topics_str = line.split(":", 1)[1].strip()
                    if topics_str and topics_str != "general":
                        analysis["key_topics"] = [
                            t.strip() for t in topics_str.split(",")
                        ]
                elif line.startswith("SENTIMENT:"):
                    analysis["sentiment"] = line.split(":", 1)[1].strip()
                elif line.startswith("VALUE:"):
                    value_str = line.split(":", 1)[1].strip()
                    if value_str and value_str != "basic information":
                        analysis["value_indicators"] = [
                            v.strip() for v in value_str.split(",")
                        ]
                elif line.startswith("ANALYSIS:"):
                    analysis["ai_analysis"] = line.split(":", 1)[1].strip()

            return analysis

        except Exception as e:
            logger.error(f"Error parsing AI response: {e}")
            return self._get_default_analysis()

    def calculate_value_boost(self, media_analysis: Dict) -> int:
        """Calculate value boost based on media analysis"""
        boost = 0

        # Content type boost
        content_type = media_analysis.get("content_type", "unknown")
        if content_type == "educational":
            boost += 15
        elif content_type == "technical":
            boost += 20
        elif content_type == "informational":
            boost += 10

        # Relevance boost
        relevance = media_analysis.get("relevance_score", 0.5)
        boost += int(relevance * 20)

        # Text content boost
        if media_analysis.get("text_content"):
            text_length = len(media_analysis["text_content"])
            if text_length > 200:
                boost += 10
            elif text_length > 100:
                boost += 5

        # Value indicators boost
        value_indicators = media_analysis.get("value_indicators", [])
        boost += len(value_indicators) * 5

        # Key topics boost
        key_topics = media_analysis.get("key_topics", [])
        boost += len(key_topics) * 3

        return min(boost, 50)  # Cap at 50 points

    def extract_media_insights(self, media_analysis: List[Dict]) -> List[str]:
        """Extract insights from media analysis"""
        insights = []

        for analysis in media_analysis:
            if analysis.get("text_content"):
                insights.append(f"Contains text: {analysis['text_content'][:100]}...")

            if analysis.get("key_topics"):
                insights.append(f"Topics: {', '.join(analysis['key_topics'])}")

            if analysis.get("value_indicators"):
                insights.append(f"Value: {', '.join(analysis['value_indicators'])}")

        return insights

    def _get_default_analysis(self) -> Dict:
        """Get default analysis when AI fails"""
        return {
            "content_type": "unknown",
            "relevance_score": 0.3,
            "key_topics": [],
            "sentiment": "neutral",
            "value_indicators": [],
            "ai_analysis": "Analysis failed - using default values",
        }
