#!/usr/bin/env python3
"""
Search Types for Research Engine
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class SearchFilter:
    """Search filter parameters"""
    platform: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = 50
    include_media: bool = True
    min_quality_score: Optional[float] = None
    min_value_score: Optional[float] = None


@dataclass
class SearchResult:
    """Search result data structure"""
    post_id: str
    platform: str
    author: str
    content: str
    title: Optional[str]
    url: str
    created_at: datetime
    quality_score: float
    value_score: float
    match_type: str
    relevance_score: float
    key_concepts: List[str]
    tags: List[str]
    media_urls: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'post_id': self.post_id,
            'platform': self.platform,
            'author': self.author,
            'content': self.content,
            'title': self.title,
            'url': self.url,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'quality_score': self.quality_score,
            'value_score': self.value_score,
            'match_type': self.match_type,
            'relevance_score': self.relevance_score,
            'key_concepts': self.key_concepts,
            'tags': self.tags,
            'media_urls': self.media_urls
        }
