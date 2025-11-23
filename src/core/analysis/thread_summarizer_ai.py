#!/usr/bin/env python3
import logging

logger = logging.getLogger(__name__)
"""
Thread Summarizer AI Services
Handles AI-powered thread summarization using different AI services
"""

import json
import os
from typing import Any, Dict

import requests

from src.domain.analysis.analyzers.thread_summary import ThreadSummary


class ThreadSummarizerAI:
    """Handles AI service interactions for thread summarization"""

    def __init__(self):
        self.ollama_url = os.getenv("OLLAMA_URL")
        self.mistral_key = os.getenv("MISTRAL_API_KEY")
        self.gemini_key = os.getenv("GEMINI_API_KEY")

    def summarize_with_ollama(
        self, content: str, author: str, platform: str
    ) -> ThreadSummary:
        """Summarize using Ollama"""
        try:
            if not self.ollama_url:
                raise Exception("Ollama URL not configured")

            prompt = self._create_summarization_prompt(content, author, platform)

            payload = {
                "model": os.getenv("OLLAMA_MODEL", "qwen2.5:7b"),
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.3, "top_p": 0.9, "max_tokens": 1000},
            }

            response = requests.post(
                f"{self.ollama_url.rstrip('/')}/api/generate", json=payload, timeout=60
            )

            if response.status_code == 200:
                result = response.json()
                ai_response = result.get("response", "")
                return self._parse_ai_response(ai_response, content)
            else:
                logger.error(f"❌ Ollama API error: {response.status_code}")
                return self._create_fallback_summary(content, author, platform)

        except Exception as e:
            logger.error(f"❌ Ollama summarization failed: {e}")
            return self._create_fallback_summary(content, author, platform)

    def summarize_with_mistral(
        self, content: str, author: str, platform: str
    ) -> ThreadSummary:
        """Summarize using Mistral AI"""
        try:
            if not self.mistral_key:
                raise Exception("Mistral API key not configured")

            prompt = self._create_summarization_prompt(content, author, platform)

            headers = {
                "Authorization": f"Bearer {self.mistral_key}",
                "Content-Type": "application/json",
            }

            payload = {
                "model": "mistral-small-latest",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 1000,
                "temperature": 0.3,
            }

            response = requests.post(
                "https://api.mistral.ai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30,
            )

            if response.status_code == 200:
                result = response.json()
                ai_response = result["choices"][0]["message"]["content"]
                return self._parse_ai_response(ai_response, content)
            else:
                logger.error(f"❌ Mistral API error: {response.status_code}")
                return self._create_fallback_summary(content, author, platform)

        except Exception as e:
            logger.error(f"❌ Mistral summarization failed: {e}")
            return self._create_fallback_summary(content, author, platform)

    def summarize_with_gemini(
        self, content: str, author: str, platform: str
    ) -> ThreadSummary:
        """Summarize using Google Gemini"""
        try:
            if not self.gemini_key:
                raise Exception("Gemini API key not configured")

            import google.generativeai as genai

            genai.configure(api_key=self.gemini_key)
            model = genai.GenerativeModel("gemini-1.5-flash")

            prompt = self._create_summarization_prompt(content, author, platform)
            result = model.generate_content(prompt)
            ai_response = result.text

            return self._parse_ai_response(ai_response, content)

        except Exception as e:
            logger.error(f"❌ Gemini summarization failed: {e}")
            return self._create_fallback_summary(content, author, platform)

    def _create_summarization_prompt(
        self, content: str, author: str, platform: str
    ) -> str:
        """Create a comprehensive summarization prompt"""
        return f"""
        Analyze and summarize this {platform} thread by {author}:

        Content: "{content}"

        Please provide a structured summary with:
        1. Main topic/theme
        2. Key points (3-5 bullet points)
        3. Important insights or takeaways
        4. Overall sentiment
        5. Action items (if any)

        Format as JSON:
        {{
            "main_topic": "brief topic description",
            "key_points": ["point1", "point2", "point3"],
            "insights": ["insight1", "insight2"],
            "sentiment": "positive/negative/neutral",
            "action_items": ["action1", "action2"],
            "summary": "brief overall summary"
        }}
        """

    def _parse_ai_response(
        self, ai_response: str, original_content: str
    ) -> ThreadSummary:
        """Parse AI response into ThreadSummary object"""
        try:
            # Try to extract JSON from response
            if "{" in ai_response and "}" in ai_response:
                start = ai_response.find("{")
                end = ai_response.rfind("}") + 1
                json_str = ai_response[start:end]

                data = json.loads(json_str)

                return ThreadSummary(
                    main_topic=data.get("main_topic", ""),
                    key_points=data.get("key_points", []),
                    insights=data.get("insights", []),
                    sentiment=data.get("sentiment", "neutral"),
                    action_items=data.get("action_items", []),
                    summary=data.get("summary", ""),
                    confidence=0.9,
                    ai_service_used="ai_service",
                )
            else:
                # Fallback parsing
                return self._create_fallback_summary(original_content, "", "")

        except Exception as e:
            logger.error(f"⚠️ Error parsing AI response: {e}")
            return self._create_fallback_summary(original_content, "", "")

    def _create_fallback_summary(
        self, content: str, author: str, platform: str
    ) -> ThreadSummary:
        """Create a basic fallback summary"""
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
        }
        keywords = [
            word for word in words if len(word) > 3 and word not in common_words
        ]

        # Basic summary
        summary_text = content[:200] + "..." if len(content) > 200 else content

        return ThreadSummary(
            main_topic="Content Analysis",
            key_points=keywords[:3],
            insights=["Content processed with basic analysis"],
            sentiment="neutral",
            action_items=[],
            summary=summary_text,
            confidence=0.3,
            ai_service_used="basic",
        )
