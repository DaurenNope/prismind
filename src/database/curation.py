#!/usr/bin/env python3
"""
Database Curation Module

Handles automatic curation of posts to usable_posts table based on quality and usability criteria.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

import ast
import asyncio
import json
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class DatabaseCuration:
    """Handles automatic post curation to usable_posts"""

    def __init__(self, supabase=None):
        self._supabase = supabase

    def _check_content_quality_for_curation(
        self, post: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if content is complete, not truncated, and properly collected.
        More comprehensive than _check_data_quality - this is for curation to usable_posts.
        Same logic as in curate_usable_posts.py
        """
        content = post.get("content", "") or ""
        ai_summary = post.get("ai_summary", "") or ""
        title = post.get("title", "") or ""

        # 1. Check for empty content
        if not content or len(content.strip()) < 50:
            return False, "Content is empty or too short (<50 chars)"

        content_lower = content.lower()
        content_stripped = content.strip()

        # 2. Check for scraping errors and error pages
        error_page_patterns = [
            "javascript is not available",
            "we've detected that javascript",
            "please enable javascript",
            "switch to a supported browser",
            "something went wrong",
            "don't fret",
            "try again",
            "privacy related extensions",
            "disable them and try again",
            "x.com links like help center",
            "terms of service",
            "privacy policy",
            "ads info",
            "© 2025 x corp",
            "error loading",
            "failed to load",
            "content not available",
            "scraping failed",
            "extraction failed",
            "could not extract",
            "error extracting",
            "failed to scrape",
            "page not found",
            "404",
            "403 forbidden",
            "access denied",
            "rate limited",
            "too many requests",
        ]

        content_start = content_lower[:500]
        error_count = sum(
            1 for pattern in error_page_patterns if pattern in content_lower
        )

        if any(pattern in content_start for pattern in error_page_patterns):
            if error_count >= 2:
                return False, "Content appears to be an error page or scraping failure"
            if len(content) < 300 and error_count >= 1:
                return (
                    False,
                    "Content appears to be an error page (short content with error pattern)",
                )

        # 3. Check for placeholder/error content
        placeholder_patterns = [
            "placeholder",
            "undefined",
            "null",
            "[deleted]",
            "[removed]",
            "this content is not available",
            "content unavailable",
            "unavailable",
        ]

        if any(pattern in content_lower for pattern in placeholder_patterns):
            return False, "Content appears to be placeholder or error message"

        # 4. Check for truncated content
        truncation_end_patterns = [
            content_stripped.endswith("..."),
            content_stripped.endswith("…"),
            content_stripped.endswith("[truncated]"),
            content_stripped.endswith("[...]"),
        ]
        truncation_in_last_chars = (
            "..." in content_stripped[-30:]
            or "…" in content_stripped[-30:]
            or "[truncated]" in content_stripped[-30:]
            or "[...]" in content_stripped[-30:]
        )

        if any(truncation_end_patterns) or truncation_in_last_chars:
            return False, "Content is truncated (ends with truncation marker)"

        # 5. Check for mid-sentence/mid-word endings
        if len(content) >= 100:
            last_char = content_stripped[-1] if content_stripped else ""
            last_50_chars = content_stripped[-50:]
            last_words = last_50_chars.split()

            proper_endings = ".!?\")'」"
            if last_char not in proper_endings and not truncation_in_last_chars:
                if last_words:
                    last_word = last_words[-1]
                    if len(last_word) > 20:
                        return (
                            False,
                            "Content appears truncated (ends with very long word)",
                        )
                    if len(last_word) > 10:
                        last_part = last_word[-5:].lower()
                        if len(last_part) >= 5 and not any(
                            v in last_part for v in "aeiou"
                        ):
                            return (
                                False,
                                "Content appears truncated (ends with incomplete word)",
                            )

                if 200 <= len(content) <= 800:
                    sentences = re.split(r"[.!?]", content_stripped)
                    if sentences:
                        last_sentence = sentences[-1].strip()
                        if len(last_sentence) < 20 and last_char not in proper_endings:
                            return (
                                False,
                                "Content appears truncated (ends with incomplete sentence)",
                            )

        # 6. Check for HTML/technical content
        html_patterns = [
            "<script",
            "<style",
            "<div",
            "<span",
            "href=",
            "src=",
            "class=",
            "id=",
            "javascript:",
        ]
        html_count = sum(1 for pattern in html_patterns if pattern in content_lower)
        if html_count >= 3:
            return False, "Content appears to contain HTML/scraping artifacts"

        # 7. Check for suspiciously short content
        if len(content) < 100:
            if content_stripped and content_stripped[-1] not in ".!?\")'」":
                return (
                    False,
                    "Content is too short and doesn't end properly (likely truncated)",
                )

        # 8. Require an AI summary to exist (length no longer enforced)
        clean_summary = ai_summary.strip()
        if not clean_summary:
            clean_summary = ""
        summary_lower = clean_summary.lower()
        error_summary_patterns = [
            "javascript error",
            "error preventing access",
            "browser error",
            "page error",
            "loading error",
            "scraping error",
            "extraction error",
        ]

        summary_has_error = any(
            pattern in summary_lower for pattern in error_summary_patterns
        )
        if summary_has_error and error_count >= 1:
            return False, "Content and AI summary indicate error page/scraping failure"

        # 9. Check title quality
        if title:
            if len(title) > 500:
                return False, "Title is too long (might be content, not title)"

        # 10. Final check: Content should look like actual post content
        words = content_stripped.split()
        if len(words) < 10 and len(content) > 200:
            return (
                False,
                "Content has too few words for its length (likely garbage data)",
            )

        return True, None

    def _check_time_sensitive_keywords(self, content: str, ai_summary: str) -> bool:
        """Check if content contains time-sensitive keywords"""
        text = (content + " " + ai_summary).lower()

        high_confidence_patterns = [
            r"\bbreaking\b",
            r"\bbreaking news\b",
            r"\bjust in\b",
            r"\bdeveloping\b",
            r"\breleased this week\b",
            r"\bjust released\b",
            r"\bjust announced\b",
            r"\bannounced today\b",
            r"\blaunched today\b",
            r"\byesterday\b",
            r"\btoday\b",
            r"\btomorrow\b",
            r"\bthis morning\b",
            r"\bthis afternoon\b",
            r"\bthis evening\b",
            r"\bhours ago\b",
            r"\bdays ago\b",
            r"\bweeks ago\b",
            r"\bjust now\b",
            r"\burgent\b",
            r"\basap\b",
            r"\bimmediate\b",
            r"\bright now\b",
            r"\bcurrently\b",
            r"\bhappening now\b",
            r"\belection\b",
            r"\bvote\b",
            r"\bpoll\b",
            r"\bresults\b",
            r"\boutcome\b",
            r"\bdecision\b",
            r"\bverdict\b",
            r"\btrial\b",
            r"\bcourt\b",
            r"\bhearing\b",
            r"\blaunch\b.*\btoday\b",
            r"\brelease\b.*\btoday\b",
            r"\bunveiled\b.*\btoday\b",
            r"\bdebuted\b.*\btoday\b",
            r"\bintroduced\b.*\btoday\b",
            r"\bpremiered\b.*\btoday\b",
            r"\bmarket opens\b",
            r"\btrading\b.*\bnow\b",
            r"\bprice\b.*\b(crash|surge|rally)\b",
        ]

        for pattern in high_confidence_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True

        medium_confidence_patterns = [
            r"\bthis week\b",
            r"\bthis month\b",
            r"\brecently\b",
            r"\blastest\b",
        ]

        medium_count = sum(
            1
            for pattern in medium_confidence_patterns
            if re.search(pattern, text, re.IGNORECASE)
        )

        if medium_count >= 2:
            return True

        return False

    def _is_post_usable(self, post: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Check if post meets criteria for usable_posts.
        RELAXED CRITERIA: If post has analysis and passes quality checks, include it.
        """
        # Exclude DEPRECATED posts
        category = (post.get("category") or "").upper()
        if category == "DEPRECATED":
            return False, None

        # TIGHTENED CRITERIA: Require minimum quality thresholds
        rewrite_score = float(post.get("rewrite_score") or 0.0)
        value_score = float(post.get("value_score") or 0.0)
        quality_score = float(post.get("quality_score") or 0.0)

        # Require at least one solid score; allow slightly lower rewrite if value/quality are high
        if max(rewrite_score, value_score, quality_score) < 4.0:
            return False, None

        # Must have some summary text (length already enforced upstream)
        ai_summary = (post.get("ai_summary") or "").strip()
        if not ai_summary:
            return False, None

        # Require analysis confidence to be reasonable (but allow fallback summaries)
        analysis_confidence = float(post.get("analysis_confidence") or 0.0)
        if analysis_confidence < 0.3:
            return False, None

        # TIGHTENED: Require persona fit validation - at least one persona with score >= 30 (0-100 format)
        # NEW: Use profile_matches (0-100 format) - dynamic, works with any profiles
        profile_matches = post.get("profile_matches", {})
        if isinstance(profile_matches, str):
            try:
                profile_matches = json.loads(profile_matches)
            except Exception as e:
                logger.error(f"Error: {e}")
                profile_matches = {}

        # Check profile_matches first (new, dynamic format)
        if isinstance(profile_matches, dict) and profile_matches:
            max_profile_score = (
                max(
                    float(v)
                    for v in profile_matches.values()
                    if isinstance(v, (int, float))
                )
                if profile_matches
                else 0.0
            )
            if max_profile_score < 30.0:  # 30/100 threshold (equivalent to 3.0/10)
                # No profile matches well enough
                return False, None
        else:
            # Fallback: Check old persona_fit_scores (0-10 format) for backward compatibility
            persona_fit_scores = post.get("persona_fit_scores", {})
            if isinstance(persona_fit_scores, str):
                try:
                    persona_fit_scores = json.loads(persona_fit_scores)
                except Exception as e:
                    logger.error(f"Error: {e}")
                    persona_fit_scores = {}

            if isinstance(persona_fit_scores, dict) and persona_fit_scores:
                max_persona_score = (
                    max(
                        float(v)
                        for v in persona_fit_scores.values()
                        if isinstance(v, (int, float))
                    )
                    if persona_fit_scores
                    else 0.0
                )
                if max_persona_score < 3.0:  # 3.0/10 threshold
                    return False, None
            else:
                # Final fallback: check best_persona_score
                best_persona_score = float(post.get("best_persona_score") or 0.0)
                if best_persona_score < 3.0:
                    return False, None

        # Analysis model is optional - if present, check it's valid, but don't require it
        analysis_model = post.get("analysis_model")
        if analysis_model and analysis_model not in (
            "gemini",
            "mistral",
            "ollama",
            "qwen",
            "qwen2.5:1.5b",
            "qwen2.5:7b",
        ):
            # Invalid model name - but don't exclude, just log
            logger.debug(
                f"Post {post.get('post_id')} has invalid analysis_model: {analysis_model}"
            )

        relevance_window = (post.get("relevance_window") or "evergreen").strip().lower()
        if relevance_window in ("", "unknown", "none"):
            relevance_window = "evergreen"
        urgency_score = float(post.get("urgency_score") or 0.0)
        time_sensitive = bool(post.get("time_sensitive", False))
        created_at = post.get("created_at")

        # Check if commentary_worthy (manual override) - always include
        commentary_worthy = bool(post.get("commentary_worthy", False))
        if commentary_worthy:
            return True, "commentary_worthy"

        # Check age
        age_info = None
        if created_at:
            try:
                if isinstance(created_at, str):
                    if "T" in created_at:
                        created_dt = datetime.fromisoformat(
                            created_at.replace("Z", "+00:00")
                        )
                    else:
                        created_dt = datetime.fromisoformat(created_at)
                elif isinstance(created_at, datetime):
                    created_dt = created_at
                else:
                    created_dt = None

                if created_dt:
                    now = datetime.now(timezone.utc)
                    if created_dt.tzinfo:
                        now_dt = now if now.tzinfo else datetime.now(created_dt.tzinfo)
                    else:
                        now_dt = datetime.now(timezone.utc)
                        created_dt = created_dt.replace(tzinfo=timezone.utc)

                    age_days = (now_dt - created_dt).days
                    age_months = age_days / 30.0

                    age_info = {"days": age_days, "months": age_months}
            except Exception as e:
                logger.error(f"Error: {e}")
                pass

        # Normalize evergreen/time-sensitive behavior
        TIME_SENSITIVE_WINDOWS = ("same-day", "24-72h", "this-week")
        MONTHLY_WINDOWS = ("this-month",)

        # If a time-sensitive post aged out, automatically treat it as evergreen
        if (
            relevance_window in TIME_SENSITIVE_WINDOWS + MONTHLY_WINDOWS
            and age_info
            and age_info["days"] > 7
        ):
            relevance_window = "evergreen"
            post["relevance_window"] = "evergreen"
            post["time_sensitive"] = False
            post["urgency_score"] = 0.0

        # Evergreen posts are now always allowed (historical backlog)
        if relevance_window == "evergreen":
            post["time_sensitive"] = False
            post["urgency_score"] = 0.0
            return True, "evergreen"

        # Apply stricter limits for non-evergreen posts
        if relevance_window in TIME_SENSITIVE_WINDOWS:
            if age_info:
                if age_info["days"] <= 7:
                    return True, "fresh_time_sensitive"
                # aged out time-sensitive post already converted above, so treat as evergreen fallback
                return True, "evergreen_converted"
            return True, "fresh_time_sensitive"

        if relevance_window in MONTHLY_WINDOWS:
            if age_info and age_info["days"] > 30:
                return True, "evergreen_converted"
            return True, "time_sensitive_month"

        # Unknown window - enforce a softer global limit (1 year)
        if age_info and age_info["days"] > 365:
            return False, "Post too old (>365 days, unknown relevance_window)"

        return True, "unknown_relevance_window"

    def _parse_array_field(self, value: Any) -> Optional[List[str]]:
        """Parse array field from various formats to Python list or None"""
        if value is None:
            return None
        if isinstance(value, list):
            return value if value else None
        if isinstance(value, str):
            if not value or value.strip() == "" or value == "[]":
                return None
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return parsed if parsed else None
                if isinstance(parsed, dict):
                    return None
            except Exception as e:
                logger.error(f"Error: {e}")
                stripped = value.strip()
                if stripped.startswith("{") and stripped.endswith("}"):
                    try:
                        normalized = stripped.replace("{", "[").replace("}", "]")
                        parsed = ast.literal_eval(normalized)
                        if isinstance(parsed, list):
                            return [
                                str(item).strip()
                                for item in parsed
                                if str(item).strip()
                            ]
                    except Exception:
                        pass
                if "," in value:
                    return [
                        v.strip().strip('"').strip("'")
                        for v in value.strip("{}").split(",")
                        if v.strip()
                    ]
                return None
        return None

    def auto_curate_to_usable_posts(self, post: Dict[str, Any]) -> bool:
        """
        Automatically curate post to usable_posts table if it meets criteria.
        Called after post is saved and has analysis.

        Returns:
            True if post was added/updated in usable_posts, False otherwise
        """
        if not self._supabase:
            return False

        try:
            # 1. Check content quality
            content_valid, content_error = self._check_content_quality_for_curation(
                post
            )
            if not content_valid:
                logger.info(
                    f"❌ Curation quality gate failed for {post.get('post_id')} ({post.get('platform')}): {content_error}"
                )
                # Remove from usable_posts if it was there before (quality degraded)
                self._remove_from_usable_posts(
                    post.get("post_id"), post.get("platform")
                )
                return False

            # 2. Check if post is usable
            is_usable, inclusion_reason = self._is_post_usable(post)
            if not is_usable:
                logger.info(
                    f"⚠️ Curation usability gate failed for {post.get('post_id')} ({post.get('platform')}): {inclusion_reason or 'no matching persona/score'}"
                )
                # Remove from usable_posts if it was there before (no longer usable)
                self._remove_from_usable_posts(
                    post.get("post_id"), post.get("platform")
                )
                return False

            # 3. Post is usable - insert/update in usable_posts
            try:
                # Parse JSON fields (OLD - keep for backward compatibility)
                persona_fit_scores = post.get("persona_fit_scores")
                if isinstance(persona_fit_scores, str):
                    try:
                        persona_fit_scores = json.loads(persona_fit_scores)
                    except Exception as e:
                        logger.error(f"Error: {e}")
                        persona_fit_scores = {}

                persona_fit_reasons = post.get("persona_fit_reasons")
                if isinstance(persona_fit_reasons, str):
                    try:
                        persona_fit_reasons = json.loads(persona_fit_reasons)
                    except Exception as e:
                        logger.error(f"Error: {e}")
                        persona_fit_reasons = {}

                # NEW: Parse profile_matches (dynamic, 0-100 format)
                profile_matches = post.get("profile_matches", {})
                if isinstance(profile_matches, str):
                    try:
                        profile_matches = json.loads(profile_matches)
                    except Exception as e:
                        logger.error(f"Error: {e}")
                        profile_matches = {}
                if not isinstance(profile_matches, dict):
                    profile_matches = {}

                # NEW: Parse rewrite_suggestions
                rewrite_suggestions = post.get("rewrite_suggestions", [])
                if isinstance(rewrite_suggestions, str):
                    try:
                        rewrite_suggestions = json.loads(rewrite_suggestions)
                    except Exception as e:
                        logger.error(f"Error: {e}")
                        rewrite_suggestions = []
                if not isinstance(rewrite_suggestions, list):
                    rewrite_suggestions = []

                # Parse array fields
                tags = self._parse_array_field(post.get("tags"))
                key_concepts = self._parse_array_field(post.get("key_concepts"))
                rewrite_reasons = self._parse_array_field(post.get("rewrite_reasons"))
                rewrite_risks = self._parse_array_field(post.get("rewrite_risks"))
                best_persona_reasons = self._parse_array_field(
                    post.get("best_persona_reasons")
                )
                fit_categories = self._parse_array_field(post.get("fit_categories"))

                # Prepare data for insertion
                category_value = (
                    post.get("category")
                    or (fit_categories[0] if fit_categories else None)
                    or post.get("topic")
                    or "general"
                )

                data = {
                    "post_id": post.get("post_id"),
                    "platform": post.get("platform"),
                    "content": post.get("content", ""),
                    "title": post.get("title"),
                    "url": post.get("url", ""),
                    "author": post.get("author"),
                    "author_handle": post.get("author_handle"),
                    "created_at": post.get("created_at"),
                    "ai_summary": post.get("ai_summary"),
                    "category": category_value,
                    "fit_categories": fit_categories,
                    "value_score": float(post.get("value_score", 0)),
                    "quality_score": float(post.get("quality_score", 0)),
                    "rewrite_score": float(post.get("rewrite_score", 0)),
                    "relevance_window": post.get("relevance_window", "evergreen"),
                    "urgency_score": float(post.get("urgency_score", 0))
                    if post.get("urgency_score")
                    else None,
                    "time_sensitive": bool(post.get("time_sensitive", False)),
                    # OLD: Keep for backward compatibility
                    "best_persona_key": post.get("best_persona_key"),
                    "best_persona_score": float(post.get("best_persona_score", 0))
                    if post.get("best_persona_score")
                    else None,
                    "persona_fit_scores": persona_fit_scores,
                    "persona_fit_reasons": persona_fit_reasons,
                    "best_persona_reasons": best_persona_reasons,
                    # NEW: Dynamic profile matching and rewrite suggestions
                    "profile_matches": profile_matches,
                    "rewrite_suggestions": rewrite_suggestions,
                    "tags": tags,
                    "key_concepts": key_concepts,
                    "topic": post.get("topic"),
                    "content_type": post.get("content_type"),
                    "language": post.get("language"),
                    "embedding": post.get("embedding"),
                    "embedding_model": post.get("embedding_model"),
                    "rewrite_readiness": post.get("rewrite_readiness"),
                    "rewrite_reasons": rewrite_reasons,
                    "rewrite_risks": rewrite_risks,
                    "analysis_confidence": float(post.get("analysis_confidence", 0))
                    if post.get("analysis_confidence")
                    else None,
                    "analysis_model": post.get("analysis_model"),
                    "analyzed_at": post.get("analyzed_at"),
                    "inclusion_reason": inclusion_reason,
                    "commentary_worthy": bool(post.get("commentary_worthy", False)),
                }

                # Upsert to usable_posts (on conflict: platform,post_id)
                self._supabase.table("usable_posts").upsert(
                    data, on_conflict="platform,post_id"
                ).execute()

                logger.info(
                    f"✅ Auto-curated post {post.get('post_id')} to usable_posts ({inclusion_reason})"
                )

                # Generate creative rewrite angles in background (fire-and-forget)
                # Only for qronoya persona for now
                try:
                    self._generate_angles_background(post, persona="qronoya")
                except Exception as e:
                    logger.warning(f"Failed to start angle generation: {e}")

                return True

            except Exception as e:
                logger.warning(
                    f"Failed to insert post {post.get('post_id')} into usable_posts: {e}"
                )
                return False

        except Exception as e:
            logger.debug(
                f"Auto-curation check failed for post {post.get('post_id')}: {e}"
            )
            return False

    def _remove_from_usable_posts(
        self, post_id: Optional[str], platform: Optional[str]
    ) -> None:
        """Remove post from usable_posts table if it no longer meets criteria"""
        if not self._supabase or not post_id or not platform:
            return

        try:
            self._supabase.table("usable_posts").delete().eq("post_id", post_id).eq(
                "platform", platform
            ).execute()
            logger.debug(
                f"Removed post {post_id} from usable_posts (no longer meets criteria)"
            )
        except Exception as e:
            logger.debug(f"Failed to remove post {post_id} from usable_posts: {e}")

    async def detect_rewrite_angles_async(
        self, post: Dict[str, Any], persona: str = "qronoya"
    ) -> List[Dict[str, Any]]:
        """
        Use Gemini to generate 2-3 CREATIVE, UNIQUE rewrite angles based on actual content.
        NO hardcoded templates - each angle is generated fresh for this specific post.

        Args:
            post: Post dictionary with content and analysis metadata
            persona: Persona key (default: 'qronoya')

        Returns:
            List of 2-3 creative angles, sorted by confidence (best first)
        """
        content = post.get("content", "")
        ai_summary = post.get("ai_summary", "")
        content_type = post.get("content_type", "general")
        time_sensitivity = post.get("time_sensitivity", "evergreen")
        topics = post.get("topics", []) or []
        key_concepts = post.get("key_concepts", []) or []

        if not content or len(content) < 100:
            logger.debug("Post content too short for angle detection")
            return []

        # Get Gemini API key (use first available)
        gemini_keys = [
            os.getenv("GEMINI_API_KEY"),
            os.getenv("GEMINI_API_KEY_2"),
            os.getenv("GEMINI_API_KEY_3"),
            os.getenv("GEMINI_API_KEY_4"),
        ]
        gemini_key = next((k for k in gemini_keys if k), None)

        if not gemini_key:
            logger.warning("No Gemini API key available for angle detection")
            return []

        gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
        gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/{gemini_model}:generateContent"

        # Build creative prompt - NO templates, just guidance
        prompt = f"""You are analyzing content for creative rewriting. Generate 2-3 UNIQUE rewrite angles for this post.

POST CONTENT:
{content[:1000]}

SUMMARY:
{ai_summary[:500]}

METADATA:
- Content Type: {content_type}
- Time Sensitivity: {time_sensitivity}
- Topics: {', '.join(topics[:5]) if topics else 'N/A'}
- Key Concepts: {', '.join(key_concepts[:5]) if key_concepts else 'N/A'}

PERSONA: {persona} (tech professional, writes in Russian, natural voice)

TASK: Generate 2-3 creative rewrite angles. Each angle should be:
- UNIQUE to this specific content (not generic templates)
- Creative and natural (avoid mechanical openings like "Заметил интересную деталь")
- Match the persona's voice (observational, technical, personal when appropriate)
- Different from each other (variety in approach)

Return JSON array with this structure:
[
  {{
    "angle_name": "Creative angle name",
    "description": "What makes this angle unique for THIS content",
    "tone": "natural tone description",
    "approach": "How to approach rewriting (e.g., 'start with observation about X', 'frame as discovery of Y', 'analyze implications of Z')",
    "confidence": 0.85
  }}
]

IMPORTANT:
- NO hardcoded openings like "Заметил интересную деталь" or "Наткнулся на"
- Each angle should be SPECIFIC to this content
- Be creative - think of unique ways to frame this
- Return 2-3 angles, sorted by confidence (best first)

JSON:"""

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{gemini_url}?key={gemini_key}",
                    json={
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {
                            "temperature": 0.9,  # Higher temp for creativity
                            "maxOutputTokens": 800,
                            "topP": 0.95,
                            "topK": 40,
                        },
                    },
                )

                if response.status_code == 200:
                    result = response.json()
                    text = (
                        result.get("candidates", [{}])[0]
                        .get("content", {})
                        .get("parts", [{}])[0]
                        .get("text", "")
                    )

                    # Parse JSON from response
                    if "```json" in text:
                        text = text.split("```json")[1].split("```")[0].strip()
                    elif "```" in text:
                        text = text.split("```")[1].split("```")[0].strip()

                    try:
                        angles = json.loads(text)
                        if isinstance(angles, list) and len(angles) > 0:
                            # Validate and return
                            validated_angles = []
                            for angle in angles[:3]:  # Max 3
                                if isinstance(angle, dict) and "angle_name" in angle:
                                    validated_angles.append(
                                        {
                                            "angle_name": angle.get("angle_name", ""),
                                            "description": angle.get("description", ""),
                                            "tone": angle.get("tone", "natural"),
                                            "approach": angle.get("approach", ""),
                                            "confidence": float(
                                                angle.get("confidence", 0.7)
                                            ),
                                        }
                                    )

                            if validated_angles:
                                # Sort by confidence
                                validated_angles.sort(
                                    key=lambda x: x["confidence"], reverse=True
                                )
                                logger.info(
                                    f"✅ Generated {len(validated_angles)} creative angles via Gemini"
                                )
                                return validated_angles
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse Gemini angle response: {e}")
                        logger.debug(f"Response text: {text[:200]}")
                else:
                    logger.warning(f"Gemini API error: {response.status_code}")

        except Exception as e:
            logger.warning(f"Failed to generate angles via Gemini: {e}")

        # Fallback: return empty (don't use hardcoded angles)
        return []

    def _generate_angles_background(
        self, post: Dict[str, Any], persona: str = "qronoya"
    ) -> None:
        """
        Fire-and-forget background task to generate angles.
        Doesn't block curation, runs async in background.
        """

        async def _async_generate():
            try:
                angles = await self.detect_rewrite_angles_async(post, persona)
                if angles and self._supabase:
                    post_id = post.get("post_id")
                    platform = post.get("platform")
                    if post_id and platform:
                        # Store angles in database
                        self._supabase.table("posts").update(
                            {
                                "rewrite_angles": {persona: angles},
                                "is_rewrite_candidate": True,
                            }
                        ).eq("post_id", post_id).eq("platform", platform).execute()
                        logger.info(
                            f"✅ Stored {len(angles)} creative angles for post {post_id}"
                        )

                        # AUTOMATICALLY TRIGGER REWRITING after angles are stored
                        try:
                            from src.pipeline.auto_pipeline import AutoPipeline
                            from src.utils.config import get_config

                            config = get_config()
                            # Only auto-rewrite if flag is enabled
                            if config.flags.get("auto_rewrite_after_analysis", True):
                                logger.info(
                                    f"🔄 Auto-triggering rewrite for post {post_id} after angle generation"
                                )

                                # Get full post data with angles
                                full_post = (
                                    self._supabase.table("posts")
                                    .select("*")
                                    .eq("post_id", post_id)
                                    .eq("platform", platform)
                                    .limit(1)
                                    .execute()
                                )
                                if full_post.data:
                                    post_with_angles = full_post.data[0]

                                    # Trigger rewrite via AutoPipeline
                                    auto_pipeline = AutoPipeline()
                                    # Process this specific post for the persona
                                    await auto_pipeline._process_single_post_for_rewrite(
                                        post_with_angles,
                                        profile_key=persona,
                                        schedule=config.flags.get(
                                            "auto_schedule_after_rewrite", False
                                        ),
                                    )
                                    logger.info(
                                        f"✅ Auto-rewrite completed for post {post_id}"
                                    )
                        except Exception as rewrite_error:
                            logger.warning(
                                f"⚠️ Auto-rewrite after angle generation failed: {rewrite_error}"
                            )
                            # Don't fail angle generation if rewrite fails
            except Exception as e:
                logger.warning(f"Background angle generation failed: {e}")

        # Run in background (fire-and-forget)
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            loop.create_task(_async_generate())
        else:
            asyncio.run(_async_generate())
