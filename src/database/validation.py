#!/usr/bin/env python3
"""
Database Validation Module

Handles post validation, data quality checks, and data normalization.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

from src.shared.utils.logging_config import get_logger

logger = get_logger(__name__)


class DatabaseValidation:
    """Handles database validation and data quality checks"""

    def __init__(self, validate_post_fn=None, record_post_operation_fn=None):
        self._validate_post = validate_post_fn
        self._record_post_operation = record_post_operation_fn
        self._record_post_operation_set = record_post_operation_fn is not None

    def validate_and_monitor_post(self, post: Dict[str, Any]) -> Dict[str, Any]:
        """
        Proactive DBA function: Validate, check quality, and monitor every post.
        Like a human DBA would do - double-check everything.

        Returns:
            Dict with validation results, issues found, and monitoring status
        """
        results = {
            "validated": False,
            "quality_checked": False,
            "issues_found": [],
            "warnings": [],
            "monitored": False,
        }

        try:
            # 1. VALIDATE POST (double-check even if already validated)
            if self._validate_post:
                validation = self._validate_post(post, strict=True)
                results["validated"] = True

                if not validation.is_valid:
                    results["issues_found"].extend(
                        [f"Validation failed: {err}" for err in validation.errors]
                    )
                    logger.warning(
                        f"🔍 DB Agent: Post {post.get('post_id')} failed validation: {validation.errors}"
                    )

                if validation.warnings:
                    results["warnings"].extend(
                        [f"Warning: {warn}" for warn in validation.warnings]
                    )
                    logger.debug(
                        f"🔍 DB Agent: Post {post.get('post_id')} has warnings: {validation.warnings}"
                    )

            # 2. CHECK DATA QUALITY
            quality_issues = self._check_data_quality(post)
            results["quality_checked"] = True
            if quality_issues:
                results["issues_found"].extend(quality_issues)
                logger.warning(
                    f"🔍 DB Agent: Post {post.get('post_id')} has quality issues: {quality_issues}"
                )

            # 3. CHECK FOR COMMON COLLECTION ISSUES
            collection_issues = self._check_collection_issues(post)
            if collection_issues:
                results["issues_found"].extend(collection_issues)
                logger.warning(
                    f"🔍 DB Agent: Post {post.get('post_id')} has collection issues: {collection_issues}"
                )

            # 4. CHECK DATA INTEGRITY
            integrity_issues = self._check_data_integrity(post)
            if integrity_issues:
                results["issues_found"].extend(integrity_issues)
                logger.warning(
                    f"🔍 DB Agent: Post {post.get('post_id')} has integrity issues: {integrity_issues}"
                )

            # 5. TRACK OPERATION
            is_update = (
                post.get("analyzed_at")
                or post.get("quality_score")
                or post.get("value_score")
            )
            # Check if record_post_operation was set dynamically
            record_fn = (
                getattr(self, "_record_post_operation", None)
                or self._record_post_operation
            )
            if record_fn:
                try:
                    record_fn(
                        post_id=post.get("post_id"),
                        platform=post.get("platform"),
                        operation="update" if is_update else "insert",
                        quality_score=post.get("quality_score"),
                        value_score=post.get("value_score"),
                        has_analysis=bool(
                            post.get("analyzed_at") or post.get("ai_summary")
                        ),
                    )
                    results["monitored"] = True
                except Exception as e:
                    logger.error(f"Error: {e}")
                    pass

            # 6. ALERT ON CRITICAL ISSUES
            if results["issues_found"]:
                self._alert_on_issues(post, results["issues_found"])

        except Exception as e:
            logger.error(f"DB Agent validate_and_monitor_post failed: {e}")

        return results

    def _check_data_quality(self, post: Dict[str, Any]) -> List[str]:
        """Check data quality issues"""
        issues = []

        # Check for truncated content
        content = post.get("content", "")
        if content and ("..." in content[-20:] or content.endswith("...")):
            issues.append("Content appears truncated (ends with ...)")

        # Check for placeholder content
        if content and any(
            placeholder in content.lower()
            for placeholder in [
                "scraping failed",
                "extraction failed",
                "content extraction in progress",
                "post from",
                "placeholder",
                "loading",
                "error extracting",
            ]
        ):
            issues.append("Content appears to be placeholder/error message")

        # Check for missing essential fields
        if not post.get("author") or post.get("author", "").lower() in [
            "unknown",
            "n/a",
            "",
        ]:
            issues.append("Author is missing or placeholder")

        if not post.get("url") or not post.get("url", "").startswith("http"):
            issues.append("URL is missing or invalid")

        # Check for suspicious quality scores
        quality_score = post.get("quality_score")
        if quality_score is not None:
            try:
                qs = float(quality_score)
                if qs < 0 or qs > 10:
                    issues.append(f"Quality score out of range: {qs} (should be 0-10)")
            except (ValueError, TypeError):
                issues.append(f"Quality score is not numeric: {quality_score}")

        value_score = post.get("value_score")
        if value_score is not None:
            try:
                vs = float(value_score)
                if vs < 0 or vs > 10:
                    issues.append(f"Value score out of range: {vs} (should be 0-10)")
            except (ValueError, TypeError):
                issues.append(f"Value score is not numeric: {value_score}")

        return issues

    def _check_collection_issues(self, post: Dict[str, Any]) -> List[str]:
        """Check for common collection issues"""
        issues = []

        # Check for duplicate indicators
        if post.get("_is_duplicate") or post.get("duplicate"):
            issues.append("Post marked as duplicate but was saved anyway")

        # Check for collection errors
        if post.get("collection_error") or post.get("_collection_failed"):
            issues.append("Post has collection error flag")

        # Check for missing platform-specific data
        platform = post.get("platform", "").lower()
        if platform == "threads":
            if not post.get("author_handle") and "@" not in (post.get("url", "")):
                issues.append("Threads post missing author handle")
        elif platform == "twitter":
            if not post.get("author_handle") and not post.get("author"):
                issues.append("Twitter post missing author information")
        elif platform == "reddit":
            if not post.get("post_id", "").startswith("t3_"):
                # Reddit IDs should have t3_ prefix
                if post.get("post_id") and not any(
                    c in post.get("post_id", "") for c in ["/", "-"]
                ):
                    issues.append("Reddit post_id may be missing t3_ prefix")

        return issues

    def _check_data_integrity(self, post: Dict[str, Any]) -> List[str]:
        """Check data integrity issues"""
        issues = []

        # Check for conflicting timestamps
        created_at = post.get("created_at")
        analyzed_at = post.get("analyzed_at")
        if created_at and analyzed_at:
            try:
                from datetime import timedelta, timezone

                from dateutil.parser import parse

                created = parse(str(created_at))
                analyzed = parse(str(analyzed_at))

                # Normalize timezones - ensure both are timezone-aware
                if created.tzinfo is None:
                    created = created.replace(tzinfo=timezone.utc)
                if analyzed.tzinfo is None:
                    analyzed = analyzed.replace(tzinfo=timezone.utc)

                # Only flag as an issue if analyzed_at is significantly before created_at
                # (more than 1 hour difference to account for timezone/clock drift)
                # This prevents false positives from minor timestamp mismatches
                time_diff = analyzed - created
                if time_diff < timedelta(hours=-1):
                    issues.append("analyzed_at is before created_at (impossible)")
                    # Auto-fix: set analyzed_at to created_at (or current time if later)
                    # This ensures data integrity
                    from datetime import datetime
                    now = datetime.now(timezone.utc)
                    fixed_analyzed_at = max(created, now).isoformat()
                    # Update the post dict so the fix is applied
                    post["analyzed_at"] = fixed_analyzed_at
                    logger.info(
                        f"Auto-fixed analyzed_at for post {post.get('post_id', 'unknown')}: "
                        f"was {analyzed_at}, now {fixed_analyzed_at}"
                    )
            except Exception as e:
                # Don't log as error - datetime parsing failures are expected for malformed data
                logger.debug(f"Datetime comparison skipped: {e}")
                pass

        # Check for analysis without required fields
        if analyzed_at or post.get("ai_summary"):
            if not post.get("ai_summary") and not post.get("value_score"):
                issues.append(
                    "Post marked as analyzed but missing ai_summary and value_score"
                )

        # Check for quality score without analysis
        if post.get("quality_score") and not (analyzed_at or post.get("ai_summary")):
            issues.append("Post has quality_score but no analysis timestamp")

        # Check for empty required fields
        if not post.get("post_id"):
            issues.append("Post missing post_id (required)")
        if not post.get("platform"):
            issues.append("Post missing platform (required)")

        # Check for invalid platform
        valid_platforms = ["twitter", "reddit", "threads", "github", "telegram", "rss"]
        if post.get("platform") and post.get("platform").lower() not in valid_platforms:
            issues.append(f"Invalid platform: {post.get('platform')}")

        return issues

    def _alert_on_issues(self, post: Dict[str, Any], issues: List[str]) -> None:
        """Alert on critical issues found"""
        if not issues:
            return

        try:
            # Log critical issues
            post_id = post.get("post_id", "unknown")
            platform = post.get("platform", "unknown")
            logger.warning(
                f"⚠️ DB Agent: Post {post_id} ({platform}) has {len(issues)} issues: {', '.join(issues[:3])}"
            )

            # If too many issues, send alert
            if len(issues) >= 3:
                message = (
                    f"🔍 DB Agent Alert: Post {post_id} ({platform}) has {len(issues)} issues:\n"
                    + "\n".join(f"  - {issue}" for issue in issues[:5])
                )

                # Try Telegram if configured
                token = os.getenv("TELEGRAM_BOT_TOKEN")
                chat_id = os.getenv("TELEGRAM_CHAT_ID") or os.getenv(
                    "TELEGRAM_ADMIN_CHAT_ID"
                )
                if token and chat_id:
                    try:
                        url = f"https://api.telegram.org/bot{token}/sendMessage"
                        payload = {
                            "chat_id": chat_id,
                            "text": message[:4000],
                        }  # Telegram limit
                        requests.post(url, json=payload, timeout=10)
                    except Exception as e:
                        logger.error(f"Error: {e}")
                        pass
        except Exception as e:
            logger.error(f"Error: {e}")
            pass

    def normalize_post_data(self, post: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize and clean post data BEFORE validation.
        This is the critical step that prevents corrupted data from entering the database.

        Fixes:
        - Corrupted timestamps (AI summary text in created_at)
        - Invalid persona keys (time sensitivity values in best_persona_key)
        - String scores (converts to floats)
        - Missing analysis fields (applies defaults)
        """
        import json
        from datetime import datetime

        # Create a copy to avoid modifying the original
        normalized = dict(post)

        # Normalize timestamp function
        def normalize_timestamp(value, fallback=None):
            if not value:
                return fallback or datetime.now().isoformat()
            if isinstance(value, datetime):
                return value.isoformat()
            if isinstance(value, str):
                # Skip if it looks like text content (not a timestamp)
                if len(value) > 50 or not any(c.isdigit() for c in value[:10]):
                    return fallback or datetime.now().isoformat()
                # Try various timestamp formats
                formats = [
                    "%Y-%m-%dT%H:%M:%S.%f",
                    "%Y-%m-%dT%H:%M:%S",
                    "%Y-%m-%d %H:%M:%S",
                    "%Y-%m-%d %H:%M:%S.%f",
                    "%Y-%m-%d",
                ]
                for fmt in formats:
                    try:
                        dt = datetime.strptime(value[: len(fmt) + 10], fmt)
                        return dt.isoformat()
                    except (ValueError, TypeError):
                        continue
                return fallback or datetime.now().isoformat()
            return fallback or datetime.now().isoformat()

        # Normalize score function
        def normalize_score(value, default=0.0):
            if value is None:
                return default
            if isinstance(value, (int, float)):
                return max(0.0, min(10.0, float(value)))
            if isinstance(value, str):
                try:
                    return max(0.0, min(10.0, float(value)))
                except (ValueError, TypeError):
                    return default
            return default

        # Normalize boolean function
        def normalize_boolean(value, default=True):
            if value is None:
                return default
            if isinstance(value, bool):
                return value
            if isinstance(value, (int, float)):
                return bool(value)
            if isinstance(value, str):
                value_stripped = value.strip()
                # Check if it looks like JSON (array or object) - invalid for boolean
                if value_stripped.startswith(("{", "[")):
                    try:
                        from src.shared.utils.logging_config import get_logger

                        get_logger(__name__).warning(
                            f"Invalid boolean value appears to be JSON: {value_stripped[:50]}..., using default {default}"
                        )
                    except Exception as e:
                        logger.error(f"Error: {e}")
                        pass
                    return default
                value_lower = value_stripped.lower()
                if value_lower in ("true", "1", "yes", "on", "t"):
                    return True
                elif value_lower in ("false", "0", "no", "off", "f", ""):
                    return False
                # Unknown string value - use default
                try:
                    from src.shared.utils.logging_config import get_logger

                    get_logger(__name__).warning(
                        f"Unknown boolean string value: {value_stripped[:50]}..., using default {default}"
                    )
                except Exception as e:
                    logger.error(f"Error: {e}")
                    pass
                return default
            # Unknown type - use default
            try:
                from src.shared.utils.logging_config import get_logger

                get_logger(__name__).warning(
                    f"Unknown boolean type: {type(value)}, using default {default}"
                )
            except Exception as e:
                logger.error(f"Error: {e}")
                pass
            return default

        # Normalize Reddit post IDs to include t3_ prefix
        platform_value = str(normalized.get("platform") or "").lower()
        post_id_value = normalized.get("post_id")
        if platform_value == "reddit" and post_id_value:
            post_id_str = str(post_id_value).strip()
            if post_id_str:
                cleaned_suffix = (
                    post_id_str.replace("t3_", "").replace("T3_", "").strip()
                )
                normalized["post_id"] = f"t3_{cleaned_suffix}"

        # Fix corrupted created_at (should be timestamp, not AI summary)
        created_at = normalized.get("created_at")
        if created_at and isinstance(created_at, str) and len(created_at) > 50:
            # It's probably AI summary text, try to get real timestamp from other fields
            fallback = (
                normalized.get("created_timestamp")
                or normalized.get("saved_at")
                or normalized.get("updated_timestamp")
            )
            normalized["created_at"] = normalize_timestamp(fallback)

        # Fix corrupted analyzed_at (should be ISO timestamp, not service name or list)
        analyzed_at = normalized.get("analyzed_at")
        if analyzed_at:
            # Check if it's corrupted (service name, list, or invalid format)
            if isinstance(analyzed_at, (list, dict)):
                # It's a list or dict - definitely corrupted
                logger.warning(
                    f"Corrupted analyzed_at is {type(analyzed_at).__name__}, fixing to current timestamp"
                )
                normalized["analyzed_at"] = datetime.utcnow().isoformat()
            elif isinstance(analyzed_at, str):
                # Check if it's a service name or invalid format
                analyzed_at_lower = analyzed_at.lower().strip()
                invalid_values = [
                    "mistral",
                    "gemini",
                    "ollama",
                    "qwen",
                    "ai_service",
                    "unknown",
                    "none",
                    "null",
                    "",
                ]
                if analyzed_at_lower in invalid_values:
                    # It's a service name - corrupted
                    logger.warning(
                        f"Corrupted analyzed_at is service name '{analyzed_at}', fixing to current timestamp"
                    )
                    normalized["analyzed_at"] = datetime.utcnow().isoformat()
                elif (
                    not analyzed_at.startswith(("202", "2023", "2024", "2025"))
                    and len(analyzed_at) < 10
                ):
                    # Doesn't look like a timestamp (should start with year and be at least 10 chars)
                    logger.warning(
                        f"Corrupted analyzed_at doesn't look like timestamp: '{analyzed_at[:50]}', fixing to current timestamp"
                    )
                    normalized["analyzed_at"] = datetime.utcnow().isoformat()
                else:
                    # Try to normalize it as a timestamp
                    normalized["analyzed_at"] = normalize_timestamp(
                        analyzed_at, datetime.utcnow().isoformat()
                    )
            else:
                # Not a string, list, or dict - probably corrupted
                logger.warning(
                    f"Corrupted analyzed_at is {type(analyzed_at).__name__}, fixing to current timestamp"
                )
                normalized["analyzed_at"] = datetime.utcnow().isoformat()
        else:
            # Missing analyzed_at - set to current timestamp
            normalized["analyzed_at"] = datetime.utcnow().isoformat()

        # Ensure analyzed_at is not before created_at (data integrity fix)
        created_at = normalized.get("created_at")
        if created_at and normalized.get("analyzed_at"):
            try:
                from datetime import timezone

                from dateutil.parser import parse
                
                created = parse(str(created_at))
                analyzed = parse(str(normalized["analyzed_at"]))
                
                # Normalize timezones
                if created.tzinfo is None:
                    created = created.replace(tzinfo=timezone.utc)
                if analyzed.tzinfo is None:
                    analyzed = analyzed.replace(tzinfo=timezone.utc)
                
                # If analyzed_at is before created_at, fix it
                if analyzed < created:
                    # Set analyzed_at to created_at (or current time if later)
                    now = datetime.now(timezone.utc)
                    fixed_analyzed_at = max(created, now).isoformat()
                    normalized["analyzed_at"] = fixed_analyzed_at
                    logger.debug(
                        f"Fixed analyzed_at < created_at: set to {fixed_analyzed_at}"
                    )
            except Exception as e:
                # Don't fail on datetime parsing errors
                logger.debug(f"Could not validate analyzed_at vs created_at: {e}")

        # Check if post is deprecated (old time-sensitive content)
        # Also check if currently deprecated post should NOT be deprecated (evergreen content)
        is_deprecated = False
        current_category = normalized.get("category")
        currently_deprecated = (
            current_category and str(current_category).upper() == "DEPRECATED"
        )
        created_at = normalized.get("created_at")
        relevance_window = normalized.get("relevance_window", "evergreen")
        urgency_score = normalized.get("urgency_score", 0.0)
        time_sensitive = normalized.get("time_sensitive", False)

        if created_at:
            try:
                from datetime import datetime, timedelta

                # Parse created_at
                if isinstance(created_at, str):
                    # Try to parse ISO format
                    try:
                        created_dt = datetime.fromisoformat(
                            created_at.replace("Z", "+00:00")
                        )
                    except Exception as e:
                        logger.error(f"Error: {e}")
                        # Try other formats
                        try:
                            created_dt = datetime.strptime(
                                created_at[:19], "%Y-%m-%dT%H:%M:%S"
                            )
                        except Exception as e:
                            logger.error(f"Error: {e}")
                            created_dt = None
                    if created_dt:
                        # Normalize timezone for comparison - ensure both are timezone-aware or both are naive
                        from datetime import timezone

                        if created_dt.tzinfo is None:
                            # Naive datetime - make it timezone-aware (UTC)
                            created_dt = created_dt.replace(tzinfo=timezone.utc)
                        now = datetime.now(timezone.utc)

                        age_days = (now - created_dt).days
                        age_months = age_days / 30.0
                        age_years = age_days / 365.0

                        # Mark as deprecated if post was time-sensitive in the past and is now outdated
                        # OR if post is old enough that it's likely outdated (conservative approach)
                        # Deprecated posts = posts that WERE time-sensitive OR are too old to be relevant for rewrites

                        # 1. Time-sensitive relevance windows that have expired
                        if (
                            relevance_window
                            and relevance_window != "evergreen"
                            and relevance_window != ""
                        ):
                            # This post was time-sensitive - check if it's expired
                            if relevance_window == "same-day" and age_days > 1:
                                is_deprecated = True
                            elif relevance_window == "24-72h" and age_days > 3:
                                is_deprecated = True
                            elif relevance_window == "this-week" and age_days > 7:
                                is_deprecated = True
                            elif relevance_window == "this-month" and age_months > 1:
                                is_deprecated = True

                        # 2. Explicitly marked as time_sensitive but old (> 6 months)
                        # If time_sensitive flag is set, it means the post was time-sensitive
                        if time_sensitive and age_months > 6:
                            is_deprecated = True

                        # 3. High urgency score indicates time-sensitive content - deprecate if old
                        # High urgency (> 0.7) means it was urgent/time-sensitive
                        if urgency_score > 0.7:
                            if age_days > 7:
                                # High urgency but more than a week old
                                is_deprecated = True
                            elif age_months > 1:
                                # High urgency but more than a month old
                                is_deprecated = True

                        # 4. Medium urgency (> 0.5) but old (> 1 year) - likely was time-sensitive
                        if urgency_score > 0.5 and age_years > 1:
                            is_deprecated = True

                        # 5. NEWS category posts are inherently time-sensitive - deprecate if old (> 1 year)
                        category_upper = (normalized.get("category", "") or "").upper()
                        if category_upper == "NEWS" and age_years > 1:
                            is_deprecated = True

                        # 6. AGGRESSIVE: Very old posts (> 2 years) - deprecate ALL of them
                        # Content older than 2 years is almost certainly outdated for rewrites,
                        # even if it was originally evergreen. Very old content loses relevance.
                        if age_years > 2:
                            is_deprecated = True

                        # 7. AGGRESSIVE: Old posts (> 1 year) - deprecate ALL of them
                        # Even if marked as "evergreen", content older than 1 year is likely outdated.
                        # Many old posts were time-sensitive when posted, even if analysis marked them as evergreen.
                        # Old content is not suitable for rewrites regardless of original classification.
                        if age_years > 1 and age_years <= 2:
                            is_deprecated = True

                        # 8. AGGRESSIVE: Posts 6-12 months old - deprecate ALL of them
                        # Posts in this age range were likely time-sensitive when posted.
                        # Even if marked as "evergreen", they're too old to be relevant for rewrites.
                        if age_months >= 6 and age_months < 12:
                            is_deprecated = True
            except Exception as e:
                # Log error but don't fail - use get_logger if available
                try:
                    from src.shared.utils.logging_config import get_logger

                    logger = get_logger(__name__)
                    logger.warning(f"Error checking deprecation for post: {e}")
                except Exception as e:
                    logger.error(f"Error: {e}")
                    pass
                pass

        # Normalize category to our expected format (if present) or infer from content
        category = normalized.get("category")
        if category:
            category = str(category).strip()
        else:
            category = ""

        # Always try to infer category from content if missing or invalid
        content = normalized.get("content", "") or ""
        content_lower = content.lower() if content else ""

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

        # Handle deprecation status
        if is_deprecated:
            # Post should be deprecated - set category to DEPRECATED
            normalized["category"] = "DEPRECATED"
            category = "DEPRECATED"
        elif currently_deprecated and not is_deprecated:
            # Post was incorrectly deprecated - clear category so it gets re-inferred
            normalized["category"] = None
            category = ""

        # If category is missing or invalid, infer it
        if not category or category not in valid_categories:
            # Try to normalize existing category first
            if category:
                try:
                    from src.domain.analysis.analyzers.intelligent_content_analyzer import (
                        IntelligentContentAnalyzer,
                    )

                    analyzer = IntelligentContentAnalyzer()
                    normalized_category = analyzer._normalize_category(category)
                    if normalized_category:
                        normalized["category"] = normalized_category
                        category = normalized_category
                except Exception as e:
                    logger.error(f"Error: {e}")
                    pass

            # If still no valid category, infer from content
            if not category or category not in [
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
            ]:
                if content_lower:
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
                            "solana",
                            "eth",
                            "btc",
                        ]
                    ):
                        normalized["category"] = "CRYPTO"
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
                            "heart",
                            "broken",
                        ]
                    ):
                        normalized["category"] = "DATING"
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
                            "algorithm",
                            "api",
                            "framework",
                            "github",
                            "python",
                            "javascript",
                        ]
                    ):
                        normalized["category"] = "TECH"
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
                            "funding",
                            "vc",
                            "venture",
                        ]
                    ):
                        normalized["category"] = "BUSINESS"
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
                            "teaching",
                        ]
                    ):
                        normalized["category"] = "LEARNING"
                    elif any(
                        kw in content_lower
                        for kw in [
                            "news",
                            "breaking",
                            "announced",
                            "reported",
                            "politics",
                            "world",
                            "government",
                        ]
                    ):
                        normalized["category"] = "NEWS"
                    elif any(
                        kw in content_lower
                        for kw in [
                            "health",
                            "fitness",
                            "nutrition",
                            "wellness",
                            "medical",
                            "diet",
                            "exercise",
                            "doctor",
                        ]
                    ):
                        normalized["category"] = "HEALTH"
                    elif any(
                        kw in content_lower
                        for kw in [
                            "movie",
                            "music",
                            "game",
                            "entertainment",
                            "fun",
                            "meme",
                            "comedy",
                            "film",
                        ]
                    ):
                        normalized["category"] = "ENTERTAINMENT"
                    else:
                        normalized["category"] = "OTHER"
                else:
                    # No content to infer from - set to OTHER as default
                    normalized["category"] = "OTHER"
                category = normalized["category"]

        # Fix corrupted best_persona_key (should be persona name, not time sensitivity value or other invalid values)
        best_key = normalized.get("best_persona_key")
        valid_personas = ["qronoya", "aspandead", "claimzilla"]
        invalid_persona_values = [
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
            "same-day",
            "24-72h",
            "this-week",
            "this-month",
        ]

        # Fix invalid persona keys: if it's not a valid persona, set to None
        if best_key:
            if best_key not in valid_personas or best_key in invalid_persona_values:
                # Invalid persona key - clear it so it can be remapped
                normalized["best_persona_key"] = None
                # Also clear the score if persona is invalid
                if normalized.get("best_persona_score"):
                    normalized["best_persona_score"] = 0.0

        # If category is set but best_persona_key is not, try to map category to persona
        if normalized.get("category") and not normalized.get("best_persona_key"):
            category = normalized.get("category")
            category_to_persona = {
                "TECH": "qronoya",
                "DATING": "aspandead",
                "CRYPTO": "claimzilla",
                "BUSINESS": "qronoya",
                "LEARNING": "qronoya",
            }
            if category in category_to_persona:
                normalized["best_persona_key"] = category_to_persona[category]
                normalized[
                    "best_persona_score"
                ] = 7.0  # Medium confidence for category-based mapping

        # Fix string scores (should be numeric)
        for field in [
            "rewrite_score",
            "analysis_confidence",
            "best_persona_score",
            "value_score",
            "quality_score",
            "urgency_score",
        ]:
            value = normalized.get(field)
            if isinstance(value, str):
                if field == "analysis_confidence":
                    normalized[field] = normalize_score(value, 0.7)
                else:
                    normalized[field] = normalize_score(value, 0.0)

        # Apply defaults for missing analysis fields
        if normalized.get("rewrite_score") is None:
            vs = normalize_score(normalized.get("value_score", 0.0))
            normalized["rewrite_score"] = vs

        if not normalized.get("rewrite_readiness"):
            summary = normalized.get("ai_summary") or ""
            summary_len = len(summary)
            normalized["rewrite_readiness"] = (
                "ready"
                if summary_len >= 150
                else ("needs_context" if summary_len < 80 else "needs_trim")
            )

        if normalized.get("rewrite_reasons") is None:
            tags = normalized.get("tags") or []
            concepts = normalized.get("key_concepts") or []
            tags_count = len(tags) if isinstance(tags, list) else 0
            concepts_count = len(concepts) if isinstance(concepts, list) else 0
            normalized["rewrite_reasons"] = [
                f"Good tags ({tags_count})",
                f"Concepts ({concepts_count})",
            ]

        if normalized.get("rewrite_risks") is None:
            risks = []
            summary = normalized.get("ai_summary") or ""
            if len(summary) < 120:
                risks.append("Short summary")
            tags = normalized.get("tags") or []
            if not tags or (isinstance(tags, list) and len(tags) == 0):
                risks.append("No tags")
            normalized["rewrite_risks"] = risks

        if normalized.get("analysis_confidence") is None:
            normalized["analysis_confidence"] = 0.7

        if not normalized.get("analysis_depth"):
            normalized["analysis_depth"] = "fast"

        if normalized.get("needs_deep_analysis") is None:
            rewrite_score = normalize_score(normalized.get("rewrite_score", 0.0))
            confidence = normalize_score(normalized.get("analysis_confidence", 0.7))
            normalized["needs_deep_analysis"] = (
                True if rewrite_score >= 8 and confidence < 0.8 else False
            )

        # Persona fit defaults
        if normalized.get("persona_fit_scores") is None:
            normalized["persona_fit_scores"] = {}
        if normalized.get("persona_fit_reasons") is None:
            normalized["persona_fit_reasons"] = {}
        if (
            not normalized.get("best_persona_key")
            or normalized.get("best_persona_key") in invalid_persona_values
        ):
            normalized["best_persona_key"] = None
        if normalized.get("best_persona_score") is None:
            normalized["best_persona_score"] = 0.0
        if normalized.get("best_persona_reasons") is None:
            normalized["best_persona_reasons"] = []

        # Normalize boolean fields (fix corrupted JSON arrays/objects in boolean fields)
        # Always normalize these fields if they exist, or set defaults
        normalized["is_saved"] = normalize_boolean(normalized.get("is_saved"), True)
        normalized["time_sensitive"] = normalize_boolean(
            normalized.get("time_sensitive"), False
        )
        normalized["needs_deep_analysis"] = normalize_boolean(
            normalized.get("needs_deep_analysis"), False
        )

        # Time sensitivity - calculate relevance_window from urgency_score if missing
        # CRITICAL: Normalize urgency_score to 0-1 scale (prevent 0-10 scale corruption)
        urgency_score = normalized.get("urgency_score")
        if urgency_score is None:
            urgency_score = 0.0
            normalized["urgency_score"] = 0.0
        else:
            # Ensure it's a float
            try:
                urgency_score = float(urgency_score)
                # If it's in 0-10 scale, convert to 0-1
                if urgency_score > 1.0:
                    urgency_score = min(1.0, urgency_score / 10.0)
                # Ensure it's in 0-1 range
                normalized["urgency_score"] = max(0.0, min(1.0, urgency_score))
            except (ValueError, TypeError):
                urgency_score = 0.0
                normalized["urgency_score"] = 0.0

        # Calculate relevance_window from urgency_score if missing (don't override existing analysis)
        # Only calculate if truly missing (None or empty string), not if it's already set
        current_window = normalized.get("relevance_window")
        if not current_window or current_window == "":
            # Calculate from urgency_score using the same logic as analysis_components.py
            if urgency_score >= 0.7:
                normalized["relevance_window"] = "same-day"
            elif urgency_score >= 0.45:
                normalized["relevance_window"] = "24-72h"
            elif urgency_score >= 0.35:
                normalized["relevance_window"] = "this-week"
            else:
                normalized["relevance_window"] = "evergreen"
        # If relevance_window exists but urgency_score suggests it might be wrong, recalculate
        # (only if urgency_score > 0.35 and window is "evergreen" - likely wrong)
        elif current_window == "evergreen" and urgency_score >= 0.35:
            # Recalculate if urgency suggests it should be more urgent
            if urgency_score >= 0.7:
                normalized["relevance_window"] = "same-day"
            elif urgency_score >= 0.45:
                normalized["relevance_window"] = "24-72h"
            else:
                normalized["relevance_window"] = "this-week"

        if normalized.get("time_sensitive_reasons") is None:
            normalized["time_sensitive_reasons"] = []

        # analyzed_at is already normalized above (line 1033-1062)

        return normalized
