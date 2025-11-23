"""
Collection Domain

This domain handles all content collection from various platforms.
"""

from .universal_collector import UniversalCollector
from .services.unified_collection_service import CollectionResult

__all__ = [
    "UniversalCollector",
    "CollectionResult",
]
