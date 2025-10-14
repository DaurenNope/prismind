"""
MarkItDown-based content normalizer for PrisMind.

This module provides functionality to normalize content from various sources
into clean Markdown format using the MarkItDown library.
"""

import logging
from typing import Any, Dict, Optional
import io
import sys

logger = logging.getLogger(__name__)


class MarkItDownNormalizer:
    """Normalizer using MarkItDown to convert HTML/PDF/web content to clean Markdown."""
    
    def __init__(self):
        """Initialize the MarkItDown normalizer."""
        self.markitdown = None
        try:
            # Check Python version - MarkItDown requires Python 3.10+
            if sys.version_info < (3, 10):
                logger.warning(f"MarkItDown requires Python 3.10+, current version is {sys.version_info}")
                logger.warning("Content normalization will be limited without MarkItDown")
                return
                
            from markitdown import MarkItDown
            self.markitdown = MarkItDown()
            logger.info("MarkItDown normalizer initialized successfully")
        except ImportError as e:
            logger.warning(f"MarkItDown not available: {e}")
            logger.warning("To install MarkItDown, you need Python 3.10+ and run: pip install 'markitdown[all]'")
        except Exception as e:
            logger.error(f"Failed to initialize MarkItDown: {e}")
    
    def is_available(self) -> bool:
        """
        Check if MarkItDown is available.
        
        Returns:
            bool: True if MarkItDown is available, False otherwise
        """
        return self.markitdown is not None
    
    def normalize_content(self, content: str, source_url: Optional[str] = None) -> str:
        """
        Normalize content using MarkItDown.
        
        Args:
            content: Raw content to normalize (HTML, text, etc.)
            source_url: Optional source URL for better processing
            
        Returns:
            str: Normalized content in Markdown format
        """
        if not self.is_available():
            logger.warning("MarkItDown not available. Returning original content.")
            # For HTML content, we can do basic processing
            return self._basic_html_to_text(content)
            
        if not content:
            return content
            
        try:
            # Convert content to Markdown
            # For HTML content, we need to encode it to bytes and use convert_stream
            content_bytes = content.encode('utf-8')
            result = self.markitdown.convert_stream(io.BytesIO(content_bytes), url=source_url, file_extension=".html")
            return result.text_content if result.text_content else content
        except Exception as e:
            logger.warning(f"Failed to normalize content with MarkItDown: {e}")
            return content
    
    def _basic_html_to_text(self, html_content: str) -> str:
        """
        Basic HTML to text conversion when MarkItDown is not available.
        
        Args:
            html_content: HTML content to convert
            
        Returns:
            str: Simplified text content
        """
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            return soup.get_text(separator=' ', strip=True)
        except ImportError:
            # If BeautifulSoup is not available, do very basic processing
            import re
            # Remove HTML tags
            clean = re.compile('<.*?>')
            text = re.sub(clean, '', html_content)
            # Normalize whitespace
            text = re.sub(r'\s+', ' ', text).strip()
            return text
        except Exception as e:
            logger.warning(f"Failed to perform basic HTML to text conversion: {e}")
            return html_content
    
    def normalize_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize a content item using MarkItDown.
        
        Args:
            item: Dictionary containing content data
            
        Returns:
            Dict[str, Any]: Item with normalized content
        """
        if not item:
            return item
            
        normalized_item = item.copy()
        
        # Fields that typically contain HTML content that should be normalized
        content_fields = [
            'content', 
            'text', 
            'full_text', 
            'html_content', 
            'description',
            'body'
        ]
        
        source_url = item.get('url') or item.get('source_url')
        
        # Normalize each content field
        for field in content_fields:
            if field in normalized_item and normalized_item[field]:
                try:
                    original_content = normalized_item[field]
                    normalized_content = self.normalize_content(original_content, source_url)
                    normalized_item[field] = normalized_content
                    
                    if original_content != normalized_content:
                        logger.debug(f"Normalized content in field '{field}'")
                        
                except Exception as e:
                    logger.warning(f"Failed to normalize field '{field}': {e}")
        
        return normalized_item


# Singleton instance
_markitdown_normalizer: Optional[MarkItDownNormalizer] = None


def get_markitdown_normalizer() -> MarkItDownNormalizer:
    """
    Get singleton instance of MarkItDownNormalizer.
    
    Returns:
        MarkItDownNormalizer: Singleton instance
    """
    global _markitdown_normalizer
    if _markitdown_normalizer is None:
        _markitdown_normalizer = MarkItDownNormalizer()
    return _markitdown_normalizer