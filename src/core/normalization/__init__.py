"""
Content normalization package for PrisMind.

This package handles normalization of content from various sources
into a consistent format using tools like MarkItDown.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict


class ContentNormalizer(ABC):
    """Abstract base class for content normalizers."""
    
    @abstractmethod
    def normalize(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize content to a standard format.
        
        Args:
            content: Dictionary containing raw content data
            
        Returns:
            Dictionary with normalized content
        """
        pass


def get_normalizer(normalizer_type: str) -> ContentNormalizer:
    """
    Factory function to get a normalizer instance.
    
    Args:
        normalizer_type: Type of normalizer to create
        
    Returns:
        ContentNormalizer instance
    """
    if normalizer_type == "markitdown":
        from src.core.normalization.markitdown_normalizer import MarkItDownNormalizer
        return MarkItDownNormalizer()
    else:
        raise ValueError(f"Unknown normalizer type: {normalizer_type}")


# For backward compatibility
from src.core.normalization.markitdown_normalizer import MarkItDownNormalizer, get_markitdown_normalizer