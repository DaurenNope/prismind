"""
BEYONDLINES Content Collection Module

This module provides universal content collection capabilities for scraping
any website, social media platform, or web application.
"""

from .universal_collector import (
    CollectionResult,
    CollectionStrategy,
    ContentType,
    ScrapingConfig,
    UniversalCollector,
)

__all__ = [
    "UniversalCollector",
    "CollectionStrategy",
    "ContentType",
    "ScrapingConfig",
    "CollectionResult",
]
