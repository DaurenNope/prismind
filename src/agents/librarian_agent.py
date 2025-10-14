#!/usr/bin/env python3
"""
Librarian Agent - Intelligent Content Curation and Organization
Automatically organizes, tags, categorizes, and curates collected content
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from collections import defaultdict

from src.services.new_database_manager import get_database_manager

logger = logging.getLogger(__name__)


class LibrarianAgent:
    """
    Intelligent content curation agent that:
    1. Organizes content into collections
    2. Creates smart categories and tags
    3. Identifies content patterns
    4. Builds knowledge graphs
    5. Curates personalized reading lists
    """
    
    def __init__(self):
        self.db = get_database_manager()
        
    def organize_content(self, limit: int = 100) -> Dict[str, Any]:
        """Organize recent content into categories"""
        logger.info(f"Organizing up to {limit} posts")
        
        posts = self.db.get_posts(limit=limit)
        
        # Categorize by topic
        categories = self._categorize_by_topic(posts)
        
        # Identify patterns
        patterns = self._identify_patterns(posts)
        
        # Create collections
        collections = self._create_collections(posts, categories)
        
        # Build knowledge graph
        knowledge_graph = self._build_knowledge_graph(posts)
        
        return {
            "total_posts": len(posts),
            "categories": categories,
            "patterns": patterns,
            "collections": collections,
            "knowledge_graph_nodes": len(knowledge_graph)
        }
    
    def _categorize_by_topic(self, posts: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Categorize posts by topic"""
        categories = defaultdict(list)
        
        # Common tech categories
        category_keywords = {
            "AI/ML": ["ai", "machine learning", "neural", "llm", "gpt", "model", "training"],
            "Development": ["code", "programming", "developer", "api", "framework"],
            "DevOps": ["docker", "kubernetes", "ci/cd", "deployment", "infrastructure"],
            "Security": ["security", "vulnerability", "encryption", "authentication"],
            "Data": ["database", "sql", "data", "analytics", "visualization"],
            "Frontend": ["react", "vue", "angular", "ui", "css", "html"],
            "Backend": ["api", "server", "backend", "microservices"],
            "Mobile": ["ios", "android", "mobile", "flutter", "react native"],
            "Cloud": ["aws", "azure", "gcp", "cloud", "serverless"],
            "Research": ["paper", "research", "study", "findings", "arxiv"]
        }
        
        for post in posts:
            post_id = post.get("post_id")
            content = f"{post.get('title', '')} {post.get('content', '')}".lower()
            tags = post.get("tags", []) or []
            if isinstance(tags, str):
                tags = [tags]
            
            matched_categories = []
            
            # Match by keywords
            for category, keywords in category_keywords.items():
                if any(kw in content for kw in keywords):
                    matched_categories.append(category)
                    categories[category].append(post_id)
            
            # Match by tags
            for tag in tags:
                tag_lower = str(tag).lower()
                for category, keywords in category_keywords.items():
                    if tag_lower in keywords or any(kw in tag_lower for kw in keywords):
                        if post_id not in categories[category]:
                            matched_categories.append(category)
                            categories[category].append(post_id)
            
            # If no category matched, use platform as category
            if not matched_categories:
                platform = post.get("platform", "Uncategorized")
                categories[platform].append(post_id)
        
        return dict(categories)
    
    def _identify_patterns(self, posts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Identify patterns in collected content"""
        patterns = {
            "trending_topics": [],
            "active_authors": [],
            "peak_collection_times": [],
            "platform_preferences": {}
        }
        
        # Trending topics (based on frequency)
        topic_counts = defaultdict(int)
        for post in posts:
            tags = post.get("tags", []) or []
            if isinstance(tags, str):
                tags = [tags]
            for tag in tags:
                topic_counts[str(tag)] += 1
        
        patterns["trending_topics"] = sorted(
            topic_counts.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:10]
        
        # Active authors
        author_counts = defaultdict(int)
        for post in posts:
            author = post.get("author")
            if author:
                author_counts[author] += 1
        
        patterns["active_authors"] = sorted(
            author_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        # Platform preferences
        platform_counts = defaultdict(int)
        for post in posts:
            platform = post.get("platform", "unknown")
            platform_counts[platform] += 1
        
        patterns["platform_preferences"] = dict(platform_counts)
        
        return patterns
    
    def _create_collections(self, posts: List[Dict[str, Any]], categories: Dict[str, List[str]]) -> List[Dict[str, Any]]:
        """Create smart collections"""
        collections = []
        
        # High-value collection
        high_value_posts = [
            p for p in posts 
            if (p.get("value_score") or 0) >= 8
        ]
        if high_value_posts:
            collections.append({
                "name": "High Value Content",
                "description": "Posts with value score >= 8",
                "count": len(high_value_posts),
                "post_ids": [p.get("post_id") for p in high_value_posts]
            })
        
        # Recent quality content
        quality_posts = [
            p for p in posts[:20]
            if (p.get("quality_score") or 0) >= 7
        ]
        if quality_posts:
            collections.append({
                "name": "Recent Quality Posts",
                "description": "Recent posts with quality score >= 7",
                "count": len(quality_posts),
                "post_ids": [p.get("post_id") for p in quality_posts]
            })
        
        # Category-based collections
        for category, post_ids in categories.items():
            if len(post_ids) >= 3:  # Only create collection if enough posts
                collections.append({
                    "name": f"{category} Collection",
                    "description": f"Posts categorized as {category}",
                    "count": len(post_ids),
                    "post_ids": post_ids[:20]  # Limit size
                })
        
        return collections
    
    def _build_knowledge_graph(self, posts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build knowledge graph from content"""
        graph = {
            "nodes": [],
            "edges": []
        }
        
        # Create nodes for posts
        for post in posts[:50]:  # Limit for performance
            post_id = post.get("post_id")
            tags = post.get("tags", []) or []
            if isinstance(tags, str):
                tags = [tags]
            
            graph["nodes"].append({
                "id": post_id,
                "type": "post",
                "title": post.get("title", "")[:50],
                "tags": tags
            })
            
            # Create edges between posts sharing tags
            for other_post in posts:
                if other_post.get("post_id") == post_id:
                    continue
                
                other_tags = other_post.get("tags", []) or []
                if isinstance(other_tags, str):
                    other_tags = [other_tags]
                
                # If they share tags, create edge
                shared_tags = set(str(t) for t in tags) & set(str(t) for t in other_tags)
                if shared_tags:
                    graph["edges"].append({
                        "from": post_id,
                        "to": other_post.get("post_id"),
                        "weight": len(shared_tags),
                        "shared_tags": list(shared_tags)
                    })
        
        return graph
    
    def curate_reading_list(self, preferences: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Curate personalized reading list"""
        posts = self.db.get_posts(limit=100)
        
        # Default preferences if none provided
        if not preferences:
            preferences = {
                "min_value_score": 7,
                "min_quality_score": 6,
                "preferred_topics": [],
                "preferred_platforms": []
            }
        
        reading_list = []
        
        for post in posts:
            score = 0
            
            # Value score
            value = post.get("value_score") or 0
            if value >= preferences.get("min_value_score", 7):
                score += value
            
            # Quality score
            quality = post.get("quality_score") or 0
            if quality >= preferences.get("min_quality_score", 6):
                score += quality
            
            # Preferred topics
            tags = post.get("tags", []) or []
            if isinstance(tags, str):
                tags = [tags]
            
            preferred_topics = preferences.get("preferred_topics", [])
            if preferred_topics:
                topic_matches = sum(
                    1 for tag in tags 
                    if any(pref.lower() in str(tag).lower() for pref in preferred_topics)
                )
                score += topic_matches * 2
            
            # Preferred platforms
            platform = post.get("platform", "")
            preferred_platforms = preferences.get("preferred_platforms", [])
            if platform in preferred_platforms:
                score += 1
            
            if score > 0:
                reading_list.append({
                    "post": post,
                    "curation_score": score
                })
        
        # Sort by curation score
        reading_list.sort(key=lambda x: x["curation_score"], reverse=True)
        
        return reading_list[:20]  # Top 20
    
    def auto_tag_content(self, post_id: str) -> List[str]:
        """Automatically generate tags for content"""
        post = self.db.get_post_by_id(post_id)
        if not post:
            return []
        
        auto_tags = set()
        
        content = f"{post.get('title', '')} {post.get('content', '')}".lower()
        
        # Technical keywords
        tech_tags = {
            "python": ["python", "py", "django", "flask"],
            "javascript": ["javascript", "js", "node", "react", "vue"],
            "ai": ["ai", "artificial intelligence", "machine learning", "ml"],
            "web": ["web", "html", "css", "frontend", "backend"],
            "cloud": ["cloud", "aws", "azure", "gcp"],
            "devops": ["devops", "docker", "kubernetes", "ci/cd"],
            "security": ["security", "vulnerability", "encryption"]
        }
        
        for tag, keywords in tech_tags.items():
            if any(kw in content for kw in keywords):
                auto_tags.add(tag)
        
        # Add existing tags
        existing_tags = post.get("tags", []) or []
        if isinstance(existing_tags, str):
            existing_tags = [existing_tags]
        
        auto_tags.update(str(t) for t in existing_tags)
        
        return list(auto_tags)


# Singleton instance
_librarian = None

def get_librarian_agent() -> LibrarianAgent:
    """Get singleton librarian instance"""
    global _librarian
    if _librarian is None:
        _librarian = LibrarianAgent()
    return _librarian
