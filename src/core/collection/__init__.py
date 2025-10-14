"""
PrisMind Content Collection Module

This module provides universal content collection capabilities for scraping
any website, social media platform, or web application.
"""

from .universal_collector import (
    UniversalCollector,
    CollectionStrategy,
    ContentType,
    ScrapingConfig,
    CollectionResult
)

__all__ = [
    'UniversalCollector',
    'CollectionStrategy', 
    'ContentType',
    'ScrapingConfig',
    'CollectionResult'
]
