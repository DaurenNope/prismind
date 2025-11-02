#!/usr/bin/env python3
"""
Digest Generator for PrisMind
Generates morning digests and evening summaries from discoveries
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from collections import defaultdict

from src.services.new_database_manager import get_database_manager
from src.core.discovery.profile_manager import ProfileManager

logger = logging.getLogger(__name__)


class DigestGenerator:
    """Generate curated digests from discovered content"""
    
    def __init__(self):
        self.db = get_database_manager()
        self.profile_manager = ProfileManager()
    
    def generate_morning_digest(self, profile_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate morning digest - top stories from last 24 hours
        
        Args:
            profile_id: Optional profile to filter by
            
        Returns:
            Digest with top stories, trending topics, must-reads
        """
        logger.info("🌅 Generating morning digest...")
        
        # Get posts from last 24 hours
        cutoff = datetime.now() - timedelta(hours=24)
        all_posts = self.db.get_posts(limit=500)
        
        # Filter recent posts
        recent_posts = []
        for post in all_posts:
            if hasattr(post, 'created_at'):
                try:
                    post_time = datetime.fromisoformat(str(post.created_at))
                    if post_time > cutoff:
                        recent_posts.append(post)
                except (ValueError, TypeError) as e:
                    logger.debug(f"Failed to parse created_at timestamp: {e}")
                    pass
        
        if not recent_posts:
            logger.info("📭 No recent posts for morning digest")
            return {
                "type": "morning",
                "timestamp": datetime.now().isoformat(),
                "posts_count": 0,
                "top_stories": [],
                "trending_topics": [],
                "must_reads": []
            }
        
        # Sort by quality score
        scored_posts = [p for p in recent_posts if hasattr(p, 'quality_score')]
        sorted_posts = sorted(
            scored_posts,
            key=lambda p: getattr(p, 'quality_score', 0),
            reverse=True
        )
        
        # Extract top stories (top 5 highest quality)
        top_stories = self._format_top_stories(sorted_posts[:5])
        
        # Identify trending topics
        trending_topics = self._identify_trending_topics(recent_posts)
        
        # Select must-reads (high quality + specific formats)
        must_reads = self._select_must_reads(sorted_posts)
        
        digest = {
            "type": "morning",
            "timestamp": datetime.now().isoformat(),
            "posts_count": len(recent_posts),
            "top_stories": top_stories,
            "trending_topics": trending_topics,
            "must_reads": must_reads,
            "profile": profile_id or "all"
        }
        
        logger.info(f"✅ Morning digest generated: {len(top_stories)} stories, "
                   f"{len(trending_topics)} topics")
        
        return digest
    
    def generate_evening_summary(self) -> Dict[str, Any]:
        """
        Generate evening summary - daily stats and highlights
        
        Returns:
            Summary with stats, highlights, tomorrow preview
        """
        logger.info("🌆 Generating evening summary...")
        
        # Get today's posts
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        all_posts = self.db.get_posts(limit=500)
        
        today_posts = []
        for post in all_posts:
            if hasattr(post, 'created_at'):
                try:
                    post_time = datetime.fromisoformat(str(post.created_at))
                    if post_time > today_start:
                        today_posts.append(post)
                except (ValueError, TypeError) as e:
                    logger.debug(f"Failed to parse created_at timestamp: {e}")
                    pass
        
        # Calculate stats
        platform_stats = defaultdict(int)
        quality_posts = 0
        
        for post in today_posts:
            if hasattr(post, 'platform'):
                platform_stats[post.platform] += 1
            if hasattr(post, 'quality_score') and post.quality_score > 0.6:
                quality_posts += 1
        
        # Identify top topics
        top_topics = self._identify_trending_topics(today_posts)
        
        # Find highlights (best of today)
        highlights = []
        if today_posts:
            scored = [p for p in today_posts if hasattr(p, 'quality_score')]
            sorted_posts = sorted(scored, key=lambda p: p.quality_score, reverse=True)
            highlights = self._format_top_stories(sorted_posts[:3])
        
        summary = {
            "type": "evening",
            "timestamp": datetime.now().isoformat(),
            "total_posts": len(today_posts),
            "quality_posts": quality_posts,
            "platform_stats": dict(platform_stats),
            "top_topics": top_topics[:3],
            "highlights": highlights,
            "tomorrow_preview": "AI & Developer Tools"  # TODO: Smart prediction
        }
        
        logger.info(f"✅ Evening summary generated: {len(today_posts)} posts, "
                   f"{quality_posts} high-quality")
        
        return summary
    
    def _format_top_stories(self, posts: List[Any]) -> List[Dict[str, Any]]:
        """Format posts as top stories"""
        stories = []
        
        for post in posts[:5]:  # Max 5 stories
            story = {
                "title": self._get_post_title(post),
                "author": getattr(post, 'author', 'Unknown'),
                "url": getattr(post, 'url', ''),
                "quality_score": getattr(post, 'quality_score', 0),
                "platform": getattr(post, 'platform', 'unknown'),
                "summary": self._get_post_summary(post)
            }
            stories.append(story)
        
        return stories
    
    def _get_post_title(self, post: Any) -> str:
        """Extract or generate post title"""
        # Try different title fields
        if hasattr(post, 'title') and post.title:
            return post.title[:100]
        
        if hasattr(post, 'content') and post.content:
            # Use first line of content
            first_line = post.content.split('\n')[0]
            return first_line[:100]
        
        return "Untitled Post"
    
    def _get_post_summary(self, post: Any) -> str:
        """Get post summary (first 200 chars)"""
        if hasattr(post, 'content') and post.content:
            return post.content[:200].replace('\n', ' ')
        return ""
    
    def _identify_trending_topics(self, posts: List[Any]) -> List[Dict[str, Any]]:
        """Identify trending topics from posts"""
        # Count topic mentions
        topic_counts = defaultdict(int)
        topic_posts = defaultdict(list)
        
        for post in posts:
            # Extract topics from content
            topics = self._extract_topics(post)
            for topic in topics:
                topic_counts[topic] += 1
                topic_posts[topic].append(post)
        
        # Sort by frequency
        trending = []
        for topic, count in sorted(topic_counts.items(), 
                                   key=lambda x: x[1], 
                                   reverse=True)[:5]:
            trending.append({
                "topic": topic,
                "count": count,
                "posts": topic_posts[topic][:3]  # Sample posts
            })
        
        return trending
    
    def _extract_topics(self, post: Any) -> List[str]:
        """Extract topics from post (simple keyword matching)"""
        topics = []
        
        content = ""
        if hasattr(post, 'content'):
            content = str(post.content).lower()
        if hasattr(post, 'title'):
            content += " " + str(post.title).lower()
        
        # Common tech topics
        topic_keywords = {
            "AI & ML": ["ai", "artificial intelligence", "machine learning", "llm", "gpt"],
            "Web Development": ["react", "javascript", "web dev", "frontend", "backend"],
            "DevTools": ["devtools", "ide", "vscode", "developer tools"],
            "Cloud": ["aws", "azure", "cloud", "kubernetes", "docker"],
            "Startups": ["startup", "founder", "vc", "funding"],
            "Mobile": ["ios", "android", "mobile app", "flutter"],
            "Database": ["database", "sql", "postgres", "mongodb"],
            "Security": ["security", "vulnerability", "encryption"],
        }
        
        for topic, keywords in topic_keywords.items():
            if any(kw in content for kw in keywords):
                topics.append(topic)
        
        return topics if topics else ["General Tech"]
    
    def _select_must_reads(self, posts: List[Any]) -> List[Dict[str, Any]]:
        """Select must-read content (high quality + good format)"""
        must_reads = []
        
        for post in posts[:20]:  # Check top 20
            # Must have high quality
            if not hasattr(post, 'quality_score') or post.quality_score < 0.7:
                continue
            
            # Prefer certain content types
            content = str(getattr(post, 'content', '')).lower()
            
            is_tutorial = any(word in content for word in 
                            ['tutorial', 'guide', 'how to', 'step by step'])
            is_long_form = len(content) > 500
            is_technical = any(word in content for word in 
                             ['code', 'implementation', 'architecture'])
            
            if is_tutorial or (is_long_form and is_technical):
                must_reads.append({
                    "title": self._get_post_title(post),
                    "url": getattr(post, 'url', ''),
                    "type": "tutorial" if is_tutorial else "technical",
                    "quality_score": post.quality_score
                })
                
                if len(must_reads) >= 3:
                    break
        
        return must_reads
    
    def format_for_telegram(self, digest: Dict[str, Any]) -> str:
        """
        Format digest for Telegram display
        
        Args:
            digest: Digest dictionary
            
        Returns:
            Formatted markdown text
        """
        if digest["type"] == "morning":
            return self._format_morning_telegram(digest)
        else:
            return self._format_evening_telegram(digest)
    
    def _format_morning_telegram(self, digest: Dict[str, Any]) -> str:
        """Format morning digest for Telegram"""
        lines = [
            "🌅 <b>Good Morning! Your Daily Intelligence Digest</b>",
            "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        ]
        
        # Top stories
        if digest["top_stories"]:
            lines.append("📰 <b>TOP STORIES</b>\n")
            for i, story in enumerate(digest["top_stories"], 1):
                lines.append(
                    f"{i}. {story['title']}\n"
                    f"   By {story['author']} | "
                    f"Quality: {story['quality_score']:.2f}\n"
                    f"   {story['url']}\n"
                )
        
        # Trending topics
        if digest["trending_topics"]:
            lines.append("\n🔥 <b>TRENDING TOPICS</b>\n")
            for topic in digest["trending_topics"][:3]:
                lines.append(f"• {topic['topic']} ({topic['count']} posts)\n")
        
        # Must reads
        if digest["must_reads"]:
            lines.append("\n📚 <b>MUST-READS</b>\n")
            for item in digest["must_reads"]:
                lines.append(f"• {item['title']}\n")
        
        lines.append(f"\n━━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append(f"📊 Total: {digest['posts_count']} posts from last 24h")
        lines.append(f"🔗 View full: /latest")
        
        return "\n".join(lines)
    
    def _format_evening_telegram(self, summary: Dict[str, Any]) -> str:
        """Format evening summary for Telegram"""
        lines = [
            "🌆 <b>Evening Summary - Today's Intelligence</b>",
            "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        ]
        
        # Stats
        lines.append(f"✨ <b>Discoveries:</b> {summary['total_posts']} posts")
        lines.append(f"⭐ <b>High Quality:</b> {summary['quality_posts']} posts")
        
        # Platform breakdown
        if summary["platform_stats"]:
            lines.append(f"\n📊 <b>By Platform:</b>")
            for platform, count in summary["platform_stats"].items():
                lines.append(f"   • {platform}: {count}")
        
        # Top topics
        if summary["top_topics"]:
            lines.append(f"\n🔥 <b>Trending Today:</b>")
            for topic in summary["top_topics"]:
                lines.append(f"   • {topic['topic']} ({topic['count']} posts)")
        
        # Highlights
        if summary["highlights"]:
            lines.append(f"\n⭐ <b>Today's Highlights:</b>")
            for item in summary["highlights"]:
                lines.append(f"   • {item['title']}")
        
        lines.append(f"\n━━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append(f"🎯 Tomorrow: {summary['tomorrow_preview']}")
        lines.append(f"💤 See you at 8 AM!")
        
        return "\n".join(lines)


def test_digest_generator():
    """Test digest generator"""
    print("\n🧪 Testing Digest Generator\n")
    
    generator = DigestGenerator()
    
    # Test morning digest
    print("🌅 Testing morning digest...")
    morning = generator.generate_morning_digest()
    print(f"   Posts: {morning['posts_count']}")
    print(f"   Stories: {len(morning['top_stories'])}")
    print(f"   Topics: {len(morning['trending_topics'])}")
    
    # Format for Telegram
    telegram_text = generator.format_for_telegram(morning)
    print(f"\n📱 Telegram format ({len(telegram_text)} chars):")
    print(telegram_text[:500] + "...\n")
    
    # Test evening summary
    print("🌆 Testing evening summary...")
    evening = generator.generate_evening_summary()
    print(f"   Posts: {evening['total_posts']}")
    print(f"   Quality: {evening['quality_posts']}")
    print(f"   Platforms: {len(evening['platform_stats'])}")
    
    telegram_text = generator.format_for_telegram(evening)
    print(f"\n📱 Telegram format ({len(telegram_text)} chars):")
    print(telegram_text[:500] + "...\n")
    
    print("✅ Digest generator working!")


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    test_digest_generator()
