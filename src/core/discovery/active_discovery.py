#!/usr/bin/env python3
"""
Active Discovery for PrisMind
Actively searches for new content matching user interests
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from src.core.discovery.topic_tracker import TopicTracker
from src.core.discovery.discovery_engine import DiscoveryEngine
from src.core.extraction.social_extractor_base import SocialPost


class ActiveDiscovery:
    """Actively discover new content from various sources"""
    
    def __init__(self, topic_tracker: Optional[TopicTracker] = None):
        self.topic_tracker = topic_tracker or TopicTracker()
        self.discovery_engine = DiscoveryEngine(self.topic_tracker)
    
    async def search_twitter(self, query: str, limit: int = 20) -> List[SocialPost]:
        """
        Search Twitter for recent tweets matching query
        Note: Requires Twitter API or web scraping
        """
        print(f"🐦 Searching Twitter for: {query}")
        
        # TODO: Implement Twitter search
        # Options:
        # 1. Twitter API v2 (requires API key)
        # 2. nitter.net scraping (no auth needed)
        # 3. Playwright-based search
        
        # For now, return empty - will implement based on available method
        print("   ⚠️ Twitter search not yet implemented")
        return []
    
    async def search_reddit(self, query: str, limit: int = 20) -> List[SocialPost]:
        """
        Search Reddit for recent posts matching query
        """
        print(f"🤖 Searching Reddit for: {query}")
        
        try:
            import praw
            import os
            
            # Use existing Reddit credentials
            reddit = praw.Reddit(
                client_id=os.getenv("REDDIT_CLIENT_ID"),
                client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
                user_agent=os.getenv("REDDIT_USER_AGENT", "PrisMind/1.0")
            )
            
            posts = []
            
            # Search across multiple subreddits
            subreddits = ["all", "technology", "programming", "startups", "artificial"]
            
            for subreddit_name in subreddits[:2]:  # Limit to 2 to avoid rate limits
                try:
                    subreddit = reddit.subreddit(subreddit_name)
                    
                    # Search hot posts
                    for submission in subreddit.search(query, limit=limit//2, time_filter="day"):
                        post = SocialPost(
                            post_id=f"reddit_{submission.id}",
                            platform="reddit",
                            author=str(submission.author) if submission.author else "Unknown",
                            author_handle=str(submission.author) if submission.author else "Unknown",
                            content=f"{submission.title}\n\n{submission.selftext[:500]}",
                            url=f"https://reddit.com{submission.permalink}",
                            created_at=datetime.fromtimestamp(submission.created_utc),
                            post_type="post"
                        )
                        posts.append(post)
                
                except Exception as e:
                    print(f"   Error searching r/{subreddit_name}: {e}")
                    continue
            
            print(f"   ✅ Found {len(posts)} Reddit posts")
            return posts[:limit]
            
        except Exception as e:
            print(f"   ❌ Reddit search error: {e}")
            return []
    
    async def scan_rss_feeds(self, keywords: List[str], limit: int = 20) -> List[SocialPost]:
        """
        Scan RSS feeds for articles matching keywords
        """
        print(f"📰 Scanning RSS feeds for: {', '.join(keywords[:3])}...")
        
        try:
            from src.core.extraction.article_extractor import ArticleExtractor, DEFAULT_RSS_FEEDS
            
            extractor = ArticleExtractor()
            
            # Get articles from default feeds
            all_articles = extractor.extract_from_multiple_feeds(
                DEFAULT_RSS_FEEDS[:3],  # Limit to 3 feeds
                limit_per_feed=10
            )
            
            # Filter by keywords
            relevant = []
            for article in all_articles:
                content_lower = article.content.lower()
                
                # Check if any keyword matches
                for keyword in keywords:
                    if keyword.lower() in content_lower:
                        relevant.append(article)
                        break
            
            print(f"   ✅ Found {len(relevant)} relevant articles")
            return relevant[:limit]
            
        except Exception as e:
            print(f"   ❌ RSS scan error: {e}")
            return []
    
    async def discover_by_topics(self, max_per_source: int = 20) -> List[Dict[str, Any]]:
        """
        Main discovery method - search all sources for tracked topics
        
        Returns:
            List of discovered posts with metadata
        """
        print("\n🔍 Starting Active Discovery")
        print("="*60)
        
        # Get all keywords from enabled topics
        keywords = self.topic_tracker.get_all_keywords()
        
        print(f"📋 Tracking {len(keywords)} keywords across topics")
        
        # Build search queries (combine related keywords)
        queries = self._build_search_queries(keywords)
        
        print(f"🔎 Generated {len(queries)} search queries\n")
        
        all_posts = []
        
        # Search Reddit
        for query in queries[:3]:  # Limit to 3 queries to avoid rate limits
            reddit_posts = await self.search_reddit(query, limit=max_per_source)
            all_posts.extend(reddit_posts)
            await asyncio.sleep(2)  # Rate limiting
        
        # Search Twitter (when implemented)
        # for query in queries[:3]:
        #     twitter_posts = await self.search_twitter(query, limit=max_per_source)
        #     all_posts.extend(twitter_posts)
        
        # Scan RSS feeds
        rss_posts = await self.scan_rss_feeds(keywords[:10], limit=max_per_source)
        all_posts.extend(rss_posts)
        
        print(f"\n📊 Total posts found: {len(all_posts)}")
        
        # Run discovery engine to filter by quality
        print("\n🎯 Filtering by relevance and quality...")
        
        discovered = self.discovery_engine.discover_from_posts(all_posts)
        
        print(f"\n✅ Active Discovery Complete!")
        print(f"   Total found: {len(all_posts)}")
        print(f"   High-quality: {len(discovered)}")
        print("="*60)
        
        return discovered
    
    def _build_search_queries(self, keywords: List[str]) -> List[str]:
        """
        Build effective search queries from keywords
        Combines related keywords for better results
        """
        queries = []
        
        # Group keywords by topic
        enabled_topics = self.topic_tracker.get_enabled_topics()
        
        for topic in enabled_topics:
            topic_keywords = topic.get("keywords", [])
            
            # Take top 3 keywords per topic
            top_keywords = topic_keywords[:3]
            
            if len(top_keywords) >= 2:
                # Combine first 2 keywords
                query = f"{top_keywords[0]} {top_keywords[1]}"
                queries.append(query)
        
        return queries
    
    async def auto_discover_loop(self, interval_hours: int = 4):
        """
        Continuous discovery loop - runs every N hours
        
        Args:
            interval_hours: Hours between discovery runs (default 4)
        """
        print(f"🤖 Starting auto-discovery loop (every {interval_hours} hours)")
        
        while True:
            try:
                print(f"\n⏰ Auto-discovery triggered at {datetime.now()}")
                
                # Run discovery
                discovered = await self.discover_by_topics(max_per_source=15)
                
                # TODO: Store discovered posts in database
                # TODO: Send notification if high-value content found
                
                print(f"💤 Sleeping for {interval_hours} hours...\n")
                
                # Reset daily counter at midnight
                now = datetime.now()
                if now.hour == 0:
                    self.discovery_engine.reset_daily_counter()
                
                # Sleep until next run
                await asyncio.sleep(interval_hours * 3600)
                
            except Exception as e:
                print(f"❌ Auto-discovery error: {e}")
                await asyncio.sleep(3600)  # Wait 1 hour on error
