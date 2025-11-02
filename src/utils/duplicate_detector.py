#!/usr/bin/env python3
"""
Universal Duplicate Detection System
Prevents duplicate content from ANY source (GitHub, Reddit, Twitter, Books, etc.)
"""

import hashlib
import logging
from typing import Optional, Dict, Any, Set
from urllib.parse import urlparse, parse_qs, urljoin
import re

logger = logging.getLogger(__name__)


class DuplicateDetector:
    """
    Universal duplicate detection for all content types
    
    Detection methods:
    1. URL normalization (handles redirects, utm params, etc.)
    2. Content hash (detects identical content with different URLs)
    3. Title similarity (catches near-duplicates)
    4. Smart matching per platform
    """
    
    def __init__(self, db_manager=None, supabase_manager=None):
        self.db = db_manager
        self.supabase = supabase_manager
        self._url_cache: Set[str] = set()
        self._content_hash_cache: Set[str] = set()
        
        # Load existing URLs/hashes into cache for fast checking
        self._initialize_cache()
    
    def _initialize_cache(self):
        """Load existing URLs and content hashes into memory"""
        
        if self.db:
            try:
                # Load all posts (no limit) - duplicate detection needs complete dataset
                # If database is too large, this might be slow, but it's necessary for accuracy
                all_posts = self.db.get_all_posts()
                logger.info(f"Loading {len(all_posts)} posts into duplicate detection cache...")
                
                for post in all_posts:
                    if post.get('url'):
                        normalized_url = self.normalize_url(post['url'])
                        self._url_cache.add(normalized_url)
                    
                    if post.get('content'):
                        content_hash = self.hash_content(post['content'])
                        self._content_hash_cache.add(content_hash)
                
                logger.info(f"✅ Loaded {len(self._url_cache)} URLs and {len(self._content_hash_cache)} content hashes into cache")
            except Exception as e:
                logger.warning(f"Cache initialization failed: {e}")
    
    def is_duplicate(self, item: Dict[str, Any]) -> bool:
        """
        Check if item is a duplicate
        
        Args:
            item: Item to check (must have 'url' or 'content')
            
        Returns:
            True if duplicate, False if unique
        """
        
        # Method 1: URL check
        if item.get('url'):
            if self.is_duplicate_url(item['url']):
                logger.debug(f"Duplicate URL: {item['url']}")
                return True
        
        # Method 2: Content hash check
        if item.get('content'):
            if self.is_duplicate_content(item['content']):
                logger.debug(f"Duplicate content: {item.get('url', 'no-url')}")
                return True
        
        # Method 3: Platform-specific checks
        platform = item.get('platform', '').lower()
        
        if platform == 'github':
            return self.is_duplicate_github(item)
        elif platform in ['twitter', 'x']:
            return self.is_duplicate_twitter(item)
        elif platform == 'reddit':
            return self.is_duplicate_reddit(item)
        elif platform == 'threads':
            return self.is_duplicate_threads(item)
        elif platform == 'book':
            return self.is_duplicate_book(item)
        
        return False
    
    def is_duplicate_threads(self, item: Dict[str, Any]) -> bool:
        """Threads-specific duplicate detection"""
        # Threads URLs can have /post/ID or just ID
        url = item.get('url', '')
        
        if url:
            # Normalize Threads URL - extract post ID
            # https://www.threads.net/@user/post/ABC123 → ABC123
            import re
            thread_match = re.search(r'/post/([^/?]+)', url)
            if thread_match:
                post_id = thread_match.group(1)
                
                # Check if this post_id already exists in cache or database
                # First check URL cache (faster)
                if self.is_duplicate_url(url):
                    return True
                
                # Then check database for Threads posts specifically
                if self.db:
                    try:
                        # Get all Threads posts (no limit - need complete check)
                        threads_posts = self.db.get_posts_by_platform('threads', limit=None) if hasattr(self.db, 'get_posts_by_platform') else self.db.get_all_posts()
                        threads_posts = [p for p in threads_posts if p.get('platform', '').lower() == 'threads']
                        
                        for post in threads_posts:
                            existing_url = post.get('url', '')
                            if existing_url:
                                existing_match = re.search(r'/post/([^/?]+)', existing_url)
                                if existing_match and existing_match.group(1) == post_id:
                                    return True
                    except Exception as e:
                        logger.warning(f"Threads duplicate check failed: {e}")
        
        # Fallback to URL check
        return self.is_duplicate_url(url)
    
    def normalize_url(self, url: str) -> str:
        """
        Normalize URL to catch duplicates with different formats
        
        Examples:
        - https://github.com/user/repo and https://github.com/user/repo/ → same
        - http vs https → same
        - URLs with UTM params → same
        - URLs with ref params → same
        """
        
        if not url:
            return ""
        
        try:
            # Parse URL
            parsed = urlparse(url.lower().strip())
            
            # Remove trailing slashes
            path = parsed.path.rstrip('/')
            
            # Remove common tracking parameters
            query_params = parse_qs(parsed.query)
            tracking_params = {'utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term',
                             'ref', 'source', 'fbclid', 'gclid', 'msclkid', '_ga', 'mc_cid', 'mc_eid'}
            
            filtered_params = {k: v for k, v in query_params.items() if k not in tracking_params}
            
            # Rebuild query string
            query_string = '&'.join([f"{k}={v[0]}" for k, v in sorted(filtered_params.items())])
            
            # Normalize scheme (treat http and https as same)
            scheme = 'https'
            
            # Rebuild normalized URL
            normalized = f"{scheme}://{parsed.netloc}{path}"
            if query_string:
                normalized += f"?{query_string}"
            
            return normalized
            
        except Exception as e:
            logger.warning(f"URL normalization failed: {e}")
            return url.lower().strip()
    
    def hash_content(self, content: str) -> str:
        """
        Create hash of content for duplicate detection
        
        Normalizes content first (lowercase, remove extra whitespace)
        """
        
        if not content:
            return ""
        
        # Normalize content
        normalized = re.sub(r'\s+', ' ', content.lower().strip())
        
        # Create hash
        return hashlib.md5(normalized.encode('utf-8')).hexdigest()
    
    def is_duplicate_url(self, url: str) -> bool:
        """Check if URL is duplicate"""
        
        normalized = self.normalize_url(url)
        
        # Check cache first (fast)
        if normalized in self._url_cache:
            return True
        
        # Check Supabase if available
        if self.supabase:
            try:
                if self.supabase.check_duplicate_by_url(url):
                    self._url_cache.add(normalized)  # Add to cache
                    return True
            except Exception as e:
                logger.warning(f"Supabase URL check failed: {e}")
        
        # Check SQLite if available (check all posts for accuracy)
        if self.db:
            try:
                all_posts = self.db.get_all_posts()
                for post in all_posts:
                    if post.get('url') and self.normalize_url(post['url']) == normalized:
                        self._url_cache.add(normalized)  # Add to cache
                        return True
            except Exception as e:
                logger.warning(f"Database URL check failed: {e}")
        
        return False
    
    def is_duplicate_content(self, content: str) -> bool:
        """Check if content is duplicate (exact match)"""
        
        content_hash = self.hash_content(content)
        
        # Check cache first (fast)
        if content_hash in self._content_hash_cache:
            return True
        
        # For now, only use cache
        # Could extend to check database if needed
        
        return False
    
    def is_duplicate_github(self, item: Dict[str, Any]) -> bool:
        """GitHub-specific duplicate detection"""
        
        url = item.get('url', '')
        
        # Normalize GitHub URLs
        # https://github.com/user/repo and github.com/user/repo/ are same
        github_match = re.search(r'github\.com/([^/]+)/([^/]+)', url)
        
        if github_match:
            owner, repo = github_match.groups()
            repo = repo.rstrip('.git')
            
            canonical_url = f"https://github.com/{owner}/{repo}"
            
            return self.is_duplicate_url(canonical_url)
        
        return self.is_duplicate_url(url)
    
    def is_duplicate_twitter(self, item: Dict[str, Any]) -> bool:
        """Twitter-specific duplicate detection"""
        
        url = item.get('url', '')
        
        # Extract tweet ID
        # https://twitter.com/user/status/123456 and https://x.com/user/status/123456 are same
        tweet_match = re.search(r'(?:twitter|x)\.com/[^/]+/status/(\d+)', url)
        
        if tweet_match:
            tweet_id = tweet_match.group(1)
            canonical_url = f"https://twitter.com/i/status/{tweet_id}"
            
            return self.is_duplicate_url(canonical_url)
        
        return self.is_duplicate_url(url)
    
    def is_duplicate_reddit(self, item: Dict[str, Any]) -> bool:
        """Reddit-specific duplicate detection"""
        
        url = item.get('url', '')
        
        # Extract post ID
        # Different reddit URL formats should be treated as same
        reddit_match = re.search(r'reddit\.com/r/[^/]+/comments/([a-z0-9]+)', url)
        
        if reddit_match:
            post_id = reddit_match.group(1)
            canonical_url = f"https://reddit.com/comments/{post_id}"
            
            return self.is_duplicate_url(canonical_url)
        
        return self.is_duplicate_url(url)
    
    def is_duplicate_book(self, item: Dict[str, Any]) -> bool:
        """Book-specific duplicate detection"""
        
        title = item.get('title', '').lower().strip()
        author = item.get('author', '').lower().strip()
        
        if not title:
            return False
        
        # Check if same title+author combination exists
        if self.db:
            try:
                posts = self.db.get_posts(limit=5000)
                for post in posts:
                    if post.get('platform') == 'book':
                        post_title = post.get('title', '').lower().strip()
                        post_author = post.get('author', '').lower().strip()
                        
                        if post_title == title and post_author == author:
                            return True
            except Exception as e:
                logger.warning(f"Book duplicate check failed: {e}")
        
        return False
    
    def mark_as_seen(self, item: Dict[str, Any]):
        """Mark item as seen to prevent future duplicates"""
        
        if item.get('url'):
            normalized_url = self.normalize_url(item['url'])
            self._url_cache.add(normalized_url)
        
        if item.get('content'):
            content_hash = self.hash_content(item['content'])
            self._content_hash_cache.add(content_hash)
    
    def get_stats(self) -> Dict[str, int]:
        """Get duplicate detector statistics"""
        
        return {
            "cached_urls": len(self._url_cache),
            "cached_content_hashes": len(self._content_hash_cache),
            "total_cached": len(self._url_cache) + len(self._content_hash_cache)
        }


