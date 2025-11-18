#!/usr/bin/env python3
import logging

logger = logging.getLogger(__name__)
"""
AI-Powered Content Scoring for BEYONDLINES
Uses Ollama/Gemini to intelligently score content quality
"""

import os
from typing import Any, Dict, Optional


class AIContentScorer:
    """Score content quality using AI models"""

    def __init__(self):
        self.ollama_available = self._check_ollama()
        self.gemini_available = bool(os.getenv("GEMINI_API_KEY"))

    def _check_ollama(self) -> bool:
        """Check if Ollama is available"""
        try:
            import httpx

            response = httpx.get("http://localhost:11434/api/tags", timeout=2)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error: {e}")
            return False

    async def score_content(self, content: str, topics: list) -> float:
        """
        Score content quality using AI

        Args:
            content: The content to score
            topics: Matched topics with relevance

        Returns:
            Quality score between 0 and 1
        """
        # Start with topic relevance score
        base_score = topics[0]["score"] if topics else 0.3

        # Try AI scoring
        ai_score = await self._ai_quality_score(content)

        if ai_score:
            # Combine topic relevance (40%) + AI quality (60%)
            final_score = (base_score * 0.4) + (ai_score * 0.6)
        else:
            # Fallback to topic relevance + heuristics
            final_score = self._heuristic_score(content, base_score)

        return min(1.0, final_score)

    async def _ai_quality_score(self, content: str) -> Optional[float]:
        """Use AI to score content quality"""

        # Truncate content for speed
        content_sample = content[:800]

        prompt = f"""Rate the quality and value of this content on a scale of 0.0 to 1.0.

Consider:
- Is it informative and educational?
- Does it provide unique insights?
- Is it well-written and clear?
- Would tech professionals find it valuable?

Content:
{content_sample}

Respond with ONLY a number between 0.0 and 1.0 (e.g., 0.75)"""

        # Try Ollama first (fast local)
        if self.ollama_available:
            try:
                import httpx

                response = httpx.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": "qwen2.5:7b",
                        "prompt": prompt,
                        "stream": False,
                        "options": {"temperature": 0.3},
                    },
                    timeout=10,
                )

                if response.status_code == 200:
                    result = response.json()
                    text = result.get("response", "").strip()

                    # Extract number
                    try:
                        score = float(text.split()[0])
                        if 0 <= score <= 1:
                            return score
                    except Exception as e:
                        logger.error(f"Error: {e}")
                        pass

            except Exception as e:
                logger.error(f"   Ollama scoring failed: {e}")

        # Try Gemini as fallback
        if self.gemini_available:
            try:
                import google.generativeai as genai

                genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
                model = genai.GenerativeModel("gemini-1.5-flash")

                response = model.generate_content(prompt)
                text = response.text.strip()

                # Extract number
                try:
                    score = float(text.split()[0])
                    if 0 <= score <= 1:
                        return score
                except Exception as e:
                    logger.error(f"Error: {e}")
                    pass

            except Exception as e:
                logger.error(f"   Gemini scoring failed: {e}")

        return None

    def _heuristic_score(self, content: str, base_score: float) -> float:
        """Fallback heuristic scoring"""

        score = base_score

        # Length bonus (substantial content)
        if len(content) > 500:
            score += 0.1
        if len(content) > 1000:
            score += 0.1

        # Quality indicators
        quality_words = [
            "research",
            "analysis",
            "study",
            "data",
            "results",
            "findings",
            "discover",
            "innovation",
            "breakthrough",
            "tutorial",
            "guide",
            "learn",
            "example",
            "how to",
        ]

        content_lower = content.lower()
        matches = sum(1 for word in quality_words if word in content_lower)
        score += min(0.2, matches * 0.05)

        # Penalty for spam indicators
        spam_words = ["click here", "buy now", "limited time", "subscribe now"]
        spam_count = sum(1 for word in spam_words if word in content_lower)
        score -= spam_count * 0.1

        return max(0.1, min(1.0, score))

    async def batch_score(self, posts: list) -> Dict[str, float]:
        """
        Score multiple posts in batch

        Returns:
            Dict of post_id -> score
        """
        scores = {}

        for post_data in posts:
            post = post_data.get("post")
            topics = post_data.get("topics", [])

            if post:
                post_id = post.post_id or post.id
                score = await self.score_content(post.content, topics)
                scores[post_id] = score

        return scores
