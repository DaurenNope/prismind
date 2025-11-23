#!/usr/bin/env python3
"""
Post Validator - Ensures only quality data reaches the database
Prevents broken/failed posts from being saved
"""

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ValidationResult:
    """Result of post validation"""

    is_valid: bool
    errors: List[str]
    warnings: List[str]

    def __bool__(self):
        return self.is_valid


class PostValidator:
    """
    Validates post data before saving to database or Supabase

    Ensures:
    - Content is real (not error messages)
    - Authors are real (not placeholders)
    - Required fields present
    - Data quality standards met
    """

    # Patterns that indicate broken/failed posts
    FAILED_CONTENT_PATTERNS = [
        r"scraping failed",
        r"extraction failed",
        r"post from.*failed",
        r"could not extract",
        r"error extracting",
        r"failed to scrape",
    ]

    # Placeholder/fake author names
    PLACEHOLDER_AUTHORS = [
        "threads user",
        "unknown author",
        "twitter user",
        "reddit user",
        "unknown",
        "n/a",
    ]

    # Placeholder handles
    PLACEHOLDER_HANDLES = [
        "threads_user",
        "unknown",
        "unknown_user",
        "na",
    ]

    # Minimum content length (characters)
    MIN_CONTENT_LENGTH = 10

    # Minimum author name length
    MIN_AUTHOR_LENGTH = 2

    def __init__(self, strict: bool = True):
        """
        Initialize validator

        Args:
            strict: If True, apply strict validation rules
        """
        self.strict = strict

    def validate_post(self, post_data: Dict[str, Any]) -> ValidationResult:
        """
        Validate a post before saving

        Args:
            post_data: Post dictionary

        Returns:
            ValidationResult with validation status and any errors/warnings
        """
        errors = []
        warnings = []

        # Normalize author early (strip zero-width, fallback to handle/username)
        try:
            zero_width = str.maketrans(
                {
                    "\u200b": None,  # ZERO WIDTH SPACE
                    "\u200c": None,  # ZERO WIDTH NON-JOINER
                    "\u200d": None,  # ZERO WIDTH JOINER
                    "\ufeff": None,  # ZERO WIDTH NO-BREAK SPACE
                    "\u2060": None,  # WORD JOINER
                    "\u00a0": " ",  # NO-BREAK SPACE → space
                }
            )
        except Exception as e:
            logger.error(f"Error: {e}")
            zero_width = None

        def _clean(s: Optional[str]) -> str:
            if not s:
                return ""
            s2 = s.translate(zero_width) if zero_width else s
            return s2.strip()

        author_raw = post_data.get("author")
        handle_raw = post_data.get("author_handle") or post_data.get("username")
        cleaned_author = _clean(author_raw)
        if not cleaned_author or len(cleaned_author.strip()) < self.MIN_AUTHOR_LENGTH:
            # Try handle as fallback
            cleaned_handle = _clean(handle_raw)
            if cleaned_handle and len(cleaned_handle.strip()) >= self.MIN_AUTHOR_LENGTH:
                cleaned_author = cleaned_handle
            else:
                # Try extracting from URL
                url = post_data.get("url", "")
                if url and "@" in url:
                    # Extract handle from URL (e.g., threads.net/@username/post/123)
                    try:
                        url_parts = url.split("@")
                        if len(url_parts) > 1:
                            potential_handle = url_parts[1].split("/")[0].strip()
                            if (
                                potential_handle
                                and len(potential_handle) >= self.MIN_AUTHOR_LENGTH
                            ):
                                cleaned_author = potential_handle
                    except (IndexError, AttributeError) as e:
                        pass

                # Last resort: use post_id or generate fallback
                if (
                    not cleaned_author
                    or len(cleaned_author.strip()) < self.MIN_AUTHOR_LENGTH
                ):
                    post_id = (
                        post_data.get("post_id", "")[:20]
                        if post_data.get("post_id")
                        else ""
                    )
                    if post_id:
                        cleaned_author = f"threads_user_{post_id}"
                    else:
                        cleaned_author = "threads_user"

        post_data["author"] = cleaned_author

        # Required fields check
        required_fields = ["content", "author", "platform", "url"]
        for field in required_fields:
            if field not in post_data or not post_data[field]:
                errors.append(f"Missing required field: {field}")

        # If missing required fields, fail immediately
        if errors:
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings)

        # Validate content
        content_valid, content_errors = self._validate_content(
            post_data.get("content", "")
        )
        errors.extend(content_errors)

        # Validate author
        author_valid, author_errors = self._validate_author(
            post_data.get("author", ""), post_data.get("author_handle", "")
        )
        errors.extend(author_errors)

        # Validate platform
        platform_valid, platform_errors = self._validate_platform(
            post_data.get("platform", "")
        )
        errors.extend(platform_errors)

        # Check for suspicious patterns
        suspicious_warnings = self._check_suspicious_patterns(post_data)
        warnings.extend(suspicious_warnings)

        # Validate URL
        url_valid, url_errors = self._validate_url(post_data.get("url", ""))
        if not url_valid:
            warnings.extend(url_errors)  # URL issues are warnings, not errors

        # Determine if valid
        is_valid = len(errors) == 0

        return ValidationResult(is_valid=is_valid, errors=errors, warnings=warnings)

    def _validate_content(self, content: str) -> Tuple[bool, List[str]]:
        """Validate post content"""
        errors = []

        if not content:
            errors.append("Content is empty")
            return False, errors

        content_lower = content.lower()

        # Check for failed scraping indicators
        for pattern in self.FAILED_CONTENT_PATTERNS:
            if re.search(pattern, content_lower):
                errors.append(f"Content indicates failed scraping: '{pattern}'")
                return False, errors

        # Check minimum length
        if len(content.strip()) < self.MIN_CONTENT_LENGTH:
            errors.append(
                f"Content too short ({len(content)} chars, minimum {self.MIN_CONTENT_LENGTH})"
            )
            return False, errors

        # Check if content is just repeated words (username spam)
        words = content.split()
        if len(words) >= 3:
            # If first word repeats 3+ times, it's probably spam
            first_word = words[0].lower()
            repeat_count = sum(1 for w in words[:5] if w.lower() == first_word)
            if repeat_count >= 3:
                errors.append(
                    f"Content appears to be repeated username spam: '{first_word}'"
                )
                return False, errors

        return True, []

    def _validate_author(self, author: str, handle: str) -> Tuple[bool, List[str]]:
        """Validate author information"""
        errors = []

        if not author:
            errors.append("Author is empty")
            return False, errors

        author_lower = author.lower().strip()

        # Check for placeholder authors
        if author_lower in self.PLACEHOLDER_AUTHORS:
            errors.append(f"Author is placeholder: '{author}'")
            return False, errors

        # Check minimum length
        if len(author.strip()) < self.MIN_AUTHOR_LENGTH:
            errors.append(f"Author name too short: '{author}'")
            return False, errors

        # Check for placeholder handles
        if handle:
            handle_lower = handle.lower().strip()
            if handle_lower in self.PLACEHOLDER_HANDLES:
                errors.append(f"Author handle is placeholder: '{handle}'")
                return False, errors

        return True, []

    def _validate_platform(self, platform: str) -> Tuple[bool, List[str]]:
        """Validate platform"""
        errors = []

        if not platform:
            errors.append("Platform is empty")
            return False, errors

        valid_platforms = [
            "threads",
            "twitter",
            "reddit",
            "github",
            "telegram",
            "rss",
            "discovery",
        ]
        if platform.lower() not in valid_platforms:
            errors.append(f"Unknown platform: '{platform}'")
            return False, errors

        return True, []

    def _validate_url(self, url: str) -> Tuple[bool, List[str]]:
        """Validate URL"""
        errors = []

        if not url:
            errors.append("URL is empty")
            return False, errors

        # Basic URL check
        if not url.startswith(("http://", "https://")):
            errors.append(f"Invalid URL format: '{url}'")
            return False, errors

        return True, []

    def _check_suspicious_patterns(self, post_data: Dict[str, Any]) -> List[str]:
        """Check for suspicious patterns that might indicate bad data"""
        warnings = []

        content = post_data.get("content", "")
        author = post_data.get("author", "")

        # Check if author name appears in content multiple times (might be spam)
        if author and content:
            author_count = content.lower().count(author.lower())
            if author_count >= 3:
                warnings.append(f"Author name appears {author_count} times in content")

        # Check if content is mostly URLs
        if content:
            url_count = len(re.findall(r"https?://", content))
            if url_count >= 5:
                warnings.append(f"Content has {url_count} URLs (might be spam)")

        # Check for suspiciously short posts with no substance
        if content and len(content.split()) <= 2:
            warnings.append("Post is very short (2 words or less)")

        return warnings

    def validate_batch(
        self, posts: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Validate a batch of posts

        Args:
            posts: List of post dictionaries

        Returns:
            Tuple of (valid_posts, invalid_posts_with_reasons)
        """
        valid_posts = []
        invalid_posts = []

        for post in posts:
            result = self.validate_post(post)

            if result.is_valid:
                valid_posts.append(post)
            else:
                # Add validation errors to post for logging
                post_with_errors = post.copy()
                post_with_errors["_validation_errors"] = result.errors
                post_with_errors["_validation_warnings"] = result.warnings
                invalid_posts.append(post_with_errors)

        return valid_posts, invalid_posts


# Singleton instance
_validator_instance: Optional[PostValidator] = None


def get_validator(strict: bool = True) -> PostValidator:
    """Get or create validator instance"""
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = PostValidator(strict=strict)
    return _validator_instance


def validate_post(post_data: Dict[str, Any], strict: bool = True) -> ValidationResult:
    """
    Quick validation function

    Args:
        post_data: Post dictionary
        strict: Use strict validation rules

    Returns:
        ValidationResult
    """
    validator = get_validator(strict=strict)
    return validator.validate_post(post_data)
