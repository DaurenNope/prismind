import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class SocialPost:
    """Standard format for social media posts"""

    platform: str
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
    folder_category: Optional[str] = None
    analysis: Optional[Dict] = None  # To hold the analysis results
    id: Optional[str] = None  # Optional internal id used by some tests
    post_id: Optional[str] = None  # Optional; will default from id if not provided

    def __post_init__(self):
        # Backwards-compat: if post_id not provided but id is, mirror it
        if self.post_id is None and self.id is not None:
            self.post_id = self.id

    def to_dict(self) -> Dict:
        """Convert SocialPost to dictionary format for database insertion"""
        from dataclasses import asdict

        data = asdict(self)

        # Map platform to source field for database compatibility
        data["source"] = self.platform

        # Ensure proper datetime formatting
        if isinstance(self.created_at, datetime):
            data["created_at"] = self.created_at.isoformat()

        # Map fields for database schema compatibility
        # Create a meaningful title from content (first 100 chars or first line)
        if self.content:
            # Take first line or first 100 chars, whichever is shorter
            first_line = self.content.split("\n")[0]
            data["title"] = (
                first_line[:100] if len(first_line) <= 100 else first_line[:97] + "..."
            )
        else:
            data["title"] = f"{self.author} on {self.platform}"

        # Map author_handle to username for compatibility
        data["username"] = self.author_handle or ""

        # Convert complex fields to JSON strings for database storage
        if data.get("engagement") and isinstance(data["engagement"], dict):
            import json

            data["engagement"] = json.dumps(data["engagement"])

        if data.get("media_urls") and isinstance(data["media_urls"], list):
            import json

            data["media_urls"] = json.dumps(data["media_urls"])

        if data.get("hashtags") and isinstance(data["hashtags"], list):
            import json

            data["hashtags"] = json.dumps(data["hashtags"])

        if data.get("mentions") and isinstance(data["mentions"], list):
            import json

            data["mentions"] = json.dumps(data["mentions"])

        # Remove fields that don't exist in database schema or are handled differently
        fields_to_remove = ["analysis", "id"]
        for field in fields_to_remove:
            data.pop(field, None)

        return data


class SocialExtractorBase(ABC):
    """Base class for all social media extractors"""

    def __init__(self, api_key: str = None, access_token: str = None):
        self.api_key = api_key
        self.access_token = access_token
        self.platform_name = self.__class__.__name__.replace("Extractor", "").lower()
        # Initialize the normalizer
        from src.core.normalization.markitdown_normalizer import (
            get_markitdown_normalizer,
        )

        self.normalizer = get_markitdown_normalizer()
        # Initialize the indexer
        self.indexer = None

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
            logger.error(f"❌ {self.platform_name} authentication failed: {e}")
            return False

    def normalize_post(self, post: SocialPost) -> SocialPost:
        """
        Normalize a social media post's content using MarkItDown.

        Args:
            post: SocialPost object to normalize

        Returns:
            SocialPost: Normalized post
        """
        # Convert to dict for normalization
        post_dict = post.to_dict()

        # Normalize the content
        normalized_dict = self.normalizer.normalize_item(post_dict)

        # Update the post content with normalized text
        post.content = normalized_dict.get("content", post.content)

        return post

    def index_post(self, post: SocialPost) -> bool:
        """
        Index a social media post for semantic search.

        Args:
            post: SocialPost object to index

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Lazy initialize the indexer to avoid circular imports
            if self.indexer is None:
                from src.core.indexing.indexer_agent import get_indexer_agent

                self.indexer = get_indexer_agent()

            return self.indexer.index_content(post)
        except Exception as e:
            logger.error(f"❌ Error indexing post: {e}")
            return False

    def format_post_for_analysis(self, post: SocialPost) -> Dict:
        """Format post data for AI analysis"""
        # Normalize the post before formatting for analysis
        normalized_post = self.normalize_post(post)

        return {
            "platform": normalized_post.platform,
            "title": f"{normalized_post.author} on {normalized_post.platform}",
            "content": normalized_post.content,
            "author": normalized_post.author,
            "url": normalized_post.url,
            "created_at": normalized_post.created_at.isoformat(),
            "hashtags": normalized_post.hashtags,
            "mentions": normalized_post.mentions,
            "media_count": len(normalized_post.media_urls),
            "engagement": normalized_post.engagement,
        }
