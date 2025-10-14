#!/usr/bin/env python3
"""
Enhanced Librarian Agent for PrisMind
Curates content like a master librarian + handles books, papers, and deep curation
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import Counter, defaultdict


class EnhancedLibrarianAgent:
    """
    Master librarian that:
    - Curates content by topic and quality
    - Manages reading lists
    - Tracks books and papers
    - Creates thematic collections
    - Provides recommendations
    """
    
    def __init__(self, db_manager=None):
        self.db = db_manager
        self.collections = {}
        self.reading_lists = {}
    
    async def curate_content(self, posts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Curate content like a master librarian
        
        Returns:
            {
                "must_read": [...],
                "interesting": [...],
                "reference": [...],
                "by_topic": {...},
                "by_format": {...},
                "collections": {...}
            }
        """
        
        print("\n📚 Enhanced Librarian: Curating your collection...")
        
        curated = {
            "must_read": [],
            "interesting": [],
            "reference": [],
            "quick_reads": [],
            "deep_dives": [],
            "by_topic": defaultdict(list),
            "by_format": defaultdict(list),
            "collections": {}
        }
        
        for item in posts:
            post = item.get("post") if isinstance(item, dict) else item
            quality = item.get("quality_score", 0) if isinstance(item, dict) else 0.5
            topics = item.get("topics", []) if isinstance(item, dict) else []
            
            # Quality-based curation (lowered thresholds)
            if quality >= 0.65:
                curated["must_read"].append(item)
            elif quality >= 0.45:
                curated["interesting"].append(item)
            else:
                curated["reference"].append(item)
            
            # Length-based curation
            content_length = len(post.content) if hasattr(post, 'content') else 0
            if content_length < 500:
                curated["quick_reads"].append(item)
            elif content_length > 2000:
                curated["deep_dives"].append(item)
            
            # Topic organization
            for topic in topics:
                topic_name = topic.get("topic_name") if isinstance(topic, dict) else str(topic)
                curated["by_topic"][topic_name].append(item)
            
            # Format organization
            content_type = self._detect_content_type(post)
            curated["by_format"][content_type].append(item)
        
        # Create thematic collections
        curated["collections"] = self._create_collections(posts)
        
        print(f"   ✅ Curated: {len(curated['must_read'])} must-read, "
              f"{len(curated['interesting'])} interesting, "
              f"{len(curated['quick_reads'])} quick reads")
        
        return curated
    
    def _detect_content_type(self, post) -> str:
        """Detect what type of content this is"""
        
        if not hasattr(post, 'content'):
            return "unknown"
        
        content = post.content.lower()
        url = post.url.lower() if hasattr(post, 'url') and post.url else ""
        
        # Books
        if any(word in content for word in ['isbn', 'book review', 'chapter', 'published by']):
            return "book"
        
        # Academic papers
        if any(word in content for word in ['arxiv', 'doi:', 'abstract:', 'methodology', 'results show']):
            return "paper"
        
        # Tutorials
        if any(word in content for word in ['tutorial', 'how to', 'step by step', 'guide', 'walkthrough']):
            return "tutorial"
        
        # News
        if any(word in content for word in ['announced', 'breaking', 'released today', 'just launched']):
            return "news"
        
        # Discussions
        if any(word in content for word in ['what do you think', 'opinions?', 'discuss', 'thoughts on']):
            return "discussion"
        
        # Tools/Libraries
        if any(word in content for word in ['github.com', 'open source', 'npm install', 'pip install']):
            return "tool"
        
        # Threads/Long-form
        if len(content) > 2000:
            return "long_form"
        
        return "article"
    
    def _create_collections(self, posts: List[Dict]) -> Dict[str, List]:
        """Create thematic collections"""
        
        collections = {
            "ai_breakthroughs": [],
            "startup_stories": [],
            "dev_tools": [],
            "learning_resources": [],
            "industry_news": []
        }
        
        for item in posts:
            post = item.get("post") if isinstance(item, dict) else item
            
            if not hasattr(post, 'content'):
                continue
            
            content = post.content.lower()
            
            # AI Breakthroughs
            if any(word in content for word in ['breakthrough', 'new model', 'gpt', 'claude', 'sota', 'state of the art']):
                collections["ai_breakthroughs"].append(item)
            
            # Startup Stories
            if any(word in content for word in ['startup', 'founder', 'raised', 'funding', 'yc', 'launch']):
                collections["startup_stories"].append(item)
            
            # Dev Tools
            if any(word in content for word in ['vscode', 'cursor', 'developer tools', 'cli', 'framework']):
                collections["dev_tools"].append(item)
            
            # Learning Resources
            if any(word in content for word in ['learn', 'course', 'tutorial', 'beginner', 'introduction']):
                collections["learning_resources"].append(item)
            
            # Industry News
            if any(word in content for word in ['announced', 'acquired', 'ipo', 'market', 'industry']):
                collections["industry_news"].append(item)
        
        # Only return non-empty collections
        return {k: v for k, v in collections.items() if v}
    
    async def create_reading_list(self, name: str, items: List[Dict], description: str = "") -> Dict[str, Any]:
        """Create a curated reading list"""
        
        reading_list = {
            "id": f"reading_list_{len(self.reading_lists)}",
            "name": name,
            "description": description,
            "items": items,
            "created": datetime.now().isoformat(),
            "progress": {
                "total": len(items),
                "read": 0,
                "reading": 0,
                "to_read": len(items)
            }
        }
        
        self.reading_lists[reading_list["id"]] = reading_list
        
        print(f"   📖 Created reading list: '{name}' ({len(items)} items)")
        
        return reading_list
    
    async def curate_books(self, query: str = None) -> List[Dict[str, Any]]:
        """
        Curate books from various sources
        
        Args:
            query: Search query for books
            
        Returns:
            List of curated books with metadata
        """
        
        print(f"\n📚 Curating books: '{query}'...")
        
        books = []
        
        # TODO: Integrate with:
        # - Open Library API
        # - Google Books API
        # - Goodreads (if available)
        # - Library Genesis search
        
        # For now, return structure
        print("   ℹ️  Book APIs not yet integrated")
        
        return books
    
    async def recommend_related(self, item: Dict[str, Any], all_posts: List[Dict]) -> List[Dict]:
        """
        Recommend related content based on a given item
        
        Args:
            item: Reference item
            all_posts: Pool of all posts to search
            
        Returns:
            List of related items
        """
        
        post = item.get("post") if isinstance(item, dict) else item
        topics = item.get("topics", []) if isinstance(item, dict) else []
        
        related = []
        topic_names = [t.get("topic_name") if isinstance(t, dict) else str(t) for t in topics]
        
        for other_item in all_posts:
            other_post = other_item.get("post") if isinstance(other_item, dict) else other_item
            other_topics = other_item.get("topics", []) if isinstance(other_item, dict) else []
            
            # Skip same item
            if hasattr(post, 'post_id') and hasattr(other_post, 'post_id'):
                if post.post_id == other_post.post_id:
                    continue
            
            # Check topic overlap
            other_topic_names = [t.get("topic_name") if isinstance(t, dict) else str(t) for t in other_topics]
            overlap = set(topic_names) & set(other_topic_names)
            
            if overlap:
                related.append({
                    **other_item,
                    "relevance": len(overlap) / max(len(topic_names), len(other_topic_names))
                })
        
        # Sort by relevance
        related.sort(key=lambda x: x.get("relevance", 0), reverse=True)
        
        return related[:5]  # Top 5 related
    
    async def generate_reading_report(self, days: int = 7) -> Dict[str, Any]:
        """
        Generate a reading report
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Reading statistics and insights
        """
        
        if not self.db:
            return {"error": "No database connection"}
        
        # Get posts from last N days
        posts = self.db.get_posts(limit=1000)
        
        # Filter by date
        cutoff = datetime.now() - timedelta(days=days)
        recent_posts = [
            p for p in posts
            if hasattr(p, 'created_at') and 
            datetime.fromisoformat(str(p.created_at)) > cutoff
        ]
        
        # Analyze
        topics = Counter()
        formats = Counter()
        quality_scores = []
        
        for post in recent_posts:
            # Extract topics
            if hasattr(post, 'topic') and post.topic:
                topics[post.topic] += 1
            
            # Detect format
            content_type = self._detect_content_type(post)
            formats[content_type] += 1
            
            # Track quality
            if hasattr(post, 'quality_score') and post.quality_score:
                quality_scores.append(post.quality_score)
        
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        
        return {
            "period_days": days,
            "total_items": len(recent_posts),
            "top_topics": topics.most_common(10),
            "by_format": dict(formats),
            "avg_quality": round(avg_quality, 2),
            "quality_distribution": {
                "excellent": len([q for q in quality_scores if q >= 0.8]),
                "good": len([q for q in quality_scores if 0.6 <= q < 0.8]),
                "fair": len([q for q in quality_scores if q < 0.6])
            }
        }
    
    async def create_thematic_digest(self, theme: str, posts: List[Dict]) -> str:
        """
        Create a thematic digest (e.g., "This week in AI")
        
        Args:
            theme: Theme name
            posts: Posts to include
            
        Returns:
            Formatted digest text
        """
        
        curated = await self.curate_content(posts)
        
        digest = f"📚 {theme.upper()}\n"
        digest += f"{'='*60}\n\n"
        
        # Must-reads
        if curated["must_read"]:
            digest += "🔥 MUST-READS:\n\n"
            for i, item in enumerate(curated["must_read"][:5], 1):
                post = item.get("post") if isinstance(item, dict) else item
                quality = item.get("quality_score", 0) if isinstance(item, dict) else 0
                
                title = post.content[:80] if hasattr(post, 'content') else "No title"
                author = post.author if hasattr(post, 'author') else "Unknown"
                
                digest += f"{i}. {title}...\n"
                digest += f"   By: {author} | Quality: {quality:.2f}\n\n"
        
        # Collections
        if curated["collections"]:
            digest += "\n📦 COLLECTIONS:\n\n"
            for collection_name, items in curated["collections"].items():
                digest += f"• {collection_name.replace('_', ' ').title()}: {len(items)} items\n"
        
        # Stats
        digest += f"\n📊 STATS:\n"
        digest += f"Total curated: {len(posts)}\n"
        digest += f"Must-reads: {len(curated['must_read'])}\n"
        digest += f"Quick reads: {len(curated['quick_reads'])}\n"
        digest += f"Deep dives: {len(curated['deep_dives'])}\n"
        
        return digest