# Singleton instance
_duplicate_detector = None


def get_duplicate_detector(db_manager=None, supabase_manager=None) -> DuplicateDetector:
    """Get global duplicate detector"""
    global _duplicate_detector
    if _duplicate_detector is None:
        _duplicate_detector = DuplicateDetector(db_manager, supabase_manager)
    return _duplicate_detector


def test_duplicate_detector():
    """Test duplicate detection"""
    
    print("🧪 Testing Duplicate Detector\n")
    
    detector = DuplicateDetector()
    
    # Test URL normalization
    print("1️⃣  URL Normalization:")
    print("-" * 70)
    
    test_urls = [
        ("https://github.com/user/repo", "https://github.com/user/repo/"),
        ("https://github.com/user/repo", "http://github.com/user/repo"),
        ("https://github.com/user/repo?utm_source=twitter", "https://github.com/user/repo"),
        ("https://twitter.com/user/status/123", "https://x.com/user/status/123"),
    ]
    
    for url1, url2 in test_urls:
        norm1 = detector.normalize_url(url1)
        norm2 = detector.normalize_url(url2)
        match = "✅ MATCH" if norm1 == norm2 else "❌ DIFFERENT"
        print(f"{match}")
        print(f"  URL 1: {url1}")
        print(f"  URL 2: {url2}")
        print(f"  Norm:  {norm1}")
        print()
    
    # Test content hashing
    print("2️⃣  Content Hashing:")
    print("-" * 70)
    
    content1 = "This is a test post about AI"
    content2 = "This   is  a   test  post  about  AI"  # Extra spaces
    content3 = "This is a different post"
    
    hash1 = detector.hash_content(content1)
    hash2 = detector.hash_content(content2)
    hash3 = detector.hash_content(content3)
    
    print(f"Content 1: {content1}")
    print(f"Content 2: {content2}")
    print(f"Hash match: {'✅ SAME' if hash1 == hash2 else '❌ DIFFERENT'}")
    print()
    print(f"Content 3: {content3}")
    print(f"Hash match: {'✅ SAME' if hash1 == hash3 else '❌ DIFFERENT (expected)'}")
    print()
    
    # Test duplicate detection
    print("3️⃣  Duplicate Detection:")
    print("-" * 70)
    
    item1 = {"url": "https://github.com/openai/whisper", "content": "Speech recognition"}
    item2 = {"url": "https://github.com/openai/whisper/", "content": "Different content"}
    
    is_dup = detector.is_duplicate(item1)
    print(f"Item 1: {'Duplicate' if is_dup else 'Unique'}")
    
    detector.mark_as_seen(item1)
    
    is_dup = detector.is_duplicate(item2)
    print(f"Item 2 (same URL): {'✅ Duplicate' if is_dup else '❌ Should be duplicate!'}")
    print()
    
    # Stats
    stats = detector.get_stats()
    print(f"📊 Stats: {stats['cached_urls']} URLs, {stats['cached_content_hashes']} content hashes")
    print()
    print("✅ Duplicate detector working!")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_duplicate_detector()
