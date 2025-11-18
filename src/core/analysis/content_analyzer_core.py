#!/usr/bin/env python3
import logging

logger = logging.getLogger(__name__)
"""
Content Analyzer Core for BEYONDLINES
Handles core content analysis and AI service interactions
"""

import json
from typing import Any, Dict, List

import requests

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer  # type: ignore
except Exception:  # pragma: no cover
    logger.error(f"Error: {e}")
    sentiment_intensity_analyzer = None  # type: ignore
else:
    sentiment_intensity_analyzer = SentimentIntensityAnalyzer  # type: ignore
from src.core.extraction.social_extractor_base import SocialPost


class ContentAnalyzerCore:
    """Core content analysis functionality"""

    def __init__(self, ai_service_manager):
        self.ai_service_manager = ai_service_manager
        self.sentiment_analyzer = (
            sentiment_intensity_analyzer() if sentiment_intensity_analyzer else None
        )

    def analyze_core_content(self, post: SocialPost) -> Dict[str, Any]:
        """Analyze the core content of a post"""
        content = post.content or ""

        # Basic sentiment analysis
        if self.sentiment_analyzer:
            sentiment_scores = self.sentiment_analyzer.polarity_scores(content)
        else:
            sentiment_scores = {"neg": 0.0, "neu": 1.0, "pos": 0.0, "compound": 0.0}

        # Content length analysis
        content_length = len(content)

        # Basic keyword extraction
        keywords = self._extract_keywords(content)

        return {
            "content_length": content_length,
            "sentiment_scores": sentiment_scores,
            "keywords": keywords,
            "has_media": len(post.media_urls or []) > 0,
            "platform": post.platform,
        }

    def create_analysis_prompt(self, post: SocialPost) -> str:
        """Create a comprehensive analysis prompt for AI"""
        content = post.content or ""
        platform = post.platform
        author = post.author or "Unknown"

        prompt = f"""
        Analyze this {platform} post by {author}:

        Content: "{content}"

        Please provide a comprehensive analysis including:
        1. Key concepts and themes
        2. Main insights and takeaways
        3. Practical applications or action items
        4. Educational value
        5. Overall quality assessment (1-10)
        6. Suggested tags for categorization

        Format your response as JSON with these fields:
        - key_concepts: array of main concepts
        - insights: array of key insights
        - action_items: array of actionable items
        - educational_value: string description
        - quality_score: number 1-10
        - suggested_tags: array of tags
        - summary: brief summary of the content
        """

        return prompt

    def analyze_with_mistral(
        self, prompt: str, sentiment_scores: Dict, service: Dict
    ) -> Dict[str, Any]:
        """Analyze content using Mistral AI"""
        try:
            headers = {
                "Authorization": f'Bearer {service["key"]}',
                "Content-Type": "application/json",
            }

            payload = {
                "model": service["model"],
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 1000,
                "temperature": 0.3,
            }

            response = requests.post(
                f"{service['base_url']}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30,
            )

            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]

                # Try to parse as JSON
                try:
                    analysis = json.loads(content)
                    analysis["ai_service"] = "mistral"
                    analysis["sentiment_analysis"] = sentiment_scores
                    return analysis
                except json.JSONDecodeError:
                    logger.error(f"Error: {e}")
                    # Fallback to text parsing
                    return self._parse_text_analysis(
                        content, sentiment_scores, "mistral"
                    )
            else:
                logger.error(f"❌ Mistral API error: {response.status_code}")
                return self._basic_analysis_fallback(sentiment_scores)

        except Exception as e:
            logger.error(f"❌ Mistral analysis failed: {e}")
            return self._basic_analysis_fallback(sentiment_scores)

    def analyze_with_ollama(
        self, prompt: str, sentiment_scores: Dict, service: Dict
    ) -> Dict[str, Any]:
        """Analyze content using Ollama"""
        try:
            payload = {
                "model": service["model"],
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.3, "top_p": 0.9, "max_tokens": 1000},
            }

            response = requests.post(
                f"{service['url']}/api/generate",
                json=payload,
                timeout=60,  # Ollama can be slower
            )

            if response.status_code == 200:
                result = response.json()
                content = result.get("response", "")

                try:
                    analysis = json.loads(content)
                    analysis["ai_service"] = "ollama"
                    analysis["sentiment_analysis"] = sentiment_scores
                    return analysis
                except json.JSONDecodeError:
                    logger.error(f"Error: {e}")
                    return self._parse_text_analysis(
                        content, sentiment_scores, "ollama"
                    )
            else:
                logger.error(f"❌ Ollama API error: {response.status_code}")
                return self._basic_analysis_fallback(sentiment_scores)

        except Exception as e:
            logger.error(f"❌ Ollama analysis failed: {e}")
            return self._basic_analysis_fallback(sentiment_scores)

    def analyze_with_gemini(
        self, prompt: str, sentiment_scores: Dict, service: Dict
    ) -> Dict[str, Any]:
        """Analyze content using Google Gemini"""
        try:
            model = service["model"]
            result = model.generate_content(prompt)
            content = result.text

            try:
                analysis = json.loads(content)
                analysis["ai_service"] = "gemini"
                analysis["sentiment_analysis"] = sentiment_scores
                return analysis
            except json.JSONDecodeError:
                logger.error(f"Error: {e}")
                return self._parse_text_analysis(content, sentiment_scores, "gemini")

        except Exception as e:
            logger.error(f"❌ Gemini analysis failed: {e}")
            return self._basic_analysis_fallback(sentiment_scores)

    def _extract_keywords(self, content: str) -> List[str]:
        """Extract basic keywords from content"""
        # Simple keyword extraction
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

        keywords = []
        for word in words:
            if len(word) > 3 and word not in common_words:
                keywords.append(word)

        # Return top 10 most frequent keywords
        from collections import Counter

        word_counts = Counter(keywords)
        return [word for word, count in word_counts.most_common(10)]

    def _parse_text_analysis(
        self, content: str, sentiment_scores: Dict, ai_service: str
    ) -> Dict[str, Any]:
        """Parse text analysis when JSON parsing fails - extract JSON from markdown"""
        import re

        # Try to extract JSON from markdown code blocks
        json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
        if json_match:
            try:
                parsed = json.loads(json_match.group(1))
                parsed["ai_service"] = ai_service
                parsed["sentiment_analysis"] = sentiment_scores
                # Ensure all required fields exist
                parsed.setdefault("key_concepts", [])
                parsed.setdefault("insights", [])
                parsed.setdefault("action_items", [])
                parsed.setdefault("educational_value", "Analysis completed")
                parsed.setdefault("quality_score", 5)
                parsed.setdefault("suggested_tags", [])
                parsed.setdefault("summary", content[:200])
                return parsed
            except json.JSONDecodeError:
                logger.error(f"Error: {e}")
                pass

        # If still no JSON, try to extract structured data from text
        key_concepts = []
        insights = []
        action_items = []

        # Extract key concepts
        concepts_match = re.search(
            r"key[_ ]concepts?:?\s*\[([^\]]+)\]", content, re.IGNORECASE
        )
        if concepts_match:
            key_concepts = [c.strip(" \"'") for c in concepts_match.group(1).split(",")]

        # Extract insights
        insights_match = re.search(
            r"insights?:?\s*\[([^\]]+)\]", content, re.IGNORECASE
        )
        if insights_match:
            insights = [i.strip(" \"'") for i in insights_match.group(1).split(",")]

        # Extract action items
        actions_match = re.search(
            r"action[_ ]items?:?\s*\[([^\]]+)\]", content, re.IGNORECASE
        )
        if actions_match:
            action_items = [a.strip(" \"'") for a in actions_match.group(1).split(",")]

        # Extract quality score
        quality_score = 5
        score_match = re.search(r"quality[_ ]score:?\s*(\d+)", content, re.IGNORECASE)
        if score_match:
            quality_score = int(score_match.group(1))

        return {
            "ai_service": ai_service,
            "sentiment_analysis": sentiment_scores,
            "key_concepts": key_concepts,
            "insights": insights if insights else ["Analysis completed"],
            "action_items": action_items,
            "educational_value": "Analysis completed",
            "quality_score": quality_score,
            "suggested_tags": key_concepts[:5],  # Use concepts as tags
            "summary": content[:200] if len(content) > 200 else content,
        }

    def _basic_analysis_fallback(self, sentiment_scores: Dict) -> Dict[str, Any]:
        """Fallback analysis when AI services fail"""
        return {
            "ai_service": "basic",
            "sentiment_analysis": sentiment_scores,
            "key_concepts": [],
            "insights": ["Content analysis completed with basic processing"],
            "action_items": [],
            "educational_value": "Basic analysis completed",
            "quality_score": 5,
            "suggested_tags": [],
            "summary": "Content processed with basic analysis",
        }
