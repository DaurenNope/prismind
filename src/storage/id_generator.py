#!/usr/bin/env python3
"""
Post ID Generator - Deterministic ID generation for all platforms.

Ensures consistent, deterministic post IDs instead of random UUIDs.
"""

import hashlib
import re
from typing import Any, Dict, Optional


class PostIDGenerator:
    """Standardized post ID generation across all platforms"""

    @staticmethod
    def generate_post_id(post: Dict[str, Any]) -> str:
        """
        Generate a deterministic post_id based on platform rules:
        - Twitter: twitter_{tweet_id} (from URL or API)
        - Reddit: reddit_{post_id} (from 'name' field or URL)
        - Threads: threads_{post_id} (from URL or API)
        - Fallback: platform_{hash(url+content)} (deterministic, not random)

        Args:
            post: Post dictionary with platform, url, content, post_id fields

        Returns:
            str: Normalized post_id in format platform_{id}
        """
        platform = post.get("platform", "").lower()
        existing_id = post.get("post_id")

        # If already has post_id, normalize it
        if existing_id:
            return PostIDGenerator._normalize_id(str(existing_id), platform)

        # Try to extract from URL
        url = post.get("url", "")
        if url:
            extracted = PostIDGenerator._extract_id_from_url(url, platform)
            if extracted:
                return f"{platform}_{extracted}"

        # Fallback: deterministic hash (NOT random UUID)
        # Use URL + first 100 chars of content for hash
        content = post.get("content", "")[:100] if post.get("content") else ""
        hash_input = f"{url}{content}".encode("utf-8")
        # Use MD5 hash and take first 12 chars (deterministic)
        url_hash = hashlib.md5(hash_input).hexdigest()[:12]
        return f"{platform}_{url_hash}"

    @staticmethod
    def _extract_id_from_url(url: str, platform: str) -> Optional[str]:
        """Extract platform-specific ID from URL"""
        if not url:
            return None

        # Twitter: https://x.com/user/status/1234567890 or https://twitter.com/user/status/1234567890
        if platform == "twitter":
            # Match /status/ followed by digits
            match = re.search(r"/status/(\d+)", url)
            if match:
                return match.group(1)
            # Also try x.com
            match = re.search(r"x\.com/[^/]+/status/(\d+)", url)
            if match:
                return match.group(1)

        # Reddit: https://reddit.com/r/sub/comments/abc123/title or https://www.reddit.com/r/sub/comments/abc123/title
        if platform == "reddit":
            # Match /comments/ followed by alphanumeric ID
            match = re.search(r"/comments/([a-zA-Z0-9]+)", url)
            if match:
                return match.group(1)
            # Also check for t3_ prefix in URL
            match = re.search(r"t3_([a-zA-Z0-9]+)", url)
            if match:
                return match.group(1)

        # Threads: https://threads.net/@user/post/1234567890
        if platform == "threads":
            match = re.search(r"/post/(\d+)", url)
            if match:
                return match.group(1)

        # Try generic: last part of URL path
        try:
            # Remove query params and fragments
            clean_url = url.split("?")[0].split("#")[0]
            # Get last segment
            parts = [p for p in clean_url.rstrip("/").split("/") if p]
            if parts:
                last_part = parts[-1]
                # If it looks like an ID (alphanumeric, reasonable length)
                if re.match(r"^[a-zA-Z0-9_-]{3,50}$", last_part):
                    return last_part
        except Exception as e:
            logger.error(f"Error: {e}")
            pass

        return None

    @staticmethod
    def _normalize_id(post_id: str, platform: str) -> str:
        """
        Normalize post_id format (remove duplicate prefixes).

        Examples:
        - twitter_123456 -> twitter_123456 (already normalized)
        - Twitter_123456 -> twitter_123456 (normalize case)
        - 123456 (platform=twitter) -> twitter_123456 (add prefix)
        - twitter_twitter_123456 -> twitter_123456 (remove duplicate)
        """
        if not post_id:
            return f"{platform}_unknown"

        post_id = str(post_id).strip()
        platform_lower = platform.lower()
        prefix = f"{platform_lower}_"

        # Remove duplicate prefixes
        while post_id.lower().startswith(prefix):
            post_id = post_id[len(prefix) :]

        # Add platform prefix if missing
        if not post_id.lower().startswith(platform_lower):
            return f"{prefix}{post_id}"

        # Ensure lowercase platform prefix
        if post_id.startswith(platform):  # e.g., "Twitter_" instead of "twitter_"
            return f"{prefix}{post_id[len(platform):].lstrip('_')}"

        return post_id
