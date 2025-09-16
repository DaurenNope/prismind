"""
Content Analyzer for processing social media posts with local Ollama models
"""
import json
import logging
from typing import Dict, List, Any, Optional
import requests
from datetime import datetime
import os

logger = logging.getLogger(__name__)

class ContentAnalyzer:
    """Analyze social media content using local Ollama models"""
    
    def __init__(self, model: str = None, base_url: str = None):
        """Initialize the content analyzer with Ollama settings"""
        self.base_url = base_url or os.getenv('OLLAMA_URL', 'http://localhost:11434')
        self.model = model or os.getenv('OLLAMA_MODEL', 'mistral')
        
    def analyze_content(self, content_type: str, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze content using Ollama
        
        Args:
            content_type: Type of content ('reddit', 'twitter', etc.)
            content: Dictionary containing the content to analyze
            
        Returns:
            Dictionary with analysis results (summary, tags, categories, etc.)
        """
        try:
            # Prepare the prompt based on content type
            if content_type == 'reddit':
                prompt = self._prepare_reddit_prompt(content)
            elif content_type == 'twitter':
                prompt = self._prepare_twitter_prompt(content)
            else:
                prompt = self._prepare_generic_prompt(content)
            
            # Call Ollama API
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "max_tokens": 1000
                    }
                }
            )
            response.raise_for_status()
            
            # Parse the response
            result = response.json()
            analysis = json.loads(result.get('response', '{}'))
            
            # Add metadata
            analysis.update({
                'analyzed_at': datetime.utcnow().isoformat(),
                'model_used': self.model,
                'content_type': content_type
            })
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing content: {str(e)}")
            return {
                'error': str(e),
                'summary': "",
                'tags': [],
                'category': 'general',
                'analyzed_at': datetime.utcnow().isoformat(),
                'model_used': self.model,
                'content_type': content_type
            }
    
    def _prepare_reddit_prompt(self, post: Dict[str, Any]) -> str:
        """Prepare prompt for Reddit post analysis"""
        title = post.get('title', '')
        text = post.get('selftext', '')
        subreddit = post.get('subreddit', 'unknown')
        
        return f"""Analyze this Reddit post and provide a JSON response with the following fields:
1. summary: A concise 2-3 sentence summary
2. tags: 3-5 relevant tags as a list
3. category: The main category (one word)
4. sentiment: Overall sentiment (positive, negative, neutral)
5. key_topics: List of key topics discussed

Post details:
- Title: {title}
- Subreddit: {subreddit}
- Content: {text[:2000]}

Respond with valid JSON only, no markdown formatting."""
    
    def _prepare_twitter_prompt(self, tweet: Dict[str, Any]) -> str:
        """Prepare prompt for Twitter post analysis"""
        text = tweet.get('text', '')
        username = tweet.get('user', {}).get('screen_name', 'unknown')
        
        return f"""Analyze this Tweet and provide a JSON response with the following fields:
1. summary: A concise 1-2 sentence summary
2. tags: 3-5 relevant tags as a list
3. category: The main category (one word)
4. sentiment: Overall sentiment (positive, negative, neutral)
5. key_topics: List of key topics discussed

Tweet details:
- User: @{username}
- Content: {text}

Respond with valid JSON only, no markdown formatting."""
    
    def _prepare_generic_prompt(self, content: Dict[str, Any]) -> str:
        """Prepare prompt for generic content analysis"""
        text = content.get('text', '') or content.get('content', '')
        title = content.get('title', '')
        
        return f"""Analyze this content and provide a JSON response with the following fields:
1. summary: A concise 2-3 sentence summary
2. tags: 3-5 relevant tags as a list
3. category: The main category (one word)
4. sentiment: Overall sentiment (positive, negative, neutral)
5. key_topics: List of key topics discussed

Content:
Title: {title}
Text: {text[:2000]}

Respond with valid JSON only, no markdown formatting."""
