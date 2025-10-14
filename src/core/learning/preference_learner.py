#!/usr/bin/env python3
"""
Preference Learning for PrisMind
Learns user preferences from bookmarks to improve discovery
"""

from typing import List, Dict, Any
from collections import Counter
import re


class PreferenceLearner:
    """Learn user preferences from bookmarked content"""
    
    def __init__(self, db_manager):
        self.db = db_manager
    
    def analyze_bookmarks(self) -> Dict[str, Any]:
        """
        Analyze user's bookmarked content to learn preferences
        
        Returns:
            Dict with:
            - top_keywords: Most common keywords
            - top_topics: Most common topics
            - preferred_platforms: Platform preferences
            - preferred_authors: Favorite authors
            - engagement_patterns: What gets saved most
        """
        
        # Get all bookmarks
        bookmarks = self.db.get_posts(limit=1000)
        bookmarks = [p for p in bookmarks if self._is_bookmark(p)]
        
        if not bookmarks:
            return self._empty_preferences()
        
        # Extract patterns
        keywords = self._extract_keywords(bookmarks)
        topics = self._extract_topics(bookmarks)
        platforms = self._count_platforms(bookmarks)
        authors = self._count_authors(bookmarks)
        content_types = self._analyze_content_types(bookmarks)
        
        return {
            "top_keywords": keywords[:50],
            "top_topics": topics[:20],
            "preferred_platforms": platforms,
            "preferred_authors": authors[:30],
            "content_types": content_types,
            "total_bookmarks": len(bookmarks)
        }
    
    def _is_bookmark(self, post) -> bool:
        """Check if post is a bookmark (not discovered)"""
        # Check metadata
        if hasattr(post, 'metadata'):
            if isinstance(post.metadata, dict):
                return post.metadata.get('source') != 'discovered'
        
        # Default: assume bookmark
        return True
    
    def _extract_keywords(self, posts: List) -> List[tuple]:
        """Extract most common keywords from bookmarks"""
        all_words = []
        
        for post in posts:
            content = post.content.lower() if hasattr(post, 'content') else ""
            
            # Extract meaningful words (3+ chars)
            words = re.findall(r'\b[a-z]{3,}\b', content)
            all_words.extend(words)
        
        # Count and filter stop words
        stop_words = {
            'the', 'and', 'for', 'are', 'with', 'this', 'that', 'from',
            'will', 'can', 'have', 'has', 'but', 'not', 'all', 'some',
            'what', 'when', 'where', 'who', 'why', 'how', 'been', 'more'
        }
        
        counter = Counter(w for w in all_words if w not in stop_words)
        return counter.most_common(50)
    
    def _extract_topics(self, posts: List) -> List[tuple]:
        """Extract topics from posts"""
        topics = []
        
        for post in posts:
            if hasattr(post, 'topic') and post.topic:
                topics.append(post.topic)
            
            if hasattr(post, 'smart_tags') and post.smart_tags:
                topics.extend(post.smart_tags.split(','))
        
        counter = Counter(t.strip() for t in topics if t)
        return counter.most_common(20)
    
    def _count_platforms(self, posts: List) -> Dict[str, int]:
        """Count posts by platform"""
        platforms = [p.platform for p in posts if hasattr(p, 'platform')]
        return dict(Counter(platforms))
    
    def _count_authors(self, posts: List) -> List[tuple]:
        """Count posts by author"""
        authors = [p.author for p in posts if hasattr(p, 'author') and p.author]
        counter = Counter(authors)
        return counter.most_common(30)
    
    def _analyze_content_types(self, posts: List) -> Dict[str, int]:
        """Analyze what types of content user saves"""
        types = {
            'tutorials': 0,
            'news': 0,
            'research': 0,
            'discussion': 0,
            'tools': 0,
            'other': 0
        }
        
        for post in posts:
            content = post.content.lower() if hasattr(post, 'content') else ""
            
            if any(word in content for word in ['tutorial', 'guide', 'how to', 'learn']):
                types['tutorials'] += 1
            elif any(word in content for word in ['announces', 'released', 'launches', 'breaking']):
                types['news'] += 1
            elif any(word in content for word in ['research', 'study', 'paper', 'findings']):
                types['research'] += 1
            elif any(word in content for word in ['discuss', 'thoughts', 'opinion', 'what do you think']):
                types['discussion'] += 1
            elif any(word in content for word in ['tool', 'library', 'framework', 'api', 'cli']):
                types['tools'] += 1
            else:
                types['other'] += 1
        
        return types
    
    def _empty_preferences(self) -> Dict[str, Any]:
        """Return empty preferences structure"""
        return {
            "top_keywords": [],
            "top_topics": [],
            "preferred_platforms": {},
            "preferred_authors": [],
            "content_types": {},
            "total_bookmarks": 0
        }
    
    def generate_discovery_keywords(self, preferences: Dict[str, Any]) -> List[str]:
        """
        Generate keywords for discovery based on learned preferences
        
        Args:
            preferences: Dict from analyze_bookmarks()
            
        Returns:
            List of keywords to use for discovery
        """
        keywords = []
        
        # Top keywords from bookmarks
        for word, count in preferences.get('top_keywords', [])[:20]:
            if count >= 2:  # Appeared at least twice
                keywords.append(word)
        
        # Top topics
        for topic, count in preferences.get('top_topics', [])[:10]:
            keywords.append(topic)
        
        return keywords[:30]  # Return top 30
    
    def should_include_post(self, post_content: str, preferences: Dict[str, Any]) -> bool:
        """
        Check if a discovered post matches user preferences
        
        Args:
            post_content: Content of discovered post
            preferences: Learned preferences
            
        Returns:
            True if post matches preferences
        """
        content_lower = post_content.lower()
        
        # Check for keyword matches
        keywords = [kw for kw, _ in preferences.get('top_keywords', [])[:30]]
        matches = sum(1 for kw in keywords if kw in content_lower)
        
        # Need at least 2 keyword matches
        return matches >= 2
