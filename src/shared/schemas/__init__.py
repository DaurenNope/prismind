"""
BEYONDLINES Data Schemas Module
=============================

Standardized data structures for type-safe communication between components.
"""

from .analyzed_content import (  # Rewrite system; Discovery system; Timing system; Vision analysis; Main contract; User learning; Knowledge graph; Publishing; Helper functions
    AnalyzedContent,
    Concept,
    ConceptConnection,
    ContentFreshness,
    ContentPreferences,
    DiscoverySignals,
    MediaInsight,
    PublishedPost,
    RewriteAngle,
    UserInterest,
    UserProfile,
    WritingStyle,
    get_rewrite_angle,
    validate_analyzed_content,
)

__all__ = [
    # Rewrite
    "RewriteAngle",
    # Discovery
    "DiscoverySignals",
    # Timing
    "ContentFreshness",
    # Vision
    "MediaInsight",
    # Main
    "AnalyzedContent",
    # User
    "UserProfile",
    "UserInterest",
    "ContentPreferences",
    "WritingStyle",
    # Concepts
    "Concept",
    "ConceptConnection",
    # Publishing
    "PublishedPost",
    # Helpers
    "validate_analyzed_content",
    "get_rewrite_angle",
]
