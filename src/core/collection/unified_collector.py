"""
Unified Collector for social media content with AI analysis
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import os

from ..extraction.reddit_extractor import RedditExtractor
from ..extraction.twitter_extractor_playwright import TwitterExtractorPlaywright
from ..analysis.content_analyzer import ContentAnalyzer
from ..models.social_post import SocialPost

logger = logging.getLogger(__name__)

class UnifiedCollector:
    """Collect and analyze content from multiple social media platforms"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the unified collector with configuration"""
        self.config = config or {}
        self.analyzer = ContentAnalyzer()
        self.extractors = {}
        
        # Initialize extractors based on configuration
        self._initialize_extractors()
    
    def _initialize_extractors(self):
        """Initialize platform-specific extractors"""
        # Initialize Reddit extractor if credentials are available
        if all(k in os.environ for k in ['REDDIT_CLIENT_ID', 'REDDIT_CLIENT_SECRET', 'REDDIT_USERNAME']):
            self.extractors['reddit'] = RedditExtractor(
                client_id=os.environ['REDDIT_CLIENT_ID'],
                client_secret=os.environ['REDDIT_CLIENT_SECRET'],
                user_agent=os.environ.get('REDDIT_USER_AGENT', 'prismind/1.0'),
                username=os.environ['REDDIT_USERNAME'],
                password=os.environ.get('REDDIT_PASSWORD')
            )
        
        # Initialize Twitter extractor if credentials are available
        if all(k in os.environ for k in ['TWITTER_USERNAME']):
            self.extractors['twitter'] = TwitterExtractorPlaywright(
                username=os.environ['TWITTER_USERNAME'],
                password=os.environ.get('TWITTER_PASSWORD')
            )
    
    async def collect_saved_content(self, platform: str = 'all', limit: int = 10) -> List[Dict[str, Any]]:
        """
        Collect saved content from specified platforms
        
        Args:
            platform: Platform to collect from ('reddit', 'twitter', or 'all')
            limit: Maximum number of items to collect per platform
            
        Returns:
            List of collected and analyzed posts
        """
        results = []
        
        # Determine which platforms to process
        platforms = [platform] if platform != 'all' else self.extractors.keys()
        
        for platform_name in platforms:
            if platform_name not in self.extractors:
                logger.warning(f"No extractor configured for platform: {platform_name}")
                continue
                
            try:
                logger.info(f"Collecting saved content from {platform_name}...")
                
                # Get saved posts from the platform
                if platform_name == 'reddit':
                    posts = self.extractors[platform_name].get_saved_posts(limit=limit)
                elif platform_name == 'twitter':
                    # Twitter extractor uses async/await
                    posts = await self.extractors[platform_name].get_saved_tweets(limit=limit)
                else:
                    logger.warning(f"Unsupported platform: {platform_name}")
                    continue
                
                # Analyze each post
                for post in posts:
                    try:
                        # Convert to dict if it's a SocialPost object
                        if hasattr(post, 'to_dict'):
                            post_data = post.to_dict()
                        else:
                            post_data = dict(post)
                        
                        # Analyze the content
                        analysis = self.analyzer.analyze_content(platform_name, post_data)
                        
                        # Combine post data with analysis
                        result = {
                            'platform': platform_name,
                            'source_id': post_data.get('id') or post_data.get('tweet_id', ''),
                            'created_at': post_data.get('created_at') or post_data.get('created_utc', ''),
                            'url': post_data.get('url', ''),
                            'author': post_data.get('author') or post_data.get('user', {}).get('screen_name', ''),
                            'content': {
                                'title': post_data.get('title', ''),
                                'text': post_data.get('text') or post_data.get('selftext', '')
                            },
                            'metrics': {
                                'score': post_data.get('score'),
                                'upvotes': post_data.get('ups'),
                                'downvotes': post_data.get('downs'),
                                'comments': post_data.get('num_comments'),
                                'retweets': post_data.get('retweet_count'),
                                'likes': post_data.get('likes') or post_data.get('favorite_count')
                            },
                            'analysis': analysis
                        }
                        
                        results.append(result)
                        
                    except Exception as e:
                        logger.error(f"Error processing {platform_name} post: {str(e)}", exc_info=True)
                
                logger.info(f"Collected {len(posts)} items from {platform_name}")
                
            except Exception as e:
                logger.error(f"Error collecting from {platform_name}: {str(e)}", exc_info=True)
        
        return results
    
    async def collect_and_analyze_all(self, limit: int = 10) -> Dict[str, Any]:
        """
        Collect and analyze content from all configured platforms
        
        Args:
            limit: Maximum number of items to collect per platform
            
        Returns:
            Dictionary with collected content and analysis
        """
        results = {}
        
        for platform_name, extractor in self.extractors.items():
            try:
                platform_results = await self.collect_saved_content(platform=platform_name, limit=limit)
                results[platform_name] = {
                    'count': len(platform_results),
                    'items': platform_results
                }
            except Exception as e:
                logger.error(f"Error processing {platform_name}: {str(e)}", exc_info=True)
                results[platform_name] = {
                    'error': str(e),
                    'count': 0,
                    'items': []
                }
        
        # Generate overall summary
        total_items = sum(len(data.get('items', [])) for data in results.values())
        
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'total_items': total_items,
            'platforms': results
        }
