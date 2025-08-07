from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class SocialPost:
    """Standard format for social media posts"""
    platform: str
    post_id: str
    author: str
    author_handle: str
    content: str
    created_at: datetime
    url: str
    post_type: str  # tweet, post, comment, message
    media_urls: List[str] = field(default_factory=list)
    hashtags: List[str] = field(default_factory=list)
    mentions: List[str] = field(default_factory=list)
    engagement: Dict = field(default_factory=dict)
    is_saved: bool = True
    saved_at: Optional[datetime] = None
    folder_category: Optional[str] = None
    analysis: Optional[Dict] = None # To hold the analysis results

class SocialExtractorBase(ABC):
    """Base class for all social media extractors"""
    
    def __init__(self, api_key: str = None, access_token: str = None):
        self.api_key = api_key
        self.access_token = access_token
        self.platform_name = self.__class__.__name__.replace('Extractor', '').lower()
    
    @abstractmethod
    def authenticate(self) -> bool:
        """Authenticate with the platform"""
        pass
    
    @abstractmethod
    def get_saved_posts(self, limit: int = 100) -> List[SocialPost]:
        """Get saved/bookmarked posts from the platform"""
        pass
    
    @abstractmethod
    def get_liked_posts(self, limit: int = 100) -> List[SocialPost]:
        """Get liked posts from the platform"""
        pass
    
    def validate_credentials(self) -> bool:
        """Check if credentials are valid"""
        try:
            return self.authenticate()
        except Exception as e:
            print(f"❌ {self.platform_name} authentication failed: {e}")
            return False
    
    def format_post_for_analysis(self, post: SocialPost) -> Dict:
        """Format post data for AI analysis"""
        return {
            'platform': post.platform,
            'title': f"{post.author} on {post.platform}",
            'content': post.content,
            'author': post.author,
            'url': post.url,
            'created_at': post.created_at.isoformat(),
            'hashtags': post.hashtags,
            'mentions': post.mentions,
            'media_count': len(post.media_urls),
            'engagement': post.engagement
        } 