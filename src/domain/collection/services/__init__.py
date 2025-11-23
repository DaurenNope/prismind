"""
Collection service module for platform-specific collectors
This is a PACKAGE (collection/ directory)
"""
from src.domain.collection.services.platform_collectors import (
    collect_reddit_bookmarks,
    collect_threads_bookmarks,
    collect_twitter_bookmarks,
)

__all__ = [
    "collect_twitter_bookmarks",
    "collect_reddit_bookmarks",
    "collect_threads_bookmarks",
]
