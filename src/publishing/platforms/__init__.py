"""Platform-specific posting modules."""

# Make imports optional to avoid breaking if dependencies are missing
try:
    from src.domain.publishing.platforms.twitter import TwitterPoster, post_to_twitter_direct

    twitter_poster = TwitterPoster  # type: ignore
    twitter_post_direct = post_to_twitter_direct  # type: ignore
except ImportError:
    logger.error(f"Error: {e}")
    twitter_poster = None
    twitter_post_direct = None

try:
    from src.domain.publishing.platforms.threads import ThreadsPoster, post_to_threads_direct

    threads_poster = ThreadsPoster  # type: ignore
    threads_post_direct = post_to_threads_direct  # type: ignore
except ImportError:
    logger.error(f"Error: {e}")
    threads_poster = None
    threads_post_direct = None

# Export the snake_case variables that are actually available
__all__ = [
    "twitter_poster",
    "twitter_post_direct",
    "threads_poster",
    "threads_post_direct",
    # Keep original names for backward compatibility if needed
    "TwitterPoster",
    "post_to_twitter_direct",
    "ThreadsPoster",
    "post_to_threads_direct",
]
