#!/usr/bin/env python3
import logging

logger = logging.getLogger(__name__)
"""
Telegram Formatting Utilities
Enhanced post formatting with GitHub metadata
"""

from typing import Any, Dict

from src.utils.github_metadata import format_github_display, get_github_metadata


def _get_field(post: Any, field: str, default: Any = None) -> Any:
    """Get a field from either a dict-like or object-like post."""
    if isinstance(post, dict):
        return post.get(field, default)
    return getattr(post, field, default)


def format_post_for_telegram(post: Any, index: int = 1) -> str:
    """
    Format a post for Telegram display with enhanced GitHub support

    Args:
        post: Post object
        index: Post number

    Returns:
        Formatted string for Telegram
    """
    # Get basic info (support dicts and objects)
    platform_raw = str(
        _get_field(post, "platform", None)
        or _get_field(post, "source", None)
        or "unknown"
    )
    platform = platform_raw.title()
    author = (
        _get_field(post, "author", None)
        or _get_field(post, "author_handle", None)
        or _get_field(post, "username", None)
        or _get_field(post, "channel_title", None)
        or "Unknown"
    )
    # Prefer summaries/title if content missing
    content = (
        _get_field(post, "content", None)
        or _get_field(post, "content_summary", None)
        or _get_field(post, "ai_summary", None)
        or _get_field(post, "summary", None)
        or _get_field(post, "title", None)
        or "No content"
    )
    url = _get_field(post, "url", "") or ""
    quality = _get_field(post, "quality_score", _get_field(post, "value_score", None))

    # Platform emoji
    emoji = {"twitter": "🐦", "reddit": "🤖", "github": "🛠️", "rss": "📰", "web": "🌐"}.get(
        platform_raw.lower(), "📄"
    )

    # Check if this is a GitHub URL
    if url and "github.com" in url:
        return format_github_post(post, index)

    # Standard post format
    lines = [
        f"{index}. {emoji} {platform} • {author}",
    ]

    # Add content (truncated)
    if isinstance(content, str) and content.strip():
        lines.append(f"   {content[:150].strip()}...")

    # Add quality score if available
    if isinstance(quality, (int, float)):
        try:
            # Normalize stars: handle 0-1 or 0-5 ranges
            score_for_stars = quality if quality <= 5 else min(quality / 20.0, 5)
            if score_for_stars <= 1:
                stars = "⭐" * max(1, int(score_for_stars * 5))
            else:
                stars = "⭐" * min(int(score_for_stars), 5)
            lines.append(f"   {stars} Quality: {float(quality):.2f}")
        except Exception as e:
            logger.error(f"Error: {e}")
            pass

    # Add URL
    if url:
        lines.append(f"   🔗 {url}")

    return "\n".join(lines)


def format_github_post(post: Any, index: int = 1) -> str:
    """
    Format GitHub repository post with rich metadata

    Args:
        post: Post object with GitHub URL
        index: Post number

    Returns:
        Formatted string for Telegram
    """
    url = _get_field(post, "url", "") or ""

    # Fetch GitHub metadata
    try:
        metadata = get_github_metadata(url, timeout=3)

        # Format for Telegram
        lines = [
            f"{index}. 🛠️  **{metadata['full_name']}**",
            f"   ⭐ {metadata['stars']:,} stars | {metadata['language']}",
            "",
            f"   {metadata['description'][:120]}...",
            "",
            f"   **Category:** {metadata['category']}",
        ]

        # Add topics if available
        if metadata.get("topics"):
            topics = ", ".join(metadata["topics"][:3])
            lines.append(f"   **Topics:** {topics}")

        # Add why it matters
        if metadata.get("why_matters"):
            lines.append(f"   💡 {metadata['why_matters']}")

        lines.append(f"   🔗 {url}")

        return "\n".join(lines)

    except Exception as e:
        logger.error(f"Error: {e}")
        # Fallback to standard format if GitHub API fails
        author = _get_field(post, "author", "Unknown") or "Unknown"
        content = (
            _get_field(post, "content", _get_field(post, "title", "GitHub repository"))
            or "GitHub repository"
        )

        return f"{index}. 🛠️  GitHub • {author}\n   {content[:100]}...\n   🔗 {url}"


def format_posts_list(posts: list, start_index: int = 1) -> str:
    """
    Format a list of posts for Telegram

    Args:
        posts: List of post objects
        start_index: Starting index number

    Returns:
        Formatted string with all posts
    """
    if not posts:
        return "No posts found."

    formatted_posts = []
    for i, post in enumerate(posts, start=start_index):
        try:
            formatted = format_post_for_telegram(post, i)
            formatted_posts.append(formatted)
        except Exception as e:
            logger.error(f"Error: {e}")
            # Fallback
            formatted_posts.append(f"{i}. Error formatting post: {str(e)}")

    return "\n\n".join(formatted_posts)


def format_post_stats(posts: list) -> str:
    """
    Generate stats summary for posts

    Args:
        posts: List of posts

    Returns:
        Stats string
    """
    if not posts:
        return "No posts"

    # Count by platform
    from collections import Counter

    def _platform_of(p: Any) -> str:
        if isinstance(p, dict):
            return str(p.get("platform", "unknown") or "unknown")
        return str(getattr(p, "platform", "unknown") or "unknown")

    platforms = Counter([_platform_of(p) for p in posts])

    # Count GitHub repos
    def _url_of(p: Any) -> str:
        if isinstance(p, dict):
            return str(p.get("url", "") or "")
        return str(getattr(p, "url", "") or "")

    github_count = sum(1 for p in posts if "github.com" in _url_of(p))

    # Average quality
    def _quality_of(p: Any):
        if isinstance(p, dict):
            return p.get("quality_score", p.get("value_score", None))
        return getattr(p, "quality_score", getattr(p, "value_score", None))

    qualities = [
        q for q in (_quality_of(p) for p in posts) if isinstance(q, (int, float))
    ]
    avg_quality = sum(qualities) / len(qualities) if qualities else 0

    lines = [
        f"<b>Total:</b> {len(posts)} posts",
    ]

    if platforms:
        platform_str = ", ".join([f"{p}: {c}" for p, c in platforms.most_common(3)])
        lines.append(f"<b>Platforms:</b> {platform_str}")

    if github_count > 0:
        lines.append(f"<b>GitHub Repos:</b> {github_count}")

    if avg_quality > 0:
        lines.append(f"<b>Avg Quality:</b> {avg_quality:.2f}")

    return " | ".join(lines)


def test_formatting():
    """Test formatting functions"""

    logger.info("🧪 Testing Telegram Formatting\n")

    # Mock post object
    class MockPost:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    # Test regular post
    post1 = MockPost(
        platform="twitter",
        author="@elonmusk",
        content="Announcing new feature!",
        url="https://twitter.com/status/123",
        quality_score=0.85,
    )

    logger.info("Regular Post:")
    logger.info(format_post_for_telegram(post1, 1))
    logger.info()

    # Test GitHub post
    post2 = MockPost(
        platform="github",
        author="microsoft",
        content="VS Code",
        url="https://github.com/microsoft/vscode",
        quality_score=0.95,
    )

    logger.info("GitHub Post:")
    logger.info(format_post_for_telegram(post2, 2))
    logger.info()

    # Test list formatting
    logger.info("Posts List:")
    formatted = format_posts_list([post1, post2])
    logger.info(formatted)
    logger.info()

    # Test stats
    logger.info("Stats:")
    logger.info(format_post_stats([post1, post2]))

    logger.info("\n✅ Test complete!")


if __name__ == "__main__":
    test_formatting()
