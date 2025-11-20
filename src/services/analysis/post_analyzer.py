#!/usr/bin/env python3
"""
Post Analysis and Storage Module
Handles AI analysis and database storage of collected posts
"""

import json
import os
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


# Load configuration
def load_collection_config():
    """Load collection configuration from config file"""
    config_path = Path("config/collection.json")
    if config_path.exists():
        with open(config_path, "r") as f:
            return json.load(f)
    return {"performance": {"skip_ai_analysis": False}}


# Analysis imports
from src.core.analysis.intelligent_content_analyzer import IntelligentContentAnalyzer
from src.utils.observability_hub import get_observability_hub, instrument_function

# Optional local media analyzer
try:
    from src.core.analysis.local_media_analyzer import LocalMediaAnalyzer

    _LOCAL_MEDIA_AVAILABLE = True
except Exception as e:
    import logging

    logging.getLogger(__name__).debug(f"Local media analyzer not available: {e}")
    _LOCAL_MEDIA_AVAILABLE = False


# Get logger at module level
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


def log(message: str, level: str = "info"):
    """Helper function for consistent logging"""
    prefix = {"info": "ℹ️", "warning": "⚠️", "error": "❌", "success": "✅"}.get(
        level, "ℹ️"
    )
    logger.info(f"{prefix} {message}")


def detect_content_truncation(content: str) -> bool:
    """
    Detect if content is truncated - including subtle signs like incomplete thoughts.

    Returns True if content appears truncated, False otherwise.
    """
    if not content or len(content.strip()) < 10:
        return False

    content = content.strip()

    # Obvious truncation: ends with ellipsis
    if content.endswith("...") or content.endswith("…"):
        return True

    # Contains "Show more" or "Read more" (shouldn't be in saved content)
    if "show more" in content.lower() or "read more" in content.lower():
        return True

    # Check for incomplete sentence (more careful detection)
    if len(content) > 50:
        last_char = content[-1]
        last_words = content.rstrip().split()[-3:] if content.rstrip().split() else []
        last_phrase = " ".join(last_words).lower() if last_words else ""

        # Definitely truncated: ends with comma
        if content.rstrip().endswith(","):
            return True

        # Definitely truncated: ends with mid-sentence connectors
        mid_sentence_endings = [
            " and",
            " but",
            " for",
            " was",
            " were",
            " that",
            " this",
            " the",
            " will be",
            " would be",
            " could be",
            " should be",
            " text and",
            " silent and",
            " the bitcoin",
            " but for",
        ]
        if any(
            content.rstrip().lower().endswith(ending) for ending in mid_sentence_endings
        ):
            return True

        # Ends with lowercase letter AND it's a connecting word (more conservative)
        if last_char.islower() and last_char.isalpha():
            # Only flag if it ends with common connecting words
            connecting_words = [
                "and",
                "but",
                "for",
                "was",
                "that",
                "the",
                "this",
                "with",
                "from",
            ]
            if last_phrase and any(
                last_phrase.endswith(word) for word in connecting_words
            ):
                return True

        # Ends with dash (might be cut off)
        if content.rstrip().endswith("-") and len(content) > 100:
            return True

        # Ends with colon and is relatively short (might be cut off)
        if content.rstrip().endswith(":") and len(content) < 500:
            return True

    return False


@instrument_function(
    operation_name="analyze_and_store_post",
    track_metrics=True,
    track_errors=True,
    track_trace=True,
)
async def analyze_and_store_post(db_manager, post_dict, supabase_manager=None):
    """
    Analyze post with AI and store with analysis results.

    Args:
        db_manager: Database manager instance
        post_dict: Dictionary containing post data
        supabase_manager: Optional Supabase manager for cloud sync

    Returns:
        bool: True if successfully stored, False otherwise
    """
    hub = get_observability_hub()
    post_id = post_dict.get("post_id", "unknown")
    platform = post_dict.get("platform", "unknown")

    # Track analysis start
    hub.metrics.increment("analyzer.analyze_post.called", labels={"platform": platform})

    # Global cancel check
    try:
        from src.services.cancel_manager import is_cancelled

        if is_cancelled("analysis"):
            log("Analysis cancelled by user", "warning")
            return False
    except Exception as e:
        import logging

        logging.getLogger(__name__).debug(
            f"Cancel manager check failed (non-critical): {e}"
        )
        # Continue - cancel check is optional

    # CRITICAL: Prefer DatabaseAgent for data normalization and quality control
    db_agent = None
    try:
        from src.database.database_agent import DatabaseAgent

        db_agent = DatabaseAgent()
    except Exception as e:
        import logging

        logging.getLogger(__name__).warning(
            f"⚠️ DatabaseAgent initialization failed, using fallback: {e}",
            exc_info=True,
        )
        # Continue with fallback - DatabaseAgent is preferred but not required

    post_id = post_dict.get("post_id", "unknown")
    log(f"Processing post: {post_id}")

    # Load configuration
    config = load_collection_config()
    skip_ai_analysis = config.get("performance", {}).get("skip_ai_analysis", False)

    # Check environment variable as well
    import os

    if os.environ.get("SKIP_AI_ANALYSIS", "").lower() in ("true", "1", "yes"):
        skip_ai_analysis = True

    # Determine if AI analysis should be performed
    if skip_ai_analysis:
        log(f"AI analysis skipped (performance mode)")
        enhanced_post = post_dict
        # Even if we skip analysis, we still want to store the post
        # Use DatabaseAgent if available for normalization
        if db_agent:
            try:
                result = db_agent.save_post(enhanced_post)
                if result:
                    log(
                        f"Stored post via DatabaseAgent successfully (no AI analysis)",
                        "success",
                    )
                    return True
                else:
                    log(f"DatabaseAgent save failed (no AI analysis)", "error")
                    return False
            except Exception as db_agent_error:
                logger.error(f"Error: {db_agent_error}")
                log(
                    f"DatabaseAgent save failed: {db_agent_error}, falling back to legacy",
                    "warning",
                )

        # Fallback: Legacy save path
        try:
            # Try to update first (in case it exists)
            local_updated = db_manager.update_post(post_id, enhanced_post)
            if not local_updated:
                # If update fails, try to add
                local_stored = db_manager.add_post(enhanced_post)
                if not local_stored:
                    log(f"Failed to store post in local database", "error")
                    return False
            log(
                f"Stored post in local database successfully (no AI analysis)",
                "success",
            )
            return True
        except Exception as local_error:
            logger.error(f"Error: {local_error}")
            log(f"Local database operation failed: {local_error}", "error")
            return False
    else:
        # Create analyzer with enhanced configuration
        analyzer = IntelligentContentAnalyzer()

        # Detect truncation before analysis
        content = post_dict.get("content", "") or ""
        is_truncated = detect_content_truncation(content)
        if is_truncated:
            log(f"⚠️ Post appears truncated (incomplete thought detected)", "warning")
            # Mark as potentially truncated for later re-collection
            post_dict["is_potentially_truncated"] = True

        # Prepare content for analysis
        analysis_content = {
            "post_id": post_dict.get("post_id", ""),
            "title": post_dict.get("title", ""),
            "content": post_dict.get("content", ""),
            "url": post_dict.get("url", ""),
            "platform": post_dict.get("platform", ""),
            "author": post_dict.get("author", ""),
            "author_handle": post_dict.get("username", ""),
            "created_at": post_dict.get("created_at", datetime.now().isoformat()),
            "hashtags": post_dict.get("hashtags", []),
            "engagement": post_dict.get("engagement", {}),
            "media_urls": post_dict.get("media_urls", []),
            "post_type": post_dict.get("post_type", "text"),
        }

        # Threads-specific sanitization before analysis (fallback cleanup)
        try:
            if (post_dict.get("platform") == "threads") and post_dict.get("content"):
                raw = str(post_dict.get("content") or "")
                import re

                text = raw
                # Remove 'Translate' artifacts
                text = re.sub(r"\bTranslate\b", " ", text)
                # Remove pagination markers like 1/3, 2 / 5
                text = re.sub(r"\b\d+\s*/\s*\d+\b", " ", text)
                # Remove short time markers like 1d, 2h, 15m
                text = re.sub(r"\b\d+\s*[dhm]\b", " ", text, flags=re.I)
                # Split and filter segments
                segs = re.split(r"[\n\r]+|\s{2,}", text)
                cleaned = []
                seen = set()
                for s in segs:
                    t = s.strip()
                    if not t:
                        continue
                    if len(t) < 6:
                        continue
                    if re.fullmatch(r"@[A-Za-z0-9._-]+", t):
                        continue
                    if re.fullmatch(r"[\w.-]+\.(com|net|org|io|ai)(/.*)?", t, re.I):
                        continue
                    key = re.sub(r"\s+", " ", t.lower())
                    if key in seen:
                        continue
                    seen.add(key)
                    cleaned.append(t)
                cleaned_text = re.sub(r"\s+", " ", " ".join(cleaned)).strip()
                # If cleaned is reasonably better/longer or original looked truncated, replace
                looked_truncated = (
                    raw.rstrip().endswith(("...", "…"))
                    or ("..." in raw)
                    or ("…" in raw)
                )
                if (len(cleaned_text) > max(len(raw), 150)) or looked_truncated:
                    post_dict["content"] = cleaned_text[:4000]
        except Exception as e:
            import logging

            logging.getLogger(__name__).debug(f"Content cleaning failed: {e}")
            pass

        # Perform AI analysis
        log(f"Analyzing content with AI...")

        try:
            analysis_result = await analyzer.analyze_content(analysis_content)

            # Start with original post data
            enhanced_post = dict(post_dict)

            # Only add essential analysis fields - lean schema
            essential_fields = {
                "ai_summary": analysis_result.get("ai_summary")
                or analysis_result.get("summary", ""),
                "value_score": analysis_result.get("value_score", 0.0),
                "quality_score": analysis_result.get(
                    "quality_score", analysis_result.get("content_quality_score", 0.0)
                ),
                "key_concepts": analysis_result.get("key_concepts", []),
                "tags": analysis_result.get("tags", []),
                "topic": analysis_result.get("topic", ""),
                "content_type": analysis_result.get("content_type", ""),
                "language": analysis_result.get("language", ""),
                "category": analysis_result.get("category", ""),  # Add category field
                "fit_categories": analysis_result.get(
                    "fit_categories", []
                ),  # Add fit_categories field
                "analyzed_at": analysis_result.get("analyzed_at"),
                "analysis_model": analysis_result.get("analysis_model")
                or analysis_result.get("ai_service"),
                # rewrite-focused
                "rewrite_score": analysis_result.get("rewrite_score"),
                "rewrite_readiness": analysis_result.get("rewrite_readiness"),
                "rewrite_reasons": analysis_result.get("rewrite_reasons"),
                "rewrite_risks": analysis_result.get("rewrite_risks"),
                "analysis_confidence": analysis_result.get("analysis_confidence"),
                "analysis_depth": analysis_result.get("analysis_depth"),
                "needs_deep_analysis": analysis_result.get("needs_deep_analysis"),
                # persona fit (OLD - keep for backward compatibility)
                "persona_fit_scores": analysis_result.get("persona_fit_scores"),
                "persona_fit_reasons": analysis_result.get("persona_fit_reasons"),
                "best_persona_key": analysis_result.get("best_persona_key"),
                "best_persona_score": analysis_result.get("best_persona_score"),
                "best_persona_reasons": analysis_result.get("best_persona_reasons"),
                # NEW: Dynamic profile matching (0-100 format for JSONB)
                "profile_matches": analysis_result.get("profile_matches", {}),
                # NEW: Creative rewrite suggestions (generated during analysis)
                "rewrite_suggestions": analysis_result.get("rewrite_suggestions", []),
                # time sensitivity
                "time_sensitive": analysis_result.get("time_sensitive"),
                "urgency_score": analysis_result.get("urgency_score"),
                "relevance_window": analysis_result.get("relevance_window"),
                "time_sensitive_reasons": analysis_result.get("time_sensitive_reasons"),
            }

            # Coerce defaults for completeness
            now_iso = datetime.now(timezone.utc).isoformat()
            if not essential_fields.get("analyzed_at"):
                essential_fields["analyzed_at"] = now_iso
            if not essential_fields.get("analysis_model"):
                essential_fields["analysis_model"] = "analyzer-default"

            # Lightweight language fallback if model omitted
            if not essential_fields.get("language"):
                txt = (post_dict.get("content") or "")[:500]
                cyr = sum(1 for c in txt if "\u0400" <= c <= "\u04FF")
                lat = sum(1 for c in txt if c.isalpha() and ord(c) < 128)
                essential_fields["language"] = (
                    "ru" if (cyr and cyr > 0.3 * (cyr + lat or 1)) else "en"
                )

            # Normalize scores to floats in 0-10 range
            def _to_score(x):
                try:
                    v = float(x)
                except Exception as e:
                    logger.error(f"Error: {e}")
                    v = 0.0
                return max(0.0, min(10.0, v))

            essential_fields["value_score"] = _to_score(
                essential_fields.get("value_score", 0.0)
            )
            essential_fields["quality_score"] = _to_score(
                essential_fields.get("quality_score", 0.0)
            )

            # Time sensitivity defaults
            if essential_fields.get("time_sensitive") is None:
                essential_fields["time_sensitive"] = False
            if essential_fields.get("urgency_score") is None:
                essential_fields["urgency_score"] = 0.0
            else:
                # CRITICAL: Normalize urgency_score to 0-1 scale (prevent 0-10 scale corruption)
                urgency = float(essential_fields.get("urgency_score", 0.0))
                if urgency > 1.0:
                    # If it's in 0-10 scale, convert to 0-1
                    essential_fields["urgency_score"] = min(1.0, urgency / 10.0)
                else:
                    essential_fields["urgency_score"] = max(0.0, min(1.0, urgency))
            if not essential_fields.get("relevance_window"):
                essential_fields["relevance_window"] = None
            if essential_fields.get("time_sensitive_reasons") is None:
                essential_fields["time_sensitive_reasons"] = ""

            # Rewrite-focused defaults
            if essential_fields.get("rewrite_score") is None:
                # Heuristic: use value_score as base for rewrite_score
                essential_fields["rewrite_score"] = _to_score(
                    essential_fields.get("value_score", 0.0)
                )
            if not essential_fields.get("rewrite_readiness"):
                summary_len = len(essential_fields.get("ai_summary") or "")
                essential_fields["rewrite_readiness"] = (
                    "ready"
                    if summary_len >= 150
                    else ("needs_context" if summary_len < 80 else "needs_trim")
                )
            if essential_fields.get("rewrite_reasons") is None:
                tags_count = len(essential_fields.get("tags") or [])
                concepts_count = len(essential_fields.get("key_concepts") or [])
                essential_fields["rewrite_reasons"] = [
                    f"Good tags ({tags_count})",
                    f"Concepts ({concepts_count})",
                ]
            if essential_fields.get("rewrite_risks") is None:
                risks = []
                summary = essential_fields.get("ai_summary") or ""
                if len(summary) < 120:
                    risks.append("Short summary")
                if not essential_fields.get("tags"):
                    risks.append("No tags")
                essential_fields["rewrite_risks"] = risks
            if essential_fields.get("analysis_confidence") is None:
                essential_fields["analysis_confidence"] = 0.7
            if not essential_fields.get("analysis_depth"):
                essential_fields["analysis_depth"] = "fast"
            if essential_fields.get("needs_deep_analysis") is None:
                rewrite_score = _to_score(essential_fields.get("rewrite_score", 0.0))
                confidence = essential_fields.get("analysis_confidence", 0.7)
                essential_fields["needs_deep_analysis"] = (
                    True if rewrite_score >= 8 and confidence < 0.8 else False
                )

            # Guarantee we always persist some summary text (fallback to content snippet)
            if not (
                essential_fields.get("ai_summary")
                and str(essential_fields.get("ai_summary")).strip()
            ):
                fallback_summary = (post_dict.get("content") or "").strip()
                fallback_summary = (
                    fallback_summary[:400].strip() if fallback_summary else ""
                )
                if fallback_summary:
                    logger.warning(
                        "AI summary missing for post %s (%s); using content fallback",
                        post_id,
                        platform,
                    )
                    essential_fields["ai_summary"] = fallback_summary
                else:
                    logger.warning(
                        "AI summary and content missing for post %s (%s); using placeholder summary",
                        post_id,
                        platform,
                    )
                    essential_fields["ai_summary"] = "Summary not available."

            # Persona fit defaults (OLD - keep for backward compatibility)
            if essential_fields.get("persona_fit_scores") is None:
                essential_fields["persona_fit_scores"] = {}
            if essential_fields.get("persona_fit_reasons") is None:
                essential_fields["persona_fit_reasons"] = {}

            # Fix corrupted best_persona_key values (should be persona name, not time sensitivity values or relevance_window)
            # Note: Now dynamic - can be any profile from config/personas/*.json, not just hardcoded ones
            best_key = essential_fields.get("best_persona_key")
            invalid_values = [
                "evergreen",
                "timely",
                "trending",
                "breaking",
                "urgent",
                "this-week",
                "this-month",
                "this-year",
                "next-week",
                "next-month",
            ]

            if best_key in invalid_values:
                essential_fields["best_persona_key"] = None
            elif not best_key:
                essential_fields["best_persona_key"] = None

            if essential_fields.get("best_persona_score") is None:
                essential_fields["best_persona_score"] = 0.0
            if essential_fields.get("best_persona_reasons") is None:
                essential_fields["best_persona_reasons"] = []

            # NEW: Profile matches defaults (dynamic - works with any profiles)
            if essential_fields.get("profile_matches") is None:
                essential_fields["profile_matches"] = {}
            if not isinstance(essential_fields.get("profile_matches"), dict):
                essential_fields["profile_matches"] = {}

            # Generate profile_matches if missing (using PersonaMatcher)
            # Check if profile_matches is None, empty dict, or only contains zeros (invalid matches)
            existing_matches = essential_fields.get("profile_matches")
            # Check if we have valid matches (non-zero scores)
            has_valid_matches = False
            if existing_matches and isinstance(existing_matches, dict):
                # Check if any score is > 0 (valid match)
                has_valid_matches = any(
                    float(v) > 0
                    for v in existing_matches.values()
                    if isinstance(v, (int, float))
                )

            if not existing_matches or (
                isinstance(existing_matches, dict)
                and (len(existing_matches) == 0 or not has_valid_matches)
            ):
                try:
                    log(
                        f"🔍 Generating profile_matches for {post_id} (existing: {existing_matches})",
                        "info",
                    )
                    from src.services.persona_matcher import get_persona_matcher

                    matcher = get_persona_matcher()
                    log(
                        f"✅ Persona matcher loaded, {len(matcher.personas)} personas available",
                        "info",
                    )
                    # Combine post data with analysis for matching
                    post_for_matching = {
                        **post_dict,
                        **essential_fields,
                        "summary": essential_fields.get("ai_summary", ""),
                        "embedding": post_dict.get(
                            "embedding"
                        ),  # Use existing embedding if available
                    }
                    # Get persona matches (returns 0-1 scale scores)
                    # Use lower threshold (0.2 = 20/100) to ensure we get matches
                    persona_result = matcher.get_recommended_personas(
                        post_for_matching, top_k=10, min_match_score=0.2
                    )
                    # Convert 0-1 scale to 0-100 scale for profile_matches
                    match_scores = persona_result.get("persona_match_scores", {})

                    # If no matches found, try even lower threshold or use fallback matching
                    if not match_scores:
                        # Try with very low threshold (0.1 = 10/100) to get at least some matches
                        persona_result = matcher.get_recommended_personas(
                            post_for_matching, top_k=5, min_match_score=0.1
                        )
                        match_scores = persona_result.get("persona_match_scores", {})

                    # If still no matches, assign a default low score to top personas as fallback
                    if not match_scores and matcher.personas:
                        # Fallback: assign 30/100 to first 3 personas as a baseline (above curation threshold)
                        # Filter out example personas (they're not real personas)
                        real_personas = [
                            p
                            for p in matcher.personas
                            if not p.get("key", "").endswith("_examples")
                        ]
                        for persona in real_personas[:3]:
                            persona_key = persona.get("key", "")
                            if persona_key:
                                match_scores[
                                    persona_key
                                ] = 0.30  # 30/100 baseline (meets curation threshold)
                                log(
                                    f"   Fallback: assigned baseline score to {persona_key}",
                                    "info",
                                )

                    essential_fields["profile_matches"] = {
                        persona_key: float(score) * 100.0  # Convert 0-1 to 0-100
                        for persona_key, score in match_scores.items()
                        if score >= 0.2  # Only include matches >= 20/100
                    }
                    # Also set best_persona_key and best_persona_score if not already set
                    if match_scores and not essential_fields.get("best_persona_key"):
                        best_persona = max(match_scores.items(), key=lambda x: x[1])
                        essential_fields["best_persona_key"] = best_persona[0]
                        essential_fields["best_persona_score"] = (
                            float(best_persona[1]) * 10.0
                        )  # Convert 0-1 to 0-10
                    log(
                        f"✅ Generated profile_matches: {len(essential_fields['profile_matches'])} personas - {list(essential_fields['profile_matches'].keys())}",
                        "info",
                    )
                    logger.info(
                        f"profile_matches values: {essential_fields['profile_matches']}"
                    )
                except Exception as persona_error:
                    logger.warning(
                        f"Persona matching failed for {post_id}: {persona_error}",
                        exc_info=True,
                    )
                    # Continue without profile_matches - curation will handle it
                    pass

            # NEW: Rewrite suggestions defaults
            if essential_fields.get("rewrite_suggestions") is None:
                essential_fields["rewrite_suggestions"] = []
            if not isinstance(essential_fields.get("rewrite_suggestions"), list):
                essential_fields["rewrite_suggestions"] = []

            # content_type fallback from media presence
            if not essential_fields.get("content_type"):
                urls = post_dict.get("media_urls") or []
                if urls:
                    if any(
                        str(u).lower().endswith((".mp4", ".mov", ".webm")) for u in urls
                    ):
                        essential_fields["content_type"] = "video"
                    elif any(
                        str(u)
                        .lower()
                        .endswith((".jpg", ".jpeg", ".png", ".gif", ".webp"))
                        for u in urls
                    ):
                        essential_fields["content_type"] = "image"
                    else:
                        essential_fields["content_type"] = "link"
                else:
                    essential_fields["content_type"] = "text"

            # Ensure list fields are actually lists
            for key in ("key_concepts", "tags"):
                val = essential_fields.get(key)
                if val is None:
                    essential_fields[key] = []
                elif not isinstance(val, list):
                    essential_fields[key] = [val] if val else []

            # Ensure author_handle exists
            if not (
                enhanced_post.get("author_handle") or post_dict.get("author_handle")
            ):
                author = (post_dict.get("author") or "").strip()
                if author:
                    enhanced_post["author_handle"] = author.split()[0]

            # Media/content fallback to ensure non-empty content
            try:
                if (
                    not enhanced_post.get("content")
                    or not str(enhanced_post.get("content")).strip()
                ):
                    fallback_pieces = []
                    # Prefer AI summary as a readable fallback
                    if essential_fields.get("ai_summary"):
                        fallback_pieces.append(str(essential_fields.get("ai_summary")))
                    # Use hashtags if present
                    ht = post_dict.get("hashtags") or []
                    if isinstance(ht, list) and ht:
                        fallback_pieces.append(
                            "#" + " #".join([str(h).strip("#") for h in ht[:8]])
                        )
                    # Include author handle
                    ah = post_dict.get("author_handle") or post_dict.get("username")
                    if ah:
                        fallback_pieces.append(f"by @{str(ah).lstrip('@')}")
                    # Include URL as last resort
                    if post_dict.get("url"):
                        fallback_pieces.append(str(post_dict.get("url")))
                    fallback_text = " \n".join([p for p in fallback_pieces if p])
                    if fallback_text:
                        enhanced_post["content"] = fallback_text[:4000]
                    else:
                        enhanced_post["content"] = "Content unavailable"
                # Ensure ai_summary fallback exists
                if not essential_fields.get("ai_summary"):
                    enhanced_post_ai = enhanced_post.get("content") or ""
                    essential_fields["ai_summary"] = (
                        enhanced_post_ai[:280] if enhanced_post_ai else ""
                    )
            except Exception as e:
                import logging

                logging.getLogger(__name__).debug(f"Content/media fallback failed: {e}")
                pass

            # Add only essential fields to the post
            enhanced_post.update(essential_fields)

            log(f"Analysis completed successfully", "success")

            # Generate embedding for semantic search
            try:
                from src.core.indexing.embedding_service import get_embedding_service

                embedding_service = get_embedding_service()
                if embedding_service.is_available():
                    # Prepare content (uses: content, title, hashtags, author)
                    content_for_embedding = (
                        embedding_service.prepare_content_for_embedding(enhanced_post)
                    )

                    # Generate embedding vector
                    embedding = embedding_service.generate_embedding(
                        content_for_embedding
                    )

                    if embedding:
                        enhanced_post["embedding"] = embedding
                        enhanced_post["embedding_model"] = embedding_service.model_name
                        log(f"Generated embedding ({len(embedding)} dims)", "success")
                    else:
                        log(f"Failed to generate embedding", "debug")
                else:
                    log("Embedding service not available", "debug")
            except Exception as embed_error:
                logger.error(f"Error: {embed_error}")
                log(f"Embedding generation error: {embed_error}", "debug")

            # Ensure model marker
            if (
                "analysis_model" not in enhanced_post
                and "ai_service" in analysis_result
            ):
                enhanced_post["analysis_model"] = analysis_result["ai_service"]

        except Exception as analysis_error:
            log(f"AI analysis failed: {analysis_error}", "warning")
            import logging
            import traceback

            logging.getLogger(__name__).error(
                f"AI analysis error traceback:\n{traceback.format_exc()}"
            )

            # Track analysis error
            hub.errors.capture_exception(
                analysis_error,
                context={
                    "operation": "ai_analysis",
                    "post_id": post_id,
                    "platform": platform,
                },
            )
            hub.metrics.increment(
                "analyzer.analyze_post.analysis_failed",
                labels={
                    "platform": platform,
                    "error_type": type(analysis_error).__name__,
                },
            )

            enhanced_post = post_dict  # Use original data if analysis fails

    # CRITICAL: Use StorageFacade directly (single source of truth)
    # StorageFacade handles: duplicate checks, SQLite + Supabase sync, collected_at
    # DatabaseAgent adds normalization and monitoring on top
    from src.storage.db import get_storage

    storage = get_storage()

    # Ensure post_id is set
    if not enhanced_post.get("post_id"):
        from src.storage.id_generator import PostIDGenerator

        enhanced_post["post_id"] = PostIDGenerator.generate_post_id(enhanced_post)

    try:
        log(f"Saving post via StorageFacade: {enhanced_post.get('post_id', 'unknown')}")
        result = storage.save_post(enhanced_post)
        if result:
            log(
                f"✅ Saved to database successfully via StorageFacade: {enhanced_post.get('post_id')}",
                "success",
            )

            # Optional: Use DatabaseAgent for monitoring/validation (non-blocking)
            if db_agent:
                try:
                    db_agent.validate_and_monitor_post(enhanced_post)
                except Exception as e:
                    logger.error(f"Error: {e}")
                    pass  # Don't fail if monitoring fails

            # Track success
            hub.metrics.increment(
                "analyzer.analyze_post.success",
                labels={
                    "platform": platform,
                    "has_analysis": str(bool(enhanced_post.get("ai_summary"))),
                },
            )
            return True
        else:
            log(
                f"❌ StorageFacade save returned False for post: {enhanced_post.get('post_id')}",
                "error",
            )
            # Track failure
            hub.metrics.increment(
                "analyzer.analyze_post.failed",
                labels={
                    "platform": platform,
                    "reason": "storage_facade_returned_false",
                },
            )
            return False
    except Exception as save_error:
        logger.error(f"Error: {save_error}")
        log(
            f"StorageFacade save failed: {save_error}",
            "error",
        )
        return False

    # REMOVED: All legacy fallback paths - StorageFacade is the only path now
    # Legacy code below is kept for reference but should never execute
    if False:  # Disabled legacy path
        # Update post in local database instead of adding
        try:
            # Try to update the existing post with analysis data
            local_updated = False
            try:
                if hasattr(db_manager, "update_post"):
                    local_updated = bool(db_manager.update_post(post_id, enhanced_post))
            except Exception as e:
                logger.error(f"Error: {e}")
                log(f"Local update failed: {e}", "warning")
                local_updated = False

            if not local_updated:
                # If update did not apply (e.g., duplicate/ignored), try insert
                try:
                    local_stored = bool(db_manager.add_post(enhanced_post))
                except Exception as e:
                    logger.error(f"Error: {e}")
                    log(f"Local insert failed: {e}", "warning")
                    local_stored = False

                if not local_stored:
                    # Final existence check: consider success if row already exists
                    try:
                        if hasattr(
                            db_manager, "get_post_by_id"
                        ) and db_manager.get_post_by_id(post_id):
                            log(
                                "Post already existed; analysis update may have been a no-op",
                                "info",
                            )
                        else:
                            log(
                                "Local store/update did not apply; proceeding anyway",
                                "warning",
                            )
                    except Exception as e:
                        # If we cannot check existence, don't block pipeline
                        import logging

                        logging.getLogger(__name__).debug(
                            f"Could not verify local existence: {e}"
                        )
                        log("Could not verify local existence; proceeding", "warning")
            log(f"Local persistence complete", "success")
        except Exception as local_error:
            logger.error(f"Error: {local_error}")
            log(f"Local database operation failed: {local_error}", "error")
            return False

    # Fallback: Store in Supabase if available (legacy path - should not be needed if DatabaseAgent works)
    if supabase_manager:
        try:
            log(
                f"Attempting Supabase sync for post: {enhanced_post.get('post_id', 'unknown')}"
            )
            # Support both legacy SupabaseManager (insert_post) and new SupabaseAdapter (save_post)
            if hasattr(supabase_manager, "insert_post"):
                cloud_result = supabase_manager.insert_post(enhanced_post)
            elif hasattr(supabase_manager, "save_post"):
                cloud_result = supabase_manager.save_post(enhanced_post)
            else:
                log(
                    f"Supabase sync object does not support insert/save operations: {type(supabase_manager).__name__}",
                    "error",
                )
                cloud_result = False
            if cloud_result:
                log(
                    f"✅ Synced to Supabase successfully: {enhanced_post.get('post_id')}",
                    "success",
                )
            else:
                log(
                    f"❌ Supabase sync returned False for post: {enhanced_post.get('post_id')}",
                    "error",
                )
                log(f"Post data keys: {list(enhanced_post.keys())}", "error")
        except Exception as cloud_error:
            logger.error(f"Error: {cloud_error}")
            log(f"❌ Supabase sync exception: {cloud_error}", "error")
            log(
                f"Post data: {enhanced_post.get('post_id')} - {enhanced_post.get('url', 'no url')}",
                "error",
            )
            # Don't fail the whole operation if cloud sync fails
    else:
        log(f"⚠️ No Supabase manager available - skipping cloud sync", "warning")

    return True
