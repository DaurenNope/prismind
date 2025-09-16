"""
Post analysis module for the sync script.
Handles AI analysis of posts using the ContentAnalyzer.
"""
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def analyze_post(post_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze a single post using ContentAnalyzer.
    
    Args:
        post_data: Dictionary containing post data
        
    Returns:
        Dictionary with analysis results
    """
    try:
        # Import here to avoid circular imports
        from src.core.analysis.content_analyzer import ContentAnalyzer
        
        # Initialize the analyzer
        analyzer = ContentAnalyzer()
        
        # Determine content type based on platform
        platform = post_data.get('platform', '').lower()
        content_type = platform if platform in ['reddit', 'twitter'] else 'generic'
        
        # Extract content fields
        content = {
            'title': post_data.get('title', ''),
            'content': post_data.get('content', ''),
            'url': post_data.get('url', ''),
            'platform': platform,
            'author': post_data.get('author', '')
        }
        
        # Add platform-specific fields
        if platform == 'reddit':
            content.update({
                'selftext': post_data.get('content', ''),
                'subreddit': post_data.get('subcategory', '')
            })
        
        # Perform analysis
        analysis = analyzer.analyze_content(content_type, content)
        
        # Map analysis results to our database fields
        result = {
            'ai_summary': analysis.get('summary', ''),
            'key_concepts': json.dumps(analysis.get('key_topics', [])),
            'sentiment': analysis.get('sentiment', 'neutral'),
            'category': analysis.get('category', 'general'),
            'tags': json.dumps(analysis.get('tags', [])),
            'analyzed_at': datetime.utcnow().isoformat(),
            'analysis_model': analysis.get('model_used', 'unknown')
        }
        
        return result
        
    except ImportError as e:
        logger.warning(f"Could not import ContentAnalyzer: {e}")
        return {}
    except Exception as e:
        logger.error(f"Error analyzing post: {e}")
        return {}

def should_analyze_post(post_data: Dict[str, Any]) -> bool:
    """
    Determine if a post should be analyzed.
    
    Args:
        post_data: Dictionary containing post data
        
    Returns:
        bool: True if the post should be analyzed, False otherwise
    """
    # Skip if already analyzed recently
    if post_data.get('analyzed_at'):
        try:
            analyzed_at = datetime.fromisoformat(post_data['analyzed_at'])
            if (datetime.utcnow() - analyzed_at).days < 30:  # Re-analyze after 30 days
                return False
        except (ValueError, TypeError):
            pass
    
    # Skip if content is too short
    content = post_data.get('content', '')
    if len(content) < 50:  # Minimum 50 characters for meaningful analysis
        return False
        
    return True