async def test_librarian():
    """Test the enhanced librarian agent"""
    
    print("🧪 Testing Enhanced Librarian Agent\n")
    
    librarian = EnhancedLibrarianAgent()
    
    # Create mock posts
    mock_posts = [
        {
            "post": type('Post', (), {
                'content': 'Tutorial: How to build AI agents with LangChain',
                'author': 'AI Developer',
                'post_id': '1',
                'url': 'https://example.com/tutorial'
            })(),
            "quality_score": 0.75,
            "topics": [{"topic_name": "AI & Machine Learning"}]
        },
        {
            "post": type('Post', (), {
                'content': 'Startup XYZ raises $10M Series A from YC',
                'author': 'Tech News',
                'post_id': '2',
                'url': 'https://example.com/funding'
            })(),
            "quality_score": 0.68,
            "topics": [{"topic_name": "Startups"}]
        }
    ]
    
    # Test curation
    curated = await librarian.curate_content(mock_posts)
    
    print(f"\n📊 Curation Results:")
    print(f"   Must-read: {len(curated['must_read'])}")
    print(f"   Interesting: {len(curated['interesting'])}")
    print(f"   Quick reads: {len(curated['quick_reads'])}")
    print(f"   By format: {dict(curated['by_format'])}")
    print(f"   Collections: {list(curated['collections'].keys())}")
    
    # Test reading list
    reading_list = await librarian.create_reading_list(
        "AI Learning Path",
        [mock_posts[0]],
        "Essential AI tutorials and guides"
    )
    
    print(f"\n📖 Reading List Created:")
    print(f"   Name: {reading_list['name']}")
    print(f"   Items: {reading_list['progress']['total']}")
    
    # Test thematic digest
    digest = await librarian.create_thematic_digest("This Week in Tech", mock_posts)
    
    print(f"\n📬 Thematic Digest:\n")
    print(digest)
    
    print("\n✅ Librarian agent working!")


if __name__ == "__main__":
    asyncio.run(test_librarian())
