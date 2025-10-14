#!/usr/bin/env python3
"""
Discovery Engine for PrisMind
Autonomously finds and curates valuable content
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from src.core.discovery.topic_tracker import TopicTracker
from src.core.extraction.social_extractor_base import SocialPost


class DiscoveryEngine:
    """Autonomous content discovery engine"""
    
    def __init__(self, topic_tracker: Optional[TopicTracker] = None):
        self.topic_tracker = topic_tracker or TopicTracker()
        self.discovered_today = 0
        self.last_discovery = None
    
    def should_discover(self) -> bool:
        """Check if we should run discovery now"""
        max_daily = self.topic_tracker.get_max_daily_posts()
        
        # Check if we've hit daily limit
        if self.discovered_today >= max_daily:
            return False
        
        # Check if enough time has passed (2 hours minimum)
        if self.last_discovery:
            elapsed = datetime.now() - self.last_discovery
            if elapsed < timedelta(hours=2):
                return False
        
        return True
    
    def filter_by_relevance(self, posts: List[SocialPost]) -> List[Dict[str, Any]]:
        """
        Filter posts by topic relevance
        Returns posts with topic match scores
        """
        relevant_posts = []
        
        for post in posts:
            # Combine content for matching
            full_content = f"{post.content}"
            
            # Match to topics
            topic_matches = self.topic_tracker.match_content_to_topics(full_content)
            
            if topic_matches:
                relevant_posts.append({
                    "post": post,
                    "topics": topic_matches,
                    "relevance_score": topic_matches[0]["score"] if topic_matches else 0
                })
        
        # Sort by relevance score
        relevant_posts.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        return relevant_posts
    
    def filter_by_quality(self, posts: List[Dict[str, Any]], 
                         value_scores: Optional[Dict[str, float]] = None) -> List[Dict[str, Any]]:
        """
        Filter posts by quality threshold
        
        Args:
            posts: List of posts with relevance scores
            value_scores: Optional dict of post_id -> value_score
        """
        threshold = self.topic_tracker.get_quality_threshold()
        quality_posts = []
        
        for item in posts:
            post = item["post"]
            post_id = post.post_id or post.id
            
            # Get value score if available
            value_score = 0
            if value_scores and post_id in value_scores:
                value_score = value_scores[post_id]
            
            # Combine relevance and value scores
            combined_score = (item["relevance_score"] * 0.6) + (value_score * 0.4)
            
            if combined_score >= threshold:
                item["quality_score"] = combined_score
                quality_posts.append(item)
        
        return quality_posts
    
    def discover_from_posts(self, posts: List[SocialPost], 
                           value_scores: Optional[Dict[str, float]] = None) -> List[Dict[str, Any]]:
        """
        Main discovery method - filter posts by relevance and quality
        
        Args:
            posts: List of SocialPost objects to evaluate
            value_scores: Optional dict of post_id -> value_score
            
        Returns:
            List of high-quality, relevant posts with metadata
        """
        if not self.should_discover():
            print("⏸️ Discovery paused (daily limit or too soon)")
            return []
        
        print(f"🔍 Discovery: Evaluating {len(posts)} posts...")
        
        # Step 1: Filter by relevance
        relevant = self.filter_by_relevance(posts)
        print(f"   📊 {len(relevant)} relevant posts found")
        
        # Step 2: Filter by quality
        quality = self.filter_by_quality(relevant, value_scores)
        print(f"   ⭐ {len(quality)} high-quality posts")
        
        # Update counters
        self.discovered_today += len(quality)
        self.last_discovery = datetime.now()
        
        # Respect daily limit
        max_daily = self.topic_tracker.get_max_daily_posts()
        if self.discovered_today > max_daily:
            excess = self.discovered_today - max_daily
            quality = quality[:-excess]
            self.discovered_today = max_daily
        
        print(f"   ✅ {len(quality)} posts added to intelligence feed")
        print(f"   📈 Total discovered today: {self.discovered_today}/{max_daily}")
        
        return quality
    
    def get_discovery_stats(self) -> Dict[str, Any]:
        """Get discovery statistics"""
        max_daily = self.topic_tracker.get_max_daily_posts()
        
        return {
            "discovered_today": self.discovered_today,
            "max_daily": max_daily,
            "remaining": max_daily - self.discovered_today,
            "last_discovery": self.last_discovery.isoformat() if self.last_discovery else None,
            "can_discover": self.should_discover()
        }
    
    def reset_daily_counter(self):
        """Reset daily discovery counter (call at midnight)"""
        self.discovered_today = 0
        print("🔄 Daily discovery counter reset")
