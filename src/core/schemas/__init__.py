"""
PrisMind Data Schemas Module
=============================

Standardized data structures for type-safe communication between components.
"""

from .analyzed_content import (
    # Rewrite system
    RewriteAngle,

    # Discovery system
    DiscoverySignals,

    # Timing system
    ContentFreshness,

    # Vision analysis
    MediaInsight,

    # Main contract
    AnalyzedContent,

    # User learning
    UserProfile,
    UserInterest,
    ContentPreferences,
    WritingStyle,

    # Knowledge graph
    Concept,
    ConceptConnection,

    # Publishing
    PublishedPost,

    # Helper functions
    validate_analyzed_content,
    get_rewrite_angle,
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
