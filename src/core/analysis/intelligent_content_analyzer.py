import logging

logger = logging.getLogger(__name__)
"""
BEYONDLINES Intelligent Content Analyzer
=====================================

This is the core intelligence system that makes BEYONDLINES truly smart.
It analyzes not just the original post, but also:
- The most valuable comments and discussions
- Media content (images, videos) using AI vision
- Extracts actionable insights and learning points
- Provides sophisticated value scoring

Author: BEYONDLINES AI System
"""

import asyncio
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

# AI imports
import google.generativeai as genai
import requests
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# Core imports
from src.core.extraction.social_extractor_base import SocialPost
from src.publishing.persona_matcher import get_persona_matcher
from src.utils.diary_storage import DiaryStorage

from .scoring import (
    compute_persona_fit,
    guess_language,
    guess_topic,
    guess_type,
    is_rewrite_candidate,
    score_quality,
    score_value,
)


class IntelligentContentAnalyzer:
    """The brain of BEYONDLINES - provides deep analysis of social media content"""

    def __init__(self):
        """Initialize the intelligent analyzer with multiple AI backends"""

        # Initialize sentiment analyzer
        self.sentiment_analyzer = SentimentIntensityAnalyzer()
        # Initialize diary storage for contextual personalization
        try:
            self._diary = DiaryStorage()
        except Exception as e:
            logger.error(f"Error: {e}")
            self._diary = None

        # Initialize AI services (try multiple for redundancy)
        self.ai_services = []
        self._init_ai_services()

        # Simple rate limiting (RPM)
        try:
            rpm = float(os.getenv("ANALYZER_RPM", "30"))
            self._min_interval_s = 60.0 / rpm if rpm > 0 else 0.0
        except Exception as e:
            logger.error(f"Error: {e}")
            self._min_interval_s = 2.0
        self._last_call_ts = 0.0

        logger.info(
            f"🧠 Intelligent Content Analyzer initialized with {len(self.ai_services)} AI services"
        )

    def _rate_limit_sleep(self):
        import time

        if self._min_interval_s <= 0:
            return
        now = time.time()
        delta = now - self._last_call_ts
        if delta < self._min_interval_s:
            time.sleep(self._min_interval_s - delta)
        self._last_call_ts = time.time()

    def _detect_time_sensitivity(
        self, post: SocialPost, analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Heuristically detect if content is time-sensitive and estimate urgency.
        Returns: dict with time_sensitive (bool), urgency_score (0-1), relevance_window (text), time_sensitive_reasons (list)
        """
        reasons: List[str] = []
        content = (post.content or "") + "\n" + (analysis.get("ai_summary") or "")
        content_lower = content.lower()
        urgency = 0.0

        # Keyword cues
        urgent_terms = [
            "breaking",
            "just in",
            "urgent",
            "deadline",
            "today",
            "tonight",
            "hours",
            "minutes",
            "now",
            "alert",
            "update",
            "live",
            "launch",
            "announced",
            "vote",
            "earnings",
            "patch",
            "vulnerability",
            "security update",
        ]
        if any(t in content_lower for t in urgent_terms):
            reasons.append("Urgent language detected")
            urgency += 0.4

        # Category/type cues
        type_hint = (analysis.get("content_type") or "").lower()
        topic_hint = (analysis.get("topic") or "").lower()
        if any(
            k in (type_hint + " " + topic_hint)
            for k in [
                "news",
                "release",
                "incident",
                "vulnerability",
                "earnings",
                "announcement",
            ]
        ):
            reasons.append("News/incident category")
            urgency += 0.3

        # Recency
        try:
            created_at = (
                post.created_at
                if isinstance(post.created_at, datetime)
                else datetime.fromisoformat(str(post.created_at).replace("Z", "+00:00"))
            )
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            age_hours = (
                datetime.now(timezone.utc) - created_at
            ).total_seconds() / 3600.0
            if age_hours <= 6:
                reasons.append("Very recent (<6h)")
                urgency += 0.3
            elif age_hours <= 24:
                reasons.append("Recent (<24h)")
                urgency += 0.15
        except Exception as e:
            logger.error(f"Error: {e}")
            pass

        # Platform hints (Twitter/Threads often time-critical)
        if post.platform in ("twitter", "threads"):
            urgency += 0.1

        urgency = max(0.0, min(1.0, urgency))
        is_time_sensitive = urgency >= 0.35

        # Relevance window suggestion
        if urgency >= 0.7:
            window = "same-day"
        elif urgency >= 0.45:
            window = "24-72h"
        elif urgency >= 0.35:
            window = "this-week"
        else:
            window = "evergreen"

        return {
            "time_sensitive": bool(is_time_sensitive),
            "urgency_score": float(urgency),
            "relevance_window": window,
            "time_sensitive_reasons": reasons,
        }

    def _init_ai_services(self):
        """Initialize available AI services in order of preference"""

        # 0. Google Gemini (Primary by default; can be overridden via ANALYZER_PRIMARY)
        gemini_key = os.getenv("GEMINI_API_KEY")
        if gemini_key:
            genai.configure(api_key=gemini_key)
            # Use Gemini 2.5 Flash-Lite for best daily limits (1,000 RPD on Free Tier)
            # Can override with ANALYZER_GEMINI_MODEL env var if needed
            gem_model_name = os.getenv("ANALYZER_GEMINI_MODEL", "gemini-2.5-flash-lite")
            vision_model_name = os.getenv(
                "ANALYZER_GEMINI_VISION_MODEL", "gemini-1.5-pro-vision-latest"
            )
            self.gemini_model = genai.GenerativeModel(gem_model_name)
            self.gemini_vision_model = genai.GenerativeModel(vision_model_name)
            self.ai_services.append(
                {
                    "name": "gemini",
                    "model": self.gemini_model,
                    "vision_model": self.gemini_vision_model,
                }
            )
            logger.info("✅ Google Gemini initialized")

        # 1. Mistral AI (Fallback)
        mistral_key = os.getenv("MISTRAL_API_KEY")
        if mistral_key:
            self.ai_services.append(
                {
                    "name": "mistral",
                    "key": mistral_key,
                    "base_url": "https://api.mistral.ai/v1",
                    "model": "mistral-small-latest",
                }
            )
            logger.info("✅ Mistral AI initialized")

        # 2. Ollama (Local Qwen) — optional local fallback
        ollama_url = os.getenv("OLLAMA_URL")
        if ollama_url:
            self.ai_services.append(
                {
                    "name": "ollama",
                    "url": ollama_url.rstrip("/"),
                    "model": os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b"),
                    "options": {"num_predict": 150, "temperature": 0.3},
                }
            )
            logger.info("✅ Ollama (Qwen 1.5B - Fast) initialized")

        # Reorder based on ANALYZER_PRIMARY env if provided
        try:
            preferred = (os.getenv("ANALYZER_PRIMARY") or "").strip().lower()
            if preferred:
                order = [preferred, "gemini", "mistral", "ollama", "basic"]
                name_to = {s["name"]: s for s in self.ai_services}
                new_list = []
                for n in order:
                    if n in name_to:
                        new_list.append(name_to[n])
                        name_to.pop(n, None)
                # Append any remaining
                for s in self.ai_services:
                    if s["name"] not in [x["name"] for x in new_list]:
                        new_list.append(s)
                self.ai_services = new_list
        except Exception as e:
            logger.error(f"Error: {e}")
            pass

    # ---------- Rate limits / chunking ----------
    @staticmethod
    def _estimate_tokens(text: str) -> int:
        try:
            return max(1, int(len(text) / 4))  # ~4 chars per token heuristic
        except Exception as e:
            logger.error(f"Error: {e}")
            return len(text)

    def _get_rate_limits(self) -> Dict[str, int]:
        # Defaults suitable for gemini-1.5-flash style usage; override via env
        rpm = int(os.getenv("ANALYZER_RPM", "10"))
        tpm = int(os.getenv("ANALYZER_TPM", "200000"))
        rpd = int(os.getenv("ANALYZER_RPD", "250"))
        return {"rpm": rpm, "tpm": tpm, "rpd": rpd}

    def _rate_limit_guard(self, requested_tokens: int) -> None:
        """Very light in-process limiter: sleep if we exceed caps.
        Not perfect across multiprocess, but good for local/UI runs.
        """
        import time

        now = int(time.time())
        limits = self._get_rate_limits()
        window_min = now // 60
        window_day = now // 86400
        state = getattr(self, "_rl_state", None) or {
            "min": window_min,
            "min_calls": 0,
            "min_tokens": 0,
            "day": window_day,
            "day_calls": 0,
        }
        # reset windows
        if state["min"] != window_min:
            state.update({"min": window_min, "min_calls": 0, "min_tokens": 0})
        if state["day"] != window_day:
            state.update({"day": window_day, "day_calls": 0})
        # busy-wait small sleeps if would exceed
        while (
            state["min_calls"] + 1 > limits["rpm"]
            or state["min_tokens"] + requested_tokens > limits["tpm"]
            or state["day_calls"] + 1 > limits["rpd"]
        ):
            time.sleep(0.25)
            now = int(time.time())
            window_min = now // 60
            window_day = now // 86400
            if state["min"] != window_min:
                state.update({"min": window_min, "min_calls": 0, "min_tokens": 0})
            if state["day"] != window_day:
                state.update({"day": window_day, "day_calls": 0})
        # account usage
        state["min_calls"] += 1
        state["min_tokens"] += requested_tokens
        state["day_calls"] += 1
        self._rl_state = state

    def _chunk_text(self, text: str, max_tokens: int) -> List[str]:
        if not text:
            return []
        approx_chars = max_tokens * 4
        chunks: List[str] = []
        i = 0
        while i < len(text):
            chunk = text[i : i + approx_chars]
            chunks.append(chunk)
            i += approx_chars
        return chunks

        # 3. ShuttleAI (Fallback)
        if not self.ai_services:
            self.ai_services.append({"name": "basic"})
            logger.warning("⚠️ No AI services available, using basic analysis")

    async def analyze_content(self, content_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze content data and provide insights.

        This method is a wrapper around analyze_bookmark for backward compatibility.

        Args:
            content_data: Dictionary containing content information

        Returns:
            Analysis results
        """
        # Create a minimal SocialPost object from the content data
        post = SocialPost(
            post_id=content_data.get("post_id", ""),
            platform=content_data.get("platform", "unknown"),
            content=content_data.get("content", ""),
            author=content_data.get("author", ""),
            author_handle=content_data.get("author_handle", ""),
            url=content_data.get("url", ""),
            created_at=content_data.get("created_at", datetime.now().isoformat()),
            hashtags=content_data.get("hashtags", []),
            engagement=content_data.get("engagement", {}),
            media_urls=content_data.get("media_urls", []),
            post_type=content_data.get("post_type", "text"),
        )

        # Analyze the post using the existing analyze_bookmark method
        return self.analyze_bookmark(post)

    def analyze_bookmark(
        self,
        post: SocialPost,
        include_comments: bool = True,
        include_media: bool = True,
    ) -> Dict[str, Any]:
        """Analyze a bookmark with AI services, with timeout and error handling"""

        logger.info(f"🔍 Analyzing {post.platform} post: {post.post_id}")

        # Respect UI cancel flag
        try:
            from src.services.cancel_manager import is_cancelled

            if is_cancelled("analysis"):
                raise Exception("Cancelled")
        except Exception as e:
            logger.error(f"Error: {e}")
            pass

        # Deterministic mode for testing and reproducibility
        if os.getenv("DETERMINISTIC_ANALYSIS", "0") == "1":
            return self._deterministic_analysis(
                post, include_comments=include_comments, include_media=include_media
            )

        analysis = {
            "post_id": post.post_id,
            "platform": post.platform,
            "analyzed_at": datetime.now().isoformat(),
            "analysis_version": "2.0",
            "ai_analysis_succeeded": False,  # Track if AI succeeded
            "ai_service_used": None,  # Track which service was used
        }

        # 1. Core Content Analysis
        try:
            core_analysis = self._analyze_core_content(post)
            # Check if AI analysis succeeded (not fallback)
            if isinstance(core_analysis, dict):
                # Check if this was AI analysis or fallback by looking for analysis_version or ai_summary quality
                if core_analysis.get(
                    "analysis_version"
                ) != "fallback" and core_analysis.get("ai_summary"):
                    analysis["ai_analysis_succeeded"] = True
                    analysis["ai_service_used"] = core_analysis.get(
                        "analysis_model", "unknown"
                    )
                else:
                    # Fallback analysis
                    analysis["ai_analysis_succeeded"] = False
                    analysis["ai_service_used"] = None
            # Ensure core_analysis is always a dict
            if not isinstance(core_analysis, dict):
                logger.warning(
                    f"⚠️ Core content analysis returned non-dict (type: {type(core_analysis)}), using fallback"
                )
                core_analysis = self._basic_analysis(
                    post, self.sentiment_analyzer.polarity_scores(post.content or "")
                )
                analysis["ai_analysis_succeeded"] = False
                analysis["ai_service_used"] = None
            analysis.update(core_analysis)
        except Exception as e:
            logger.error(f"⚠️ Core content analysis failed: {e}")
            # Use basic analysis as fallback
            core_analysis = self._basic_analysis(
                post, self.sentiment_analyzer.polarity_scores(post.content or "")
            )
            analysis["ai_analysis_succeeded"] = False
            analysis["ai_service_used"] = None
            if isinstance(core_analysis, dict):
                analysis.update(core_analysis)
            else:
                logger.error(f"⚠️ Fallback analysis also failed, using minimal dict")
                analysis.update(
                    {
                        "summary": str(post.content)[:200] if post.content else "",
                        "category": "General",
                        "key_concepts": [],
                        "sentiment": "neutral",
                    }
                )

        # 2. Comment Analysis (Reddit only)
        if include_comments and post.platform == "reddit":
            try:
                comment_analysis = self._analyze_comments(post)
                analysis["comment_insights"] = comment_analysis
            except Exception as e:
                logger.error(f"⚠️ Comment analysis failed: {e}")
                analysis["comment_insights"] = []

        # 3. Media Analysis (only for URL-based media, disabled by default)
        enable_vision = os.getenv("ENABLE_VISION_ANALYSIS", "false").lower() in (
            "true",
            "1",
            "yes",
        )
        # Auto-enable for media-only posts (no text content)
        media_only = bool(post.media_urls) and not (
            post.content and str(post.content).strip()
        )
        if include_media and post.media_urls and (enable_vision or media_only):
            # Only analyze media URLs (not local paths or base64)
            valid_media_urls = [
                url
                for url in post.media_urls
                if isinstance(url, str)
                and (url.startswith("http://") or url.startswith("https://"))
            ]
            if valid_media_urls:
                try:
                    media_analysis = self._analyze_media_content(valid_media_urls)
                    analysis["media_insights"] = media_analysis

                    # Enhance analysis with media insights
                    if media_analysis.get("analyzed_media", 0) > 0:
                        for insight in media_analysis.get("insights", []):
                            # Add technical concepts from images
                            if (
                                "technical_concepts" in insight
                                and insight["technical_concepts"]
                            ):
                                existing_concepts = analysis.get("key_concepts", [])
                                for concept in insight["technical_concepts"]:
                                    if concept not in existing_concepts:
                                        existing_concepts.append(concept)
                                analysis["key_concepts"] = existing_concepts

                            # Flag high-value visual content
                            if (
                                insight.get("educational_value") == "high"
                                and insight.get("adds_value") == "yes"
                            ):
                                analysis["has_high_value_visuals"] = True

                            # Add extracted text to context
                            if insight.get("extracted_text"):
                                analysis["visual_text_content"] = insight[
                                    "extracted_text"
                                ]
                except Exception as e:
                    logger.error(f"⚠️ Media analysis failed: {e}")
                    analysis["media_insights"] = {
                        "total_media": len(valid_media_urls),
                        "analyzed_media": 0,
                        "insights": [],
                    }

        # Ensure analysis is always a dict (safety check)
        if not isinstance(analysis, dict):
            logger.warning(
                f"⚠️ Analysis is not a dict (type: {type(analysis)}), creating fallback dict"
            )
            analysis = {
                "post_id": post.post_id,
                "platform": post.platform,
                "analyzed_at": datetime.now().isoformat(),
                "analysis_version": "fallback",
                # Ensure persona matching can still work with fallback analysis
                "summary": str(post.content)[:200] if post.content else "",
                "category": post.hashtags[0] if post.hashtags else "General",
                "key_concepts": post.hashtags[:5] if post.hashtags else [],
                "tags": post.hashtags if post.hashtags else [],
                "sentiment": "neutral",
                "content_quality_score": 5.0,
                "intelligent_value_score": 5.0,
            }

        # 4. Time Sensitivity Detection (news/urgent)
        try:
            ts = self._detect_time_sensitivity(post, analysis)
            if isinstance(ts, dict):
                analysis.update(ts)
        except Exception as e:
            logger.error(f"⚠️ Time sensitivity detection failed: {e}")

        # 5. Advanced Value Scoring
        content_quality_score = 0.0  # Initialize before use
        try:
            value_score = self._calculate_intelligent_value_score(analysis, post)
            analysis["intelligent_value_score"] = value_score
        except Exception as e:
            logger.error(f"⚠️ Value scoring failed: {e}")
            analysis["intelligent_value_score"] = 0.0

        # 6. Content Quality Score
        try:
            content_quality_score = self._calculate_content_quality_score(
                analysis, post
            )
            analysis["content_quality_score"] = content_quality_score
        except Exception as e:
            logger.error(f"⚠️ Quality scoring failed: {e}")
            analysis["content_quality_score"] = 0.0
            content_quality_score = 0.0  # Ensure it's set even on error

        # 7. Rewrite Candidate Assessment
        try:
            is_rewrite_candidate = self._determine_rewrite_candidate(
                analysis, post, content_quality_score
            )
            analysis["is_rewrite_candidate"] = is_rewrite_candidate
        except Exception as e:
            logger.error(f"⚠️ Rewrite candidate assessment failed: {e}")
            analysis["is_rewrite_candidate"] = False

        # 8. Generate Actionable Insights
        try:
            actionable_insights = self._generate_actionable_insights(analysis, post)
            analysis["actionable_insights"] = actionable_insights
        except Exception as e:
            logger.error(f"⚠️ Actionable insights generation failed: {e}")
            analysis["actionable_insights"] = []

        # 9. Learning Recommendations
        try:
            learning_recs = self._generate_learning_recommendations(analysis, post)
            analysis["learning_recommendations"] = learning_recs
        except Exception as e:
            logger.error(f"⚠️ Learning recommendations generation failed: {e}")
            analysis["learning_recommendations"] = []

        # 10. Persona Matching (match analyzed post to personas)
        try:
            from src.services.persona_matcher import get_persona_matcher

            matcher = get_persona_matcher()
            persona_recommendations = matcher.get_recommended_personas(analysis)

            analysis["recommended_personas"] = persona_recommendations.get(
                "recommended_personas", []
            )
            analysis["persona_match_scores"] = persona_recommendations.get(
                "persona_match_scores", {}
            )
            analysis["persona_candidacy"] = persona_recommendations.get(
                "persona_candidacy", {}
            )

            if analysis["recommended_personas"]:
                logger.info(
                    f"🎭 Matched to personas: {', '.join(analysis['recommended_personas'][:3])}"
                )
        except Exception as e:
            logger.error(f"⚠️ Persona matching failed: {e}")
            analysis["recommended_personas"] = []
            analysis["persona_match_scores"] = {}
            analysis["persona_candidacy"] = {}

        logger.info(
            f"✅ Analysis complete - Value Score: {analysis.get('intelligent_value_score', 0.0)}/10"
        )
        return analysis

    def _deterministic_analysis(
        self, post: SocialPost, include_comments: bool, include_media: bool
    ) -> Dict[str, Any]:
        """Produce stable, reproducible analysis without external AI calls.

        Uses simple rules and content hashing to generate consistent outputs for tests.
        """
        import hashlib

        content = post.content or ""
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        category_pool = ["Technology", "AI", "Business", "Learning", "General"]
        category = category_pool[int(content_hash[:2], 16) % len(category_pool)]

        sentiment_scores = self.sentiment_analyzer.polarity_scores(content)

        # Deterministic rewrite angles based on content hash
        personas = ["technical", "builder", "learner", "trendsetter", "thought_leader"]
        deterministic_rewrite_angles = []
        for i, persona in enumerate(personas):
            engagement_level = ["high", "medium", "low"][int(content_hash[i], 16) % 3]
            deterministic_rewrite_angles.append(
                {
                    "persona": persona,
                    "angle": f"Deterministic {persona} angle for {category}",
                    "hook": f"Consistent hook for {persona} persona",
                    "key_points": [
                        f"Point 1 for {persona}",
                        f"Point 2 for {persona}",
                        f"Point 3 for {persona}",
                    ],
                    "target_audience": f"{persona.title()} audience",
                    "estimated_engagement": engagement_level,
                }
            )

        # Calculate content age
        try:
            created_dt = datetime.fromisoformat(post.created_at.replace("Z", "+00:00"))
            age_hours = (
                datetime.now(created_dt.tzinfo) - created_dt
            ).total_seconds() / 3600
            if age_hours < 24:
                publication_age = f"{int(age_hours)} hours"
            elif age_hours < 168:  # 7 days
                publication_age = f"{int(age_hours/24)} days"
            else:
                publication_age = f"{int(age_hours/168)} weeks"
        except Exception as e:
            logger.error(f"Error: {e}")
            publication_age = "unknown"

        analysis = {
            "post_id": post.post_id,
            "platform": post.platform,
            "analyzed_at": datetime.now().isoformat(),
            "analysis_version": "deterministic-1.0",
            "category": category,
            "subcategory": post.platform.title(),
            "content_type": post.post_type,
            "topics": post.hashtags[:3] if post.hashtags else ["general"],
            "key_concepts": [],
            "summary": content[:200] + "..." if len(content) > 200 else content,
            "why_valuable": "User bookmarked this content",
            "sentiment": "Positive"
            if sentiment_scores["compound"] > 0.2
            else ("Negative" if sentiment_scores["compound"] < -0.2 else "Neutral"),
            "complexity_level": "Unknown",
            "time_to_consume": "Unknown",
            "actionable_items": [],
            "learning_value": "Reproducible deterministic analysis",
            "practical_applications": [],
            "related_skills": [],
            "follow_up_research": [],
            "quality_indicators": [],
            "tags": post.hashtags[:5] if post.hashtags else [],
            "confidence_score": 1.0,
            "sentiment_scores": sentiment_scores,
            "ai_service": "deterministic",
            "rewrite_angles": deterministic_rewrite_angles,
            "discovery_signals": {
                "author_authority": ["high", "medium", "low"][
                    int(content_hash[5], 16) % 3
                ],
                "trend_relevance": ["emerging", "mainstream", "declining"][
                    int(content_hash[6], 16) % 3
                ],
                "viral_potential": int(content_hash[7], 16) * 6,  # 0-90 range
                "discussion_quality": ["high", "medium", "low"][
                    int(content_hash[8], 16) % 3
                ],
                "unique_perspective": "yes"
                if int(content_hash[9], 16) % 2 == 0
                else "no",
            },
            "content_freshness": {
                "publication_age": publication_age,
                "still_relevant": "yes" if int(content_hash[10], 16) % 2 == 0 else "no",
                "time_sensitivity": ["urgent", "timely", "evergreen"][
                    int(content_hash[11], 16) % 3
                ],
            },
        }

        try:
            value_score = score_value(
                analysis.get("ai_summary") or "",
                analysis.get("tags") or [],
                analysis.get("key_concepts") or [],
            )
            analysis["intelligent_value_score"] = value_score
        except Exception as e:
            logger.error(f"Error: {e}")
            analysis["intelligent_value_score"] = 5.0

        # Add content quality score and rewrite candidate assessment
        try:
            content_quality_score = score_quality(
                post.content or "",
                analysis.get("ai_summary") or "",
            )
            analysis["content_quality_score"] = content_quality_score
        except Exception as e:
            logger.error(f"Error: {e}")
            analysis["content_quality_score"] = 5.0

        try:
            analysis["is_rewrite_candidate"] = is_rewrite_candidate(
                analysis, post, content_quality_score
            )
        except Exception as e:
            logger.error(f"Error: {e}")
            analysis["is_rewrite_candidate"] = False

        if include_comments and post.platform == "reddit":
            analysis["comment_insights"] = []
        if include_media and post.media_urls:
            analysis["media_insights"] = {
                "total_media": len(post.media_urls),
                "analyzed_media": 0,
                "insights": [],
            }
        try:
            analysis["actionable_insights"] = self._generate_actionable_insights(
                analysis, post
            )
        except Exception as e:
            logger.error(f"Error: {e}")
            analysis["actionable_insights"] = []
        try:
            analysis[
                "learning_recommendations"
            ] = self._generate_learning_recommendations(analysis, post)
        except Exception as e:
            logger.error(f"Error: {e}")
            analysis["learning_recommendations"] = []
        return analysis

    def _analyze_core_content(self, post: SocialPost) -> Dict[str, Any]:
        """Analyze the main post content with AI"""

        # Get sentiment analysis
        sentiment_scores = self.sentiment_analyzer.polarity_scores(post.content)

        # Create comprehensive analysis prompt
        prompt = self._create_analysis_prompt(post)
        # Apply chunking for very long content when Gemini is primary
        try:
            if self.ai_services and self.ai_services[0]["name"] == "gemini":
                tokens = self._estimate_tokens(post.content or "")
                # Chunk if > 60% of TPM to be safe across multiple requests
                if tokens > int(self._get_rate_limits()["tpm"] * 0.6):
                    return self._analyze_with_gemini_chunked(post, sentiment_scores)
        except Exception as e:
            logger.error(f"Error: {e}")
            pass

        # Try AI services in order
        for service in self.ai_services:
            # Mid-loop cancel check
            try:
                from src.services.cancel_manager import is_cancelled

                if is_cancelled("analysis"):
                    raise Exception("Cancelled")
            except Exception as e:
                logger.error(f"Error: {e}")
                pass
            try:
                if service["name"] == "ollama":
                    return self._coerce_analysis(
                        post,
                        self._analyze_with_ollama(prompt, sentiment_scores, service),
                    )
                elif service["name"] == "mistral":
                    return self._coerce_analysis(
                        post,
                        self._analyze_with_mistral(prompt, sentiment_scores, service),
                    )
                elif service["name"] == "gemini":
                    req_tokens = self._estimate_tokens(prompt)
                    self._rate_limit_guard(req_tokens)
                    return self._coerce_analysis(
                        post,
                        self._analyze_with_gemini(prompt, sentiment_scores, service),
                    )
                else:
                    return self._coerce_analysis(
                        post, self._basic_analysis(post, sentiment_scores)
                    )
            except Exception as e:
                logger.error(f"⚠️ {service['name']} analysis failed: {e}")
                continue

        # Fallback to basic analysis
        return self._coerce_analysis(post, self._basic_analysis(post, sentiment_scores))

    def _analyze_with_gemini_chunked(
        self, post: SocialPost, sentiment_scores: Dict
    ) -> Dict[str, Any]:
        """Map-Reduce style analysis for very long content under TPM caps."""
        # Build chunks from content
        chunks = self._chunk_text(
            post.content or "", max_tokens=int(self._get_rate_limits()["tpm"] * 0.25)
        )
        partials: List[Dict[str, Any]] = []
        # Map step: summarize each chunk
        for idx, ch in enumerate(chunks, 1):
            prompt = (
                "Summarize this part of a longer post and extract key_concepts and topics as JSON: "
                '{"summary": str, "key_concepts": [str], "topics": [str]}\n\n' + ch
            )
            for service in self.ai_services:
                if service["name"] == "gemini":
                    try:
                        req_tokens = self._estimate_tokens(prompt)
                        self._rate_limit_guard(req_tokens)
                        resp = service["model"].generate_content(
                            prompt,
                            generation_config=genai.types.GenerationConfig(
                                temperature=0.1, max_output_tokens=600
                            ),
                        )
                        content = (resp.text or "").strip()
                        if content.startswith("```json"):
                            content = content[7:-3]
                        elif content.startswith("```"):
                            content = content[3:-3]
                        partial = json.loads(content)
                        partials.append(partial)
                        break
                    except Exception as e:
                        logger.error(f"⚠️ Gemini chunk {idx} failed: {e}")
                        continue
        # Reduce step: combine summaries and concepts
        combined_summary = " ".join((p.get("summary") or "") for p in partials)[:2000]
        combined_topics: List[str] = []
        combined_concepts: List[str] = []
        for p in partials:
            for arr_key, target in (
                ("topics", combined_topics),
                ("key_concepts", combined_concepts),
            ):
                vals = p.get(arr_key) or []
                for v in vals:
                    if isinstance(v, str) and v not in target:
                        target.append(v)
        # Final pass: ask Gemini to produce full analysis using combined info
        final_prompt = self._create_analysis_prompt(
            SocialPost(
                post_id=post.post_id,
                platform=post.platform,
                content=f"{combined_summary}",
                author=post.author,
                author_handle=post.author_handle,
                url=post.url,
                created_at=post.created_at,
                hashtags=list(set((post.hashtags or []) + combined_topics[:5])),
                engagement=post.engagement,
                media_urls=post.media_urls,
                post_type=post.post_type,
            )
        )
        for service in self.ai_services:
            if service["name"] == "gemini":
                req_tokens = self._estimate_tokens(final_prompt)
                self._rate_limit_guard(req_tokens)
                return self._analyze_with_gemini(
                    final_prompt, sentiment_scores, service
                )
        # Fallback
        return self._basic_analysis(post, sentiment_scores)

    def _create_analysis_prompt(self, post: SocialPost) -> str:
        """Create a comprehensive analysis prompt with improved categorization"""

        # Define specific categories to avoid generic "Technology" or "General"
        categories = [
            "AI & Machine Learning",
            "Development Tools",
            "Crypto & Web3",
            "Business & Startups",
            "Content Creation",
            "Automation & Productivity",
            "Coding & Software Engineering",
            "Data & Analytics",
            "Design & UX",
            "News & Trends",
            "Learning & Education",
            "Other",
        ]

        # Define the 5 personas for content transformation
        personas = ["technical", "builder", "learner", "trendsetter", "thought_leader"]

        # Attach recent builder diary context (short, most recent first)
        diary_context = ""
        try:
            if self._diary:
                profile_key = os.getenv("ANALYZER_PROFILE_KEY") or None
                recent = self._diary.load_entries(profile_key=profile_key, limit=5)
                if recent:
                    lines = []
                    for e in recent[:5]:
                        ts = e.get("timestamp", "")[:19].replace("T", " ")
                        shipped = (e.get("shipped") or "").strip().replace("\n", " ")
                        focus = (e.get("focus") or "").strip().replace("\n", " ")
                        short = shipped[:140] + ("..." if len(shipped) > 140 else "")
                        if focus:
                            short = f"{short} | focus: {focus[:80]}"
                        lines.append(f"- {ts} {short}")
                    diary_context = "Recent builder updates:\\n" + "\\n".join(lines)
        except Exception as e:
            logger.error(f"Error: {e}")
            diary_context = ""

        return f"""
        You are an expert content analyst. Return STRICT JSON ONLY with these keys (fill every field):
        {{
          "ai_summary": string (200-400 chars, concrete and specific),
          "tags": [string <= 8],
          "key_concepts": [string <= 8],
          "topic": string (short, e.g., "AI Agents"),
          "content_type": string ("news"|"how_to"|"opinion"|"thread"|"case_study"),
          "language": string (e.g., "en"),
          "value_score": number 0..10,
          "quality_score": number 0..10,
          "category": string (primary category: "TECH", "Dating", "Crypto", "Business", "Learning", "News", "Personal", "Health", "Entertainment", "Other", "Deprecated"),
          "fit_categories": [string] (list of categories this content fits - can be multiple, e.g. ["TECH", "Business"]),
          "rewrite_suggestions": [
            {{
              "angle": string (creative, specific rewrite angle for THIS content - unique, not generic),
              "tone": string (natural tone description, e.g., "observational, technical"),
              "approach": string (how to approach rewriting, e.g., "start with observation about X", "frame as discovery of Y"),
              "confidence": number 0..1 (how confident this angle is for this specific content)
            }}
          ] (2-3 creative rewrite suggestions, each unique to THIS content, sorted by confidence)
        }}
        INPUT:
        platform: {post.platform}  author: {post.author} @{post.author_handle}
        content: {post.content}
        hashtags: {', '.join(post.hashtags) if post.hashtags else 'None'}
        created_at: {post.created_at}  url: {post.url}

        IMPORTANT:
        1. Determine the PRIMARY category (single value) - the main category this content belongs to
        2. Determine fit_categories (array) - all categories this content could fit (can be multiple)
        3. Generate 2-3 CREATIVE rewrite suggestions that are SPECIFIC to THIS content:
           - Each angle should be UNIQUE to this content (not generic templates)
           - Be creative - think of unique ways to frame this content for rewriting
           - Each angle should have a natural tone and specific approach
           - Sort by confidence (best angle first)
           - NO hardcoded openings like "I noticed" or "Here's what"
        4. Consider the user's current narrative and focus from the recent builder updates to make judgments more context-aware and creative.

        {diary_context}

        Categories:
        - TECH: Technology, programming, AI, software, development, engineering
        - Dating: Relationships, dating advice, romance, personal connections
        - Crypto: Cryptocurrency, blockchain, DeFi, NFTs, trading
        - Business: Startups, entrepreneurship, marketing, finance, strategy
        - Learning: Education, tutorials, how-to guides, knowledge sharing
        - News: Current events, breaking news, world events, politics
        - Personal: Personal stories, life advice, self-improvement, lifestyle
        - Health: Health, fitness, nutrition, wellness, medical
        - Entertainment: Movies, music, games, fun content, memes
        - Other: Anything that doesn't fit the above categories

        Example: A post about "AI startup funding" might have:
        - category: "Business" (primary)
        - fit_categories: ["Business", "TECH"] (fits multiple categories)
        - rewrite_suggestions: [
            {{"angle": "Analyze the implications of AI funding surge on startup ecosystem", "tone": "analytical, informed", "approach": "Start with data observation, then analyze trends", "confidence": 0.85}},
            {{"angle": "Share insights on what this means for founders raising capital", "tone": "practical, advisory", "approach": "Frame as actionable advice for entrepreneurs", "confidence": 0.75}}
          ]
        """

    def _analyze_with_mistral(
        self, prompt: str, sentiment_scores: Dict, service: Dict
    ) -> Dict[str, Any]:
        """Analyze content using Mistral AI"""
        from src.utils.circuit_breaker_wrapper import get_circuit_breaker

        mistral_breaker = get_circuit_breaker(
            "mistral_ai", failure_threshold=3, recovery_timeout=30.0
        )

        @mistral_breaker.protect
        def _call_mistral():
            """Call Mistral API with circuit breaker protection"""
            self._rate_limit_sleep()
            response = requests.post(
                f"{service['base_url']}/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {service['key']}",
                },
                json={
                    "model": service["model"],
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are an expert content analyst specializing in extracting maximum value from social media bookmarks. Provide detailed, actionable insights.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": 1500,
                    "temperature": 0.1,
                },
                timeout=30,
            )

            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"].strip()

                # Clean JSON response
                if content.startswith("```json"):
                    content = content[7:-3]
                elif content.startswith("```"):
                    content = content[3:-3]

                try:
                    analysis = json.loads(content)
                    # Ensure analysis is a dictionary
                    if not isinstance(analysis, dict):
                        raise ValueError(
                            f"Analysis result is not a dictionary: {type(analysis)}"
                        )

                    analysis["sentiment_scores"] = sentiment_scores
                    analysis["ai_service"] = "mistral"

                    return analysis
                except (json.JSONDecodeError, ValueError) as e:
                    raise Exception(f"Failed to parse Mistral response as JSON: {e}")
            else:
                raise Exception(f"Mistral API error: {response.status_code}")

        return _call_mistral()

    def _analyze_with_ollama(
        self, prompt: str, sentiment_scores: Dict, service: Dict
    ) -> Dict[str, Any]:
        """Analyze content using Ollama"""
        from src.utils.circuit_breaker_wrapper import get_circuit_breaker

        ollama_breaker = get_circuit_breaker(
            "ollama", failure_threshold=3, recovery_timeout=30.0
        )

        @ollama_breaker.protect
        def _call_ollama():
            """Call Ollama API with circuit breaker protection"""
            try:
                self._rate_limit_sleep()
                url = f"{service['url']}/api/chat"
                payload = {
                    "model": service["model"],
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are an expert content analyst providing deep insights.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "stream": False,
                    "temperature": 0.7,
                    "top_p": 0.9,
                }

                # Add timeout to prevent hanging
                resp = requests.post(url, json=payload, timeout=30)  # 30 second timeout
                resp.raise_for_status()

                result = resp.json()
                content = result["message"]["content"]

                # Parse the JSON response
                try:
                    parsed = json.loads(content)
                    parsed["sentiment_scores"] = sentiment_scores
                    parsed["ai_service"] = "ollama"
                    return parsed
                except json.JSONDecodeError:
                    logger.error(f"Error: {e}")
                    # If parsing fails, create a basic structure
                    return {
                        "summary": content[:500],
                        "key_concepts": [],
                        "category": "General",
                        "sentiment_scores": sentiment_scores,
                        "ai_service": "ollama",
                    }
            except requests.exceptions.Timeout:
                logger.warning("⚠️ Ollama request timed out")
                raise Exception("Ollama analysis timed out")
            except Exception as e:
                logger.error(f"⚠️ Ollama analysis failed: {e}")
                raise

        return _call_ollama()

    def _analyze_with_gemini(
        self, prompt: str, sentiment_scores: Dict, service: Dict
    ) -> Dict[str, Any]:
        """Analyze content using Google Gemini"""
        from src.utils.circuit_breaker_wrapper import get_circuit_breaker

        gemini_breaker = get_circuit_breaker(
            "gemini_ai", failure_threshold=3, recovery_timeout=30.0
        )

        @gemini_breaker.protect
        def _call_gemini():
            """Call Gemini API with circuit breaker protection"""
            self._rate_limit_sleep()
            try:
                response = service["model"].generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.1, max_output_tokens=1500
                    ),
                )
            except Exception as e:
                logger.error(f"Error: {e}")
                raise Exception(f"Gemini request failed: {e}")

            # Try robust extraction of JSON content
            try:
                content = (getattr(response, "text", "") or "").strip()
            except Exception as e:
                logger.error(f"Error: {e}")
                content = ""
            if not content and hasattr(response, "candidates") and response.candidates:
                try:
                    content = "".join(
                        p.text or "" for p in response.candidates[0].content.parts
                    )
                except Exception as e:
                    logger.error(f"Error: {e}")
                    content = ""

            # Clean JSON response
            if content.startswith("```json"):
                content = content[7:-3]
            elif content.startswith("```"):
                content = content[3:-3]
            # Fallback: extract first JSON object via brace matching
            if not content.strip().startswith("{"):
                import re

                match = re.search(r"\{[\s\S]*\}", content)
                if match:
                    content = match.group(0)

            try:
                analysis = json.loads(content)
                if not isinstance(analysis, dict):
                    raise ValueError(
                        f"Analysis result is not a dictionary: {type(analysis)}"
                    )
            except (json.JSONDecodeError, ValueError):
                # Soft fallback: return minimal structured result
                analysis = {
                    "summary": "",
                    "value_score": 0.0,
                    "content_quality_score": 0.0,
                    "sentiment": "",
                    "key_concepts": [],
                    "tags": [],
                    "category": "unknown",
                }

            analysis["sentiment_scores"] = sentiment_scores
            analysis["ai_service"] = "gemini"
            return analysis

        return _call_gemini()

    def _coerce_analysis(
        self, post: SocialPost, analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        import re

        def _listize(x):
            if x is None:
                return []
            if isinstance(x, list):
                return [str(i).strip() for i in x if str(i).strip()]
            if isinstance(x, str):
                parts = [p.strip(" #") for p in re.split(r"[#,;]|\\n", x) if p.strip()]
                return parts[:8]
            return []

        summary = (analysis.get("ai_summary") or analysis.get("summary") or "").strip()
        if len(summary) < 50:
            base_title = getattr(post, "title", "") or ""
            base = f"{base_title}. {post.content or ''}".strip()
            summary = base[:600] or ""
        analysis["ai_summary"] = (
            summary[:600] if summary else (post.content or "")[:400]
        )

        tags = _listize(analysis.get("tags") or post.hashtags or [])
        if not tags:
            safe_title = getattr(post, "title", "") or ""
            content = f"{safe_title} {post.content or ''}"
            tags = self._extract_keywords(content)[:8]
        analysis["tags"] = tags

        kcs = _listize(analysis.get("key_concepts"))
        if not kcs:
            kcs = self._extract_keywords(post.content or "")[:8]
        analysis["key_concepts"] = kcs

        try:
            vs = float(analysis.get("value_score") or 0)
        except Exception as e:
            logger.error(f"Error: {e}")
            vs = 0
        try:
            qs = float(
                analysis.get("content_quality_score")
                or analysis.get("quality_score")
                or 0
            )
        except Exception as e:
            logger.error(f"Error: {e}")
            qs = 0
        analysis["value_score"] = (
            vs if vs > 0 else score_value(analysis["ai_summary"], tags, kcs)
        )
        analysis["quality_score"] = (
            qs if qs > 0 else score_quality(post.content or "", analysis["ai_summary"])
        )

        analysis["topic"] = (
            analysis.get("topic") or guess_topic(tags, kcs) or ""
        ).strip()[:50]
        analysis["content_type"] = (
            analysis.get("content_type") or guess_type(post) or "thread"
        ).strip()[:30]
        analysis["language"] = (
            analysis.get("language") or guess_language(post.content or "") or "en"
        ).strip()[:10]

        analysis["analysis_model"] = analysis.get("ai_service") or "gemini"
        # datetime is imported at top of file
        analysis["analyzed_at"] = datetime.utcnow().isoformat()

        # Map categories to personas (category is for discovery, best_persona_key is for rewriter)
        # Normalize category to our expected format
        raw_category = analysis.get("category", "").strip()

        # Check if post is deprecated (old time-sensitive content)
        is_deprecated = False
        created_at = post.created_at if hasattr(post, "created_at") else None
        relevance_window = analysis.get("relevance_window", "evergreen")
        urgency_score = analysis.get("urgency_score", 0.0)

        if created_at and relevance_window and relevance_window != "evergreen":
            try:
                if isinstance(created_at, str):
                    try:
                        created_dt = datetime.fromisoformat(
                            created_at.replace("Z", "+00:00")
                        )
                    except Exception as e:
                        logger.error(f"Error: {e}")
                        try:
                            created_dt = datetime.strptime(
                                created_at[:19], "%Y-%m-%dT%H:%M:%S"
                            )
                        except Exception as e:
                            logger.error(f"Error: {e}")
                            created_dt = None
                    if created_dt:
                        age_days = (
                            datetime.now(
                                created_dt.tzinfo if created_dt.tzinfo else None
                            )
                            - created_dt.replace(tzinfo=None)
                        ).days
                        if relevance_window == "same-day" and age_days > 1:
                            is_deprecated = True
                        elif relevance_window == "24-72h" and age_days > 3:
                            is_deprecated = True
                        elif relevance_window == "this-week" and age_days > 7:
                            is_deprecated = True
                        elif urgency_score > 0.5 and age_days > 7:
                            is_deprecated = True
            except Exception as e:
                logger.error(f"Error: {e}")
                pass

        # If deprecated, set category to DEPRECATED
        if is_deprecated:
            raw_category = "DEPRECATED"
            analysis["category"] = "DEPRECATED"

        # If category is missing or empty, try to infer from content
        # BUT: preserve AI-provided category if it exists (don't override AI analysis)
        ai_provided_category = (
            analysis.get("category")
            and raw_category
            and raw_category.lower() not in ["unknown", "other", "general", ""]
        )
        if not raw_category or raw_category.lower() in [
            "unknown",
            "other",
            "general",
            "",
        ]:
            # Only infer if AI didn't provide a category
            # Check if this is a fallback analysis (low confidence means AI failed)
            is_fallback = analysis.get(
                "analysis_version"
            ) == "fallback" or not analysis.get("ai_analysis_succeeded", True)

            if is_fallback:
                # Infer category from content keywords only for fallback analysis
                content_lower = (post.content or "").lower()
                if any(
                    kw in content_lower
                    for kw in [
                        "crypto",
                        "bitcoin",
                        "blockchain",
                        "defi",
                        "nft",
                        "ethereum",
                        "web3",
                        "token",
                    ]
                ):
                    raw_category = "CRYPTO"
                elif any(
                    kw in content_lower
                    for kw in [
                        "dating",
                        "relationship",
                        "romance",
                        "love",
                        "partner",
                        "single",
                        "marriage",
                    ]
                ):
                    raw_category = "DATING"
                elif any(
                    kw in content_lower
                    for kw in [
                        "ai",
                        "code",
                        "programming",
                        "software",
                        "tech",
                        "developer",
                        "engineering",
                        "startup",
                        "business",
                    ]
                ):
                    raw_category = "TECH"
                elif any(
                    kw in content_lower
                    for kw in [
                        "startup",
                        "business",
                        "entrepreneur",
                        "marketing",
                        "finance",
                        "invest",
                        "revenue",
                    ]
                ):
                    raw_category = "BUSINESS"
                elif any(
                    kw in content_lower
                    for kw in [
                        "learn",
                        "tutorial",
                        "how to",
                        "guide",
                        "education",
                        "course",
                        "study",
                    ]
                ):
                    raw_category = "LEARNING"
                else:
                    raw_category = "OTHER"
            else:
                # AI succeeded but didn't provide category - keep it as OTHER (don't override with simple inference)
                raw_category = "OTHER"

        category = self._normalize_category(raw_category)

        fit_categories = analysis.get("fit_categories", [])
        if isinstance(fit_categories, str):
            # Try to parse as JSON if it's a string
            try:
                import json

                fit_categories = json.loads(fit_categories)
            except Exception as e:
                logger.error(f"Error: {e}")
                fit_categories = []
        if not isinstance(fit_categories, list):
            fit_categories = []
        # Normalize fit_categories to our expected format
        fit_categories = [
            self._normalize_category(c.strip()) for c in fit_categories if c
        ]
        # Remove empty strings and duplicates
        fit_categories = list(set([c for c in fit_categories if c]))

        valid_categories = [
            "TECH",
            "DATING",
            "CRYPTO",
            "BUSINESS",
            "LEARNING",
            "NEWS",
            "PERSONAL",
            "HEALTH",
            "ENTERTAINMENT",
            "OTHER",
            "DEPRECATED",
        ]

        # Category to persona mapping (for the 3 main personas)
        category_to_persona = {
            "TECH": "qronoya",
            "DATING": "aspandead",
            "CRYPTO": "claimzilla",
            "BUSINESS": "qronoya",  # Business content goes to tech persona
            "LEARNING": "qronoya",  # Learning content goes to tech persona
        }

        # Always compute persona fit scores using sophisticated PersonaMatcher
        # NEW: Calculate profile_matches for ALL dynamically loaded profiles (0-100 format for JSONB)
        try:
            matcher = get_persona_matcher()
            # Get scores for ALL profiles (not just top 3) - set max_personas high
            all_profile_keys = list(matcher.persona_profiles.keys())
            persona_matches = matcher.match_personas(
                analysis, min_personas=1, max_personas=len(all_profile_keys) or 10
            )

            # NEW: Build profile_matches JSONB (0-100 format, dynamic - works with any number of profiles)
            profile_matches = {}
            for persona_id in all_profile_keys:
                # Find score for this persona (default to 0 if not in matches)
                score = 0.0
                for pid, raw_score, _ in persona_matches:
                    if pid == persona_id:
                        score = round(raw_score, 2)  # Keep 0-100 format for JSONB
                        break
                profile_matches[persona_id] = score

            analysis["profile_matches"] = profile_matches

            # OLD: Keep persona_fit_scores for backward compatibility (0-10 scale)
            # Convert PersonaMatcher results (score 0-100+) to normalized 0-10 scale
            persona_fit_scores = {}
            persona_fit_reasons = {}

            for persona_id, raw_score, reason in persona_matches:
                # Normalize: PersonaMatcher uses 0-100+ scale, we store 0-10
                normalized_score = round(min(raw_score / 10.0, 10.0), 2)
                persona_fit_scores[persona_id] = normalized_score
                persona_fit_reasons[persona_id] = [reason] if reason else []

            # Also compute scores for all personas (even if below threshold) for completeness
            for persona_id in all_profile_keys:
                if persona_id not in persona_fit_scores:
                    persona_fit_scores[persona_id] = 0.0
                    persona_fit_reasons[persona_id] = []

            # Determine best persona (highest score)
            if persona_matches:
                best_key, raw_best_score, best_reason = persona_matches[0]
                best_score = round(min(raw_best_score / 10.0, 10.0), 2)
                best_reasons = [best_reason] if best_reason else []
            else:
                best_key = None
                best_score = 0.0
                best_reasons = []

            # Keep old fields for backward compatibility
            analysis["persona_fit_scores"] = persona_fit_scores
            analysis["persona_fit_reasons"] = persona_fit_reasons
        except Exception as e:
            logger.error(f"⚠️ Persona matching failed: {e}")
            # Fallback to simple keyword matching
            try:
                persona_fit = compute_persona_fit(post, analysis)
                # Convert 0-1 scale to 0-10 scale
                persona_scores_raw = persona_fit.get("scores", {})
                persona_fit_scores = {
                    k: round(v * 10.0, 2) for k, v in persona_scores_raw.items()
                }
                persona_fit_reasons = {
                    k: v if isinstance(v, list) else [v]
                    for k, v in persona_fit.get("reasons", {}).items()
                }
                best_key = persona_fit.get("best_persona")
                best_score_raw = persona_fit.get("best_score", 0.0)
                best_score = round(best_score_raw * 10.0, 2)  # Convert 0-1 to 0-10
                best_reasons = persona_fit_reasons.get(best_key, []) if best_key else []

                # NEW: Also create profile_matches from fallback scores (0-100 format)
                profile_matches = {}
                for pid, score_0_10 in persona_fit_scores.items():
                    # Convert 0-10 scale to 0-100 scale for profile_matches
                    profile_matches[pid] = round(score_0_10 * 10.0, 2)

                analysis["profile_matches"] = profile_matches
                analysis["persona_fit_scores"] = persona_fit_scores
                analysis["persona_fit_reasons"] = persona_fit_reasons
            except Exception as e:
                logger.error(f"Error: {e}")
                best_key = None
                best_score = 0.0
                best_reasons = []
                analysis["profile_matches"] = {}  # Empty but valid JSONB
                analysis["persona_fit_scores"] = {}
                analysis["persona_fit_reasons"] = {}

        # If deprecated, don't assign persona (deprecated content shouldn't be rewritten)
        if category == "DEPRECATED":
            selected_persona = None
            selected_reason = "Content is deprecated (old time-sensitive post)"
        else:
            # Determine best_persona_key from fit_categories (can fit multiple categories)
            # Priority: CRYPTO > DATING > TECH/BUSINESS/LEARNING
            persona_candidates = []

            # Check fit_categories first (more comprehensive)
            for fit_cat in fit_categories:
                if fit_cat in category_to_persona:
                    persona = category_to_persona[fit_cat]
                    if persona not in persona_candidates:
                        persona_candidates.append(persona)

            # Also check primary category
            if category and category in category_to_persona:
                persona = category_to_persona[category]
                if persona not in persona_candidates:
                    persona_candidates.insert(
                        0, persona
                    )  # Primary category gets priority

            # Determine best persona: priority order (CRYPTO > DATING > TECH)
            if "claimzilla" in persona_candidates:
                selected_persona = "claimzilla"
                selected_reason = f"Fits categories: {', '.join([c for c in fit_categories if category_to_persona.get(c) == 'claimzilla'])}"
            elif "aspandead" in persona_candidates:
                selected_persona = "aspandead"
                selected_reason = f"Fits categories: {', '.join([c for c in fit_categories if category_to_persona.get(c) == 'aspandead'])}"
            elif "qronoya" in persona_candidates:
                selected_persona = "qronoya"
                selected_reason = f"Fits categories: {', '.join([c for c in fit_categories if category_to_persona.get(c) == 'qronoya'])}"
            elif best_key:
                # Use persona matching result if no category match
                selected_persona = best_key
                selected_reason = f"Persona matching: {', '.join(best_reasons)}"
            else:
                # Final fallback: try to infer persona from content keywords
                content_lower = (post.content or "").lower()
                if any(
                    kw in content_lower
                    for kw in [
                        "crypto",
                        "bitcoin",
                        "blockchain",
                        "defi",
                        "nft",
                        "ethereum",
                        "web3",
                        "token",
                    ]
                ):
                    selected_persona = "claimzilla"
                    selected_reason = "Inferred from content keywords (crypto)"
                elif any(
                    kw in content_lower
                    for kw in [
                        "dating",
                        "relationship",
                        "romance",
                        "love",
                        "partner",
                        "single",
                        "marriage",
                    ]
                ):
                    selected_persona = "aspandead"
                    selected_reason = "Inferred from content keywords (dating)"
                elif any(
                    kw in content_lower
                    for kw in [
                        "ai",
                        "code",
                        "programming",
                        "software",
                        "tech",
                        "developer",
                        "engineering",
                        "startup",
                        "business",
                    ]
                ):
                    selected_persona = "qronoya"
                    selected_reason = "Inferred from content keywords (tech)"
                else:
                    selected_persona = None
                    selected_reason = "No persona match found"

        # Set best_persona_key and related fields
        analysis["best_persona_key"] = selected_persona
        if selected_persona:
            # Use persona matching score if available (already normalized to 0-10)
            if selected_persona == best_key and best_score > 0:
                analysis["best_persona_score"] = best_score  # Already 0-10 scale
            elif (
                selected_persona in persona_fit_scores
                and persona_fit_scores[selected_persona] > 0
            ):
                # Use PersonaMatcher score for this persona (already normalized to 0-10)
                analysis["best_persona_score"] = persona_fit_scores[selected_persona]
            else:
                # Use persona_candidates if available, otherwise default score
                has_candidates = "persona_candidates" in locals() and persona_candidates
                analysis["best_persona_score"] = 8.0 if has_candidates else 5.0
            analysis["best_persona_reasons"] = (
                [selected_reason] if selected_reason else []
            )
        else:
            analysis["best_persona_score"] = 0.0
            analysis["best_persona_reasons"] = []

        # Store fit_categories for discovery/filtering (normalize to list)
        if fit_categories:
            analysis["fit_categories"] = fit_categories
        elif category:
            analysis["fit_categories"] = [category]
        else:
            analysis["fit_categories"] = []

        # NEW: Extract and store rewrite_suggestions from AI analysis (if provided)
        rewrite_suggestions = analysis.get("rewrite_suggestions", [])
        if isinstance(rewrite_suggestions, str):
            try:
                import json

                rewrite_suggestions = json.loads(rewrite_suggestions)
            except Exception as e:
                logger.error(f"Error: {e}")
                rewrite_suggestions = []
        if not isinstance(rewrite_suggestions, list):
            rewrite_suggestions = []

        # Validate and clean rewrite suggestions
        validated_suggestions = []
        for suggestion in rewrite_suggestions[:3]:  # Max 3 suggestions
            if isinstance(suggestion, dict) and "angle" in suggestion:
                validated_suggestions.append(
                    {
                        "angle": str(suggestion.get("angle", "")),
                        "tone": str(suggestion.get("tone", "natural")),
                        "approach": str(suggestion.get("approach", "")),
                        "confidence": float(suggestion.get("confidence", 0.7)),
                    }
                )

        # Sort by confidence (best first)
        validated_suggestions.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        analysis["rewrite_suggestions"] = validated_suggestions

        # Rewrite-oriented defaults if missing
        if "rewrite_score" not in analysis:
            # Heuristic from summary and structure
            rs = score_value(
                analysis["ai_summary"], analysis["tags"], analysis["key_concepts"]
            )
            analysis["rewrite_score"] = rs
        if "rewrite_readiness" not in analysis:
            summary_len = len(analysis["ai_summary"] or "")
            analysis["rewrite_readiness"] = (
                "ready"
                if summary_len >= 150
                else ("needs_context" if summary_len < 80 else "needs_trim")
            )
        if "rewrite_reasons" not in analysis:
            analysis["rewrite_reasons"] = [
                f"Good tags ({len(analysis['tags'])})",
                f"Concepts ({len(analysis['key_concepts'])})",
            ]
        if "rewrite_risks" not in analysis:
            risks = []
            if len(analysis["ai_summary"]) < 120:
                risks.append("Short summary")
            if not analysis["tags"]:
                risks.append("No tags")
            analysis["rewrite_risks"] = risks
        # Calculate dynamic analysis confidence based on AI success and quality
        if "analysis_confidence" not in analysis:
            if analysis.get("ai_analysis_succeeded"):
                # AI succeeded - calculate confidence based on analysis quality
                ai_summary_len = len(analysis.get("ai_summary", "") or "")
                has_tags = bool(analysis.get("tags"))
                has_concepts = bool(analysis.get("key_concepts"))
                has_category = bool(analysis.get("category"))

                # Base confidence for AI analysis
                confidence = 0.7

                # Increase confidence based on quality indicators
                if ai_summary_len >= 150:
                    confidence += 0.1
                if ai_summary_len >= 200:
                    confidence += 0.05
                if has_tags and has_concepts:
                    confidence += 0.1
                if has_category:
                    confidence += 0.05

                # Cap at 0.95 (never 100% - AI can be wrong)
                analysis["analysis_confidence"] = round(min(confidence, 0.95), 2)
            else:
                # Fallback analysis - low confidence
                analysis["analysis_confidence"] = 0.3

        # Calculate dynamic analysis depth based on AI service used
        if "analysis_depth" not in analysis:
            ai_service = analysis.get("ai_service_used", "").lower()
            if ai_service in ("gemini", "mistral"):
                analysis["analysis_depth"] = "deep"  # Sophisticated AI models
            elif ai_service == "ollama":
                analysis["analysis_depth"] = "medium"  # Local model
            else:
                analysis["analysis_depth"] = "fast"  # Fallback/basic analysis

        # Determine if deep analysis is needed
        if "needs_deep_analysis" not in analysis:
            rewrite_score = analysis.get("rewrite_score", 0)
            confidence = analysis.get("analysis_confidence", 0.7)
            # Need deep analysis if high value but low confidence
            analysis["needs_deep_analysis"] = rewrite_score >= 8 and confidence < 0.8

        return analysis

    def _persona_fit_scores(self, post: SocialPost, analysis: Dict[str, Any]):
        pass

    def _extract_keywords(self, text: str) -> List[str]:
        if not text:
            return []
        import re

        words = [w.lower() for w in re.findall(r"[A-Za-z][A-Za-z0-9_+-]{3,}", text)]
        freq: Dict[str, int] = {}
        for w in words:
            freq[w] = freq.get(w, 0) + 1
        return [w for w, _ in sorted(freq.items(), key=lambda kv: (-kv[1], kv[0]))][:10]

    def _score_value(self, summary: str, tags: List[str], concepts: List[str]) -> float:
        score = 0
        if len(summary) > 120:
            score += 3
        if tags:
            score += 2
        if concepts:
            score += 2
        if any(
            k in summary.lower()
            for k in ("how to", "guide", "step", "tips", "framework")
        ):
            score += 2
        return float(max(1, min(10, score)))

    def _score_quality(self, content: str, summary: str) -> float:
        score = 0
        if len(summary) > 150:
            score += 3
        if len(content) > 300:
            score += 2
        if any(p in summary for p in (":", "-", ";")):
            score += 1
        return float(max(1, min(10, score)))

    def _guess_topic(self, tags: List[str], concepts: List[str]) -> str:
        pool = (tags or []) + (concepts or [])
        if not pool:
            return "General"
        return pool[0][:50]

    def _guess_type(self, post: SocialPost) -> str:
        if post.post_type and post.post_type.lower() in ("thread", "tweet", "post"):
            return "thread" if post.platform in ("threads", "twitter") else "post"
        if getattr(post, "title", None) and len(post.content or "") > 600:
            return "how_to"
        return "opinion"

    def _guess_language(self, text: str) -> str:
        try:
            import re

            if re.search(r"[А-Яа-я]", text):
                return "ru"
            if re.search(r"[\u0600-\u06FF]", text):
                return "ar"
            return "en"
        except Exception as e:
            logger.error(f"Error: {e}")
            return "en"

    def _normalize_category(self, category: str) -> str:
        """Normalize category to our expected format (TECH, DATING, CRYPTO, etc.)"""
        if not category:
            return ""

        category_upper = category.upper()

        # Map common category variations to our standard categories
        category_mapping = {
            # TECH variations
            "TECH": "TECH",
            "TECHNOLOGY": "TECH",
            "AI": "TECH",
            "AI & MACHINE LEARNING": "TECH",
            "MACHINE LEARNING": "TECH",
            "ARTIFICIAL INTELLIGENCE": "TECH",
            "SOFTWARE": "TECH",
            "DEVELOPMENT": "TECH",
            "DEVELOPMENT TOOLS": "TECH",
            "PROGRAMMING": "TECH",
            "ENGINEERING": "TECH",
            "COMPUTER SCIENCE": "TECH",
            # CRYPTO variations
            "CRYPTO": "CRYPTO",
            "CRYPTOCURRENCY": "CRYPTO",
            "CRYPTO & WEB3": "CRYPTO",
            "WEB3": "CRYPTO",
            "BLOCKCHAIN": "CRYPTO",
            "DEFI": "CRYPTO",
            "BITCOIN": "CRYPTO",
            "ETHEREUM": "CRYPTO",
            # DATING variations
            "DATING": "DATING",
            "RELATIONSHIPS": "DATING",
            "RELATIONSHIP": "DATING",
            "LOVE": "DATING",
            "ROMANCE": "DATING",
            # BUSINESS variations
            "BUSINESS": "BUSINESS",
            "BUSINESS & STARTUPS": "BUSINESS",
            "STARTUPS": "BUSINESS",
            "ENTREPRENEURSHIP": "BUSINESS",
            "MARKETING": "BUSINESS",
            "FINANCE": "BUSINESS",
            # LEARNING variations
            "LEARNING": "LEARNING",
            "EDUCATION": "LEARNING",
            "TUTORIAL": "LEARNING",
            "HOW-TO": "LEARNING",
            # NEWS variations
            "NEWS": "NEWS",
            "CURRENT EVENTS": "NEWS",
            "POLITICS": "NEWS",
            # PERSONAL variations
            "PERSONAL": "PERSONAL",
            "LIFESTYLE": "PERSONAL",
            "SELF-IMPROVEMENT": "PERSONAL",
            # HEALTH variations
            "HEALTH": "HEALTH",
            "FITNESS": "HEALTH",
            "WELLNESS": "HEALTH",
            # ENTERTAINMENT variations
            "ENTERTAINMENT": "ENTERTAINMENT",
            "MOVIES": "ENTERTAINMENT",
            "MUSIC": "ENTERTAINMENT",
            "GAMES": "ENTERTAINMENT",
        }

        # Check exact match first
        if category_upper in category_mapping:
            return category_mapping[category_upper]

        # Check if category contains any of our keywords
        for key, value in category_mapping.items():
            if key in category_upper and key != category_upper:
                return value

        # Default to OTHER if no match
        return "OTHER"

    def _analyze_comments(self, post: SocialPost) -> Dict[str, Any]:
        """Analyze Reddit comments to extract valuable insights"""

        # This would integrate with Reddit API to get comments
        # For now, return placeholder structure
        return {
            "top_insights": [
                "Most valuable comment insights would appear here",
                "Community consensus and expert opinions",
                "Practical tips and experiences shared",
            ],
            "expert_opinions": [],
            "common_questions": [],
            "practical_tips": [],
            "warnings_caveats": [],
            "additional_resources": [],
        }

    def _analyze_media_content(self, media_urls: List[str]) -> Dict[str, Any]:
        """Analyze images and videos using AI vision"""

        media_insights = {
            "total_media": len(media_urls),
            "analyzed_media": 0,
            "insights": [],
        }

        for url in media_urls[:3]:  # Analyze first 3 media items
            try:
                insight = self._analyze_single_media(url)
                if insight:
                    media_insights["insights"].append(insight)
                    media_insights["analyzed_media"] += 1
            except Exception as e:
                logger.error(f"⚠️ Media analysis failed for {url}: {e}")

        return media_insights

    def _analyze_single_media(self, media_url: str) -> Optional[Dict[str, Any]]:
        """Analyze a single media item using AI vision

        Only processes HTTP/HTTPS URLs. Skips local paths, base64, or other non-URL formats.
        """
        # Guard: only process valid HTTP/HTTPS URLs
        if not isinstance(media_url, str) or not (
            media_url.startswith("http://") or media_url.startswith("https://")
        ):
            logger.warning(f"⚠️ Skipping non-URL media: {media_url[:50]}...")
            return None

        # Check if we have Gemini Vision available
        for service in self.ai_services:
            if service["name"] == "gemini" and "vision_model" in service:
                try:
                    # Download image
                    response = requests.get(media_url, timeout=10)
                    if response.status_code != 200:
                        logger.error(f"Failed to download image: {media_url}")
                        continue

                    # Save image temporarily
                    from io import BytesIO

                    from PIL import Image

                    img = Image.open(BytesIO(response.content))

                    # Create comprehensive vision analysis prompt
                    vision_prompt = """
                    Analyze this image from a social media post and provide structured insights.

                    Return a JSON response with this structure:
                    {
                      "content_type": "diagram/code/screenshot/infographic/photo/chart/other",
                      "description": "What is shown in the image (2-3 sentences)",
                      "key_elements": ["element1", "element2", "element3"],
                      "extracted_text": "Any visible text or code (if applicable)",
                      "technical_concepts": ["concept1", "concept2"],
                      "educational_value": "high/medium/low",
                      "practical_insights": ["insight1", "insight2"],
                      "adds_value": "yes/no - Does this image add significant value to understanding the content?"
                    }

                    Focus on technical, educational, and practical value.
                    Return ONLY valid JSON, no additional text.
                    """

                    # Use Gemini Vision to analyze
                    vision_response = service["vision_model"].generate_content(
                        [vision_prompt, img],
                        generation_config=genai.types.GenerationConfig(
                            temperature=0.1, max_output_tokens=800
                        ),
                    )

                    # Parse the response
                    content = vision_response.text.strip()

                    # Clean JSON response
                    if content.startswith("```json"):
                        content = content[7:-3]
                    elif content.startswith("```"):
                        content = content[3:-3]

                    import json

                    vision_analysis = json.loads(content)

                    # Add metadata
                    vision_analysis["media_url"] = media_url
                    vision_analysis["analyzed_with"] = "gemini-vision"

                    logger.info(
                        f"✅ Vision analysis complete: {vision_analysis.get('content_type', 'unknown')}"
                    )

                    return vision_analysis

                except Exception as e:
                    logger.error(f"⚠️ Vision analysis failed for {media_url}: {e}")
                    # Return basic analysis as fallback
                    return {
                        "media_url": media_url,
                        "content_type": "image",
                        "description": "Vision analysis unavailable",
                        "key_elements": [],
                        "educational_value": "unknown",
                        "extracted_text": "",
                        "analyzed_with": "basic",
                    }

        # No vision service available
        return {
            "media_url": media_url,
            "content_type": "image",
            "description": "No vision AI service available",
            "key_elements": [],
            "educational_value": "unknown",
            "extracted_text": "",
            "analyzed_with": "none",
        }

    def _calculate_intelligent_value_score(
        self, analysis: Dict, post: SocialPost
    ) -> float:
        """Calculate sophisticated value score based on multiple factors with wider distribution"""

        # Safety check - ensure analysis is a dict
        if not isinstance(analysis, dict):
            logger.warning(
                f"⚠️ _calculate_intelligent_value_score received non-dict: {type(analysis)}"
            )
            return 0.0

        score = 3.0  # Lower base score for more contrast

        # Content quality indicators (0-3 points)
        if isinstance(analysis.get("quality_indicators"), list):
            quality_count = len(analysis["quality_indicators"])
            score += min(quality_count * 0.6, 3.0)  # Increased weight

        # Actionable content bonus (0-2 points)
        if isinstance(analysis.get("actionable_items"), list):
            actionable_count = len(analysis["actionable_items"])
            score += min(actionable_count * 0.4, 2.0)  # Increased weight

        # Learning value bonus (0-2 points)
        learning_value = analysis.get("learning_value")
        if learning_value and isinstance(learning_value, str):
            if len(learning_value) > 50:
                score += 2.0
            else:
                score += 1.0

        # Engagement quality with exponential scaling (0-2 points)
        if isinstance(post.engagement, dict):
            likes = (
                post.engagement.get("likes", 0)
                or post.engagement.get("score", 0)
                or post.engagement.get("favorite_count", 0)
            )
            comments = (
                post.engagement.get("comments", 0)
                or post.engagement.get("replies", 0)
                or post.engagement.get("num_comments", 0)
            )

            # Exponential scaling for viral content
            if likes > 1000 or comments > 100:
                score += 2.0  # Viral
            elif likes > 500 or comments > 50:
                score += 1.5  # High engagement
            elif likes > 100 or comments > 20:
                score += 1.0  # Good engagement
            elif likes > 20 or comments > 5:
                score += 0.5  # Medium engagement

        # Platform-specific adjustments (0-1 points)
        if post.platform == "reddit":
            # Reddit discussions often have high value
            score += 0.5
        elif post.platform == "twitter":
            # Twitter threads can be valuable
            if post.post_type == "thread":
                score += 1.0  # Threads are high value

        # Content complexity and depth (0-1.5 points)
        if "complexity_level" in analysis:
            complexity = analysis["complexity_level"]
            if complexity == "Expert":
                score += 1.5
            elif complexity == "Advanced":
                score += 1.0
            elif complexity == "Intermediate":
                score += 0.5

        # Practical applications bonus (0-1.5 points)
        if "practical_applications" in analysis:
            app_count = len(analysis["practical_applications"])
            score += min(app_count * 0.5, 1.5)

        # Penalize low quality (can go below base)
        if (
            "quality_indicators" in analysis
            and len(analysis["quality_indicators"]) == 0
        ):
            score -= 1.0

        # Cap the score at 10 and floor at 1
        return max(1.0, min(score, 10.0))

    def _calculate_content_quality_score(
        self, analysis: Dict, post: SocialPost
    ) -> float:
        """
        Calculate content quality score for social media reposting (0-10 scale)

        Optimized for content that works well on social media:
        - Clarity and readability
        - Engagement potential
        - Information value
        - Shareability factors
        """

        # Safety check - ensure inputs are correct types
        if not isinstance(analysis, dict):
            logger.warning(
                f"⚠️ _calculate_content_quality_score received non-dict: {type(analysis)}"
            )
            return 0.0

        if not post.content or not isinstance(post.content, str):
            return 0.0

        quality_score = 0.0
        content = post.content.lower()
        original_content = post.content

        # Base content value (0-3 points)
        content_length = len(original_content)
        if 50 <= content_length <= 280:  # Twitter-optimal length
            quality_score += 3.0
        elif 280 < content_length <= 500:  # Good for LinkedIn/Facebook
            quality_score += 2.5
        elif content_length > 500:  # Long-form content
            quality_score += 2.0
        elif content_length < 50:  # Too short
            quality_score += 0.5

        # Engagement indicators (0-2 points)
        engagement_words = [
            "tip",
            "hack",
            "secret",
            "amazing",
            "incredible",
            "must-know",
            "game-changer",
            "breakthrough",
            "revolutionary",
            "insider",
        ]
        engagement_count = sum(1 for word in engagement_words if word in content)
        quality_score += min(engagement_count * 0.5, 2.0)

        # Technical value (0-2 points)
        tech_value_terms = [
            "ai",
            "ml",
            "python",
            "javascript",
            "react",
            "api",
            "database",
            "algorithm",
            "framework",
            "tool",
            "software",
            "code",
            "dev",
        ]
        tech_count = sum(1 for term in tech_value_terms if term in content)
        quality_score += min(tech_count * 0.3, 2.0)

        # Structure and readability (0-1.5 points)
        if any(
            indicator in content
            for indicator in ["1.", "2.", "3.", "•", "-", "first", "second"]
        ):
            quality_score += 1.0
        if "\n" in original_content:  # Has line breaks
            quality_score += 0.5

        # Social media friendly elements (0-1.5 points)
        if any(indicator in content for indicator in ["#", "@", "http", "link"]):
            quality_score += 0.5
        if any(indicator in content for indicator in ["?", "!", "what", "how", "why"]):
            quality_score += 0.5  # Questions/exclamations engage better
        if any(
            emoji_indicator in original_content
            for emoji_indicator in ["🚀", "💡", "🔥", "✨", "⚡"]
        ):
            quality_score += 0.5

        # Actual engagement metrics (0-1 point)
        if hasattr(post, "engagement") and post.engagement:
            # Ensure engagement is a dict, not a string
            if isinstance(post.engagement, dict):
                likes = (
                    post.engagement.get("likes", 0)
                    or post.engagement.get("score", 0)
                    or post.engagement.get("favorite_count", 0)
                )
                comments = (
                    post.engagement.get("replies", 0)
                    or post.engagement.get("num_comments", 0)
                    or post.engagement.get("reply_count", 0)
                )

                if likes > 100 or comments > 20:
                    quality_score += 1.0
                elif likes > 20 or comments > 5:
                    quality_score += 0.5

        return min(quality_score, 10.0)

    def _determine_rewrite_candidate(
        self, analysis: Dict, post: SocialPost, quality_score: float
    ) -> bool:
        """
        Determine if content is a good candidate for rewriting and reposting to social media

        A post is a rewrite candidate if:
        - It has good information but poor social media presentation
        - It's too long for optimal social media engagement
        - It lacks engaging elements but has valuable content
        - It has potential but needs optimization for social platforms
        """

        # Safety check - ensure inputs are correct types
        if not isinstance(analysis, dict):
            return False

        if not post.content or not isinstance(post.content, str):
            return False

        if not isinstance(quality_score, (int, float)):
            quality_score = 0.0

        content = post.content
        content_lower = content.lower()
        content_length = len(content)

        # High-quality content that's too long for social media
        if quality_score >= 6.0 and content_length > 500:
            return True

        # Good technical content but lacks social media engagement elements
        tech_terms = [
            "ai",
            "ml",
            "python",
            "javascript",
            "react",
            "api",
            "database",
            "algorithm",
            "framework",
            "tool",
            "software",
            "code",
            "dev",
        ]
        has_tech_content = sum(1 for term in tech_terms if term in content_lower) >= 2

        engagement_elements = ["#", "@", "?", "!", "🚀", "💡", "🔥", "✨", "⚡"]
        has_engagement_elements = any(
            element in content for element in engagement_elements
        )

        if has_tech_content and not has_engagement_elements and quality_score >= 4.0:
            return True

        # Content with good structure but could be more engaging
        has_structure = any(
            indicator in content_lower
            for indicator in ["1.", "2.", "3.", "•", "-", "first", "second"]
        )
        engagement_words = [
            "tip",
            "hack",
            "secret",
            "amazing",
            "incredible",
            "must-know",
            "game-changer",
            "breakthrough",
            "revolutionary",
            "insider",
        ]
        has_engagement_words = any(word in content_lower for word in engagement_words)

        if has_structure and not has_engagement_words and quality_score >= 5.0:
            return True

        # Long posts with good content but poor social media optimization
        if content_length > 800 and quality_score >= 5.0:
            return True

        # Posts with valuable information but suboptimal length for social media
        if content_length < 50 and quality_score >= 6.0:  # Too short but high quality
            return True

        # Posts with good engagement potential but missing key elements
        if quality_score >= 7.0 and not has_engagement_elements:
            return True

        # Check for posts that performed well but could be optimized further
        if hasattr(post, "engagement") and post.engagement:
            likes = (
                post.engagement.get("likes", 0)
                or post.engagement.get("score", 0)
                or post.engagement.get("favorite_count", 0)
            )
            comments = (
                post.engagement.get("replies", 0)
                or post.engagement.get("num_comments", 0)
                or post.engagement.get("reply_count", 0)
            )

            # Good engagement but could be better with optimization
            if (
                (likes > 50 or comments > 10)
                and quality_score >= 6.0
                and not has_engagement_elements
            ):
                return True

        return False

    def _generate_actionable_insights(
        self, analysis: Dict, post: SocialPost
    ) -> List[str]:
        """Generate specific actionable insights from the analysis"""

        insights = []

        # Extract from analysis
        if "actionable_items" in analysis:
            insights.extend(analysis["actionable_items"])

        # Add platform-specific insights
        if post.platform == "reddit":
            insights.append(
                f"Explore discussion thread for community insights: {post.url}"
            )

        if "follow_up_research" in analysis:
            for research in analysis["follow_up_research"]:
                insights.append(f"Research: {research}")

        return insights[:5]  # Return top 5 insights

    def _generate_learning_recommendations(
        self, analysis: Dict, post: SocialPost
    ) -> Dict[str, Any]:
        """Generate personalized learning recommendations"""

        return {
            "next_steps": analysis.get("follow_up_research", []),
            "related_skills": analysis.get("related_skills", []),
            "difficulty_level": analysis.get("complexity_level", "Unknown"),
            "estimated_time": analysis.get("time_to_consume", "Unknown"),
            "prerequisites": [],
            "learning_path": [],
        }

    def _basic_analysis(
        self, post: SocialPost, sentiment_scores: Dict
    ) -> Dict[str, Any]:
        """Fallback basic analysis when AI services are unavailable"""

        # Mark as fallback analysis
        analysis = {
            "analysis_version": "fallback",
            "ai_analysis_succeeded": False,
            "ai_service_used": None,
        }

        # NEW: Basic rewrite suggestions when AI is not available (simplified format)
        basic_rewrite_suggestions = [
            {
                "angle": "Extract the core concept and rewrite from a practical perspective",
                "tone": "natural, observational",
                "approach": "Identify the main insight and frame it as a practical observation",
                "confidence": 0.5,
            },
            {
                "angle": "Focus on actionable takeaways from this content",
                "tone": "practical, direct",
                "approach": "Highlight what readers can actually do with this information",
                "confidence": 0.4,
            },
        ]

        # OLD: Keep basic_rewrite_angles for backward compatibility
        basic_rewrite_angles = []

        # Calculate content age
        try:
            created_dt = datetime.fromisoformat(post.created_at.replace("Z", "+00:00"))
            age_hours = (
                datetime.now(created_dt.tzinfo) - created_dt
            ).total_seconds() / 3600
            if age_hours < 24:
                publication_age = f"{int(age_hours)} hours"
            elif age_hours < 168:  # 7 days
                publication_age = f"{int(age_hours/24)} days"
            else:
                publication_age = f"{int(age_hours/168)} weeks"
        except Exception as e:
            logger.error(f"Error: {e}")
            publication_age = "unknown"

        # Compute better discovery signals even in basic mode
        likes = 0
        comments = 0
        if post.engagement:
            likes = (
                post.engagement.get("likes", 0)
                or post.engagement.get("score", 0)
                or post.engagement.get("favorite_count", 0)
            )
            comments = (
                post.engagement.get("comments", 0)
                or post.engagement.get("replies", 0)
                or post.engagement.get("num_comments", 0)
            )

        # Author authority based on engagement
        if likes > 1000 or comments > 100:
            author_authority = "high"
        elif likes > 100 or comments > 20:
            author_authority = "medium"
        else:
            author_authority = "low"

        # Trend relevance based on keywords
        content_lower = post.content.lower() if post.content else ""
        emerging_keywords = [
            "gpt-5",
            "gpt5",
            "claude",
            "gemini",
            "new release",
            "just launched",
            "breaking",
            "announced",
            "alpha",
            "beta",
        ]
        declining_keywords = [
            "deprecated",
            "legacy",
            "old version",
            "no longer",
            "sunset",
        ]

        if any(kw in content_lower for kw in emerging_keywords):
            trend_relevance = "emerging"
        elif any(kw in content_lower for kw in declining_keywords):
            trend_relevance = "declining"
        else:
            trend_relevance = "mainstream"

        # Discussion quality based on comments
        if comments > 50:
            discussion_quality = "high"
        elif comments > 10:
            discussion_quality = "medium"
        else:
            discussion_quality = "low"

        # Viral potential calculation
        engagement_score = (likes * 0.6 + comments * 1.5) / 10  # Scale to 0-100
        viral_potential = min(100, int(engagement_score))

        # Unique perspective detection
        unique_indicators = [
            "new approach",
            "novel",
            "first",
            "discovered",
            "invented",
            "created",
            "built",
            "data shows",
            "research",
        ]
        unique_perspective = (
            "yes" if any(ind in content_lower for ind in unique_indicators) else "no"
        )

        # Infer category from content keywords (can fit multiple categories)
        category = "OTHER"
        fit_categories = []

        if any(
            kw in content_lower
            for kw in [
                "ai",
                "code",
                "programming",
                "software",
                "tech",
                "developer",
                "engineering",
                "algorithm",
                "api",
                "framework",
            ]
        ):
            category = "TECH"
            fit_categories.append("TECH")
        if any(
            kw in content_lower
            for kw in [
                "crypto",
                "bitcoin",
                "blockchain",
                "defi",
                "nft",
                "ethereum",
                "web3",
                "token",
            ]
        ):
            if category == "OTHER":
                category = "CRYPTO"
            fit_categories.append("CRYPTO")
        if any(
            kw in content_lower
            for kw in [
                "dating",
                "relationship",
                "romance",
                "love",
                "partner",
                "single",
                "marriage",
            ]
        ):
            if category == "OTHER":
                category = "DATING"
            fit_categories.append("DATING")
        if any(
            kw in content_lower
            for kw in [
                "startup",
                "business",
                "entrepreneur",
                "marketing",
                "finance",
                "invest",
                "revenue",
            ]
        ):
            if category == "OTHER":
                category = "BUSINESS"
            fit_categories.append("BUSINESS")
        if any(
            kw in content_lower
            for kw in [
                "learn",
                "tutorial",
                "how to",
                "guide",
                "education",
                "course",
                "study",
            ]
        ):
            if category == "OTHER":
                category = "LEARNING"
            fit_categories.append("LEARNING")
        if any(
            kw in content_lower
            for kw in ["news", "breaking", "announced", "reported", "politics", "world"]
        ):
            if category == "OTHER":
                category = "NEWS"
            fit_categories.append("NEWS")
        if any(
            kw in content_lower
            for kw in [
                "health",
                "fitness",
                "nutrition",
                "wellness",
                "medical",
                "diet",
                "exercise",
            ]
        ):
            if category == "OTHER":
                category = "HEALTH"
            fit_categories.append("HEALTH")
        if any(
            kw in content_lower
            for kw in [
                "movie",
                "music",
                "game",
                "entertainment",
                "fun",
                "meme",
                "comedy",
            ]
        ):
            if category == "OTHER":
                category = "ENTERTAINMENT"
            fit_categories.append("ENTERTAINMENT")
        if any(
            kw in content_lower
            for kw in ["personal", "life", "story", "experience", "myself", "journey"]
        ):
            if category == "OTHER":
                category = "PERSONAL"
            fit_categories.append("PERSONAL")

        # If no categories found, use OTHER
        if not fit_categories:
            fit_categories = ["OTHER"]

        # Map category to persona (for the 3 main personas)
        # FIXED: Removed DATING -> aspandead mapping (dating advice != deep personal growth)
        category_to_persona = {
            "TECH": "qronoya",
            "CRYPTO": "claimzilla",
            "BUSINESS": "qronoya",  # Business content goes to tech persona
            "LEARNING": "qronoya",  # Learning content goes to tech persona
            "PRODUCTIVITY": "qronoya",  # Productivity content goes to tech persona
        }

        # Determine best_persona_key from fit_categories (priority: CRYPTO > TECH > PERSONAL)
        # FIXED: DATING content should NOT go to aspandead (deep philosophical writer)
        # aspandead is for deep personal growth, not dating advice
        best_persona_key = None
        if "CRYPTO" in fit_categories:
            best_persona_key = "claimzilla"
        elif any(
            cat in ["TECH", "BUSINESS", "LEARNING", "PRODUCTIVITY"]
            for cat in fit_categories
        ):
            best_persona_key = "qronoya"
        elif "DATING" in fit_categories or "PERSONAL" in fit_categories:
            # Dating/personal content: use qronoya (practical) or leave unassigned
            # Don't force it to aspandead unless it's clearly about deep personal growth
            best_persona_key = None  # Let persona matcher decide based on content
        else:
            # Try primary category
            best_persona_key = category_to_persona.get(category)

        # NEW: Calculate basic profile_matches from category (low confidence for basic analysis)
        profile_matches = {}
        try:
            matcher = get_persona_matcher()
            all_profile_keys = list(matcher.persona_profiles.keys())
            # For basic analysis, assign low scores based on category
            for pid in all_profile_keys:
                profile_matches[pid] = 0.0

            # Set minimal scores based on category
            if best_persona_key:
                profile_matches[best_persona_key] = 30.0  # Low confidence (30/100)
        except Exception as e:
            logger.error(f"Error: {e}")
            # Fallback: empty profile_matches
            profile_matches = {}

        # Merge with base analysis dict (created at start of function)
        analysis.update(
            {
                "category": category,
                "fit_categories": fit_categories,
                "best_persona_key": best_persona_key,
                "best_persona_score": 5.0
                if best_persona_key
                else 0.0,  # Lower confidence for basic analysis
                "best_persona_reasons": [
                    f"Inferred from categories: {', '.join(fit_categories)}"
                ]
                if best_persona_key
                else [],
                "subcategory": post.platform.title(),
                "content_type": post.post_type,
                "topics": post.hashtags[:3] if post.hashtags else ["general"],
                "key_concepts": [],
                "summary": post.content[:200] + "..."
                if len(post.content) > 200
                else post.content,
                "ai_summary": post.content[:200] + "..."
                if len(post.content) > 200
                else post.content,
                "why_valuable": "User bookmarked this content",
                "sentiment": "Neutral",
                "complexity_level": "Unknown",
                "time_to_consume": "Unknown",
                "actionable_items": [],
                "learning_value": "Content analysis not available",
                "practical_applications": [],
                "related_skills": [],
                "follow_up_research": [],
                "quality_indicators": [],
                "tags": post.hashtags[:5] if post.hashtags else [],
                "confidence_score": 0.3,
                "sentiment_scores": sentiment_scores,
                "ai_service": "basic",
                "analysis_model": "basic",
                "rewrite_angles": basic_rewrite_angles,  # OLD: Keep for backward compatibility
                "rewrite_suggestions": basic_rewrite_suggestions,  # NEW: Simplified rewrite suggestions
                "profile_matches": profile_matches,  # NEW: Dynamic profile matching
                "discovery_signals": {
                    "author_authority": author_authority,
                    "trend_relevance": trend_relevance,
                    "viral_potential": viral_potential,
                    "discussion_quality": discussion_quality,
                    "unique_perspective": unique_perspective,
                },
                "content_freshness": {
                    "publication_age": publication_age,
                    "still_relevant": "yes",
                    "time_sensitivity": "evergreen",
                },
            }
        )

        return analysis


# Example usage and testing
if __name__ == "__main__":
    analyzer = IntelligentContentAnalyzer()
    logger.info("🧠 Intelligent Content Analyzer ready!")
