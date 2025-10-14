#!/usr/bin/env python3
"""
Topic Tracker for PrisMind
Manages user interests and tracks topics for autonomous discovery
"""

import json
from typing import List, Dict, Any, Optional
from datetime import datetime


class TopicTracker:
    """Track topics of interest for autonomous content discovery"""
    
    def __init__(self, config_file: str = "config/topics.json"):
        self.config_file = config_file
        self.topics = self._load_topics()
    
    def _load_topics(self) -> Dict[str, Any]:
        """Load topics from config file"""
        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            # Default topics if config doesn't exist
            return self._get_default_topics()
    
    def _get_default_topics(self) -> Dict[str, Any]:
        """Default topics for discovery"""
        return {
            "topics": [
                {
                    "id": "ai_ml",
                    "name": "AI & Machine Learning",
                    "keywords": [
                        "artificial intelligence", "machine learning", "AI", "ML",
                        "neural networks", "deep learning", "GPT", "Claude",
                        "LLM", "language model", "AI agents", "transformers"
                    ],
                    "priority": "high",
                    "enabled": True
                },
                {
                    "id": "dev_tools",
                    "name": "Developer Tools",
                    "keywords": [
                        "developer tools", "dev tools", "IDE", "VSCode",
                        "coding assistant", "github copilot", "cursor",
                        "productivity", "automation", "CLI tools"
                    ],
                    "priority": "high",
                    "enabled": True
                },
                {
                    "id": "startups",
                    "name": "Startups & Entrepreneurship",
                    "keywords": [
                        "startup", "entrepreneurship", "founder", "YC",
                        "venture capital", "funding", "product launch",
                        "bootstrapping", "SaaS", "business model"
                    ],
                    "priority": "medium",
                    "enabled": True
                },
                {
                    "id": "web_dev",
                    "name": "Web Development",
                    "keywords": [
                        "react", "nextjs", "typescript", "javascript",
                        "frontend", "backend", "full stack", "web dev",
                        "tailwind", "vercel", "cloudflare"
                    ],
                    "priority": "medium",
                    "enabled": True
                },
                {
                    "id": "tech_trends",
                    "name": "Tech Trends",
                    "keywords": [
                        "tech news", "technology", "innovation",
                        "breakthrough", "disruption", "emerging tech",
                        "future of work", "remote work", "productivity"
                    ],
                    "priority": "low",
                    "enabled": True
                }
            ],
            "quality_threshold": 0.35,
            "max_daily_posts": 50,
            "last_updated": datetime.now().isoformat()
        }
    
    def save_topics(self):
        """Save topics to config file"""
        import os
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        
        self.topics["last_updated"] = datetime.now().isoformat()
        
        with open(self.config_file, 'w') as f:
            json.dump(self.topics, f, indent=2)
    
    def get_enabled_topics(self) -> List[Dict[str, Any]]:
        """Get list of enabled topics"""
        return [t for t in self.topics.get("topics", []) if t.get("enabled", True)]
    
    def get_all_keywords(self) -> List[str]:
        """Get all keywords from enabled topics"""
        keywords = []
        for topic in self.get_enabled_topics():
            keywords.extend(topic.get("keywords", []))
        return keywords
    
    def get_keywords_by_topic(self, topic_id: str) -> List[str]:
        """Get keywords for specific topic"""
        for topic in self.topics.get("topics", []):
            if topic.get("id") == topic_id:
                return topic.get("keywords", [])
        return []
    
    def match_content_to_topics(self, content: str) -> List[Dict[str, Any]]:
        """
        Match content to topics based on keywords
        Returns list of matched topics with scores
        """
        content_lower = content.lower()
        matches = []
        
        for topic in self.get_enabled_topics():
            keyword_matches = 0
            matched_keywords = []
            
            for keyword in topic.get("keywords", []):
                if keyword.lower() in content_lower:
                    keyword_matches += 1
                    matched_keywords.append(keyword)
            
            if keyword_matches > 0:
                # Score based on number of keyword matches
                score = min(1.0, keyword_matches / 3)  # Max score at 3+ keywords
                
                matches.append({
                    "topic_id": topic.get("id"),
                    "topic_name": topic.get("name"),
                    "score": score,
                    "matched_keywords": matched_keywords,
                    "priority": topic.get("priority", "medium")
                })
        
        # Sort by score descending
        matches.sort(key=lambda x: x["score"], reverse=True)
        return matches
    
    def is_relevant(self, content: str) -> bool:
        """Check if content is relevant to any tracked topic"""
        matches = self.match_content_to_topics(content)
        return len(matches) > 0
    
    def get_quality_threshold(self) -> float:
        """Get minimum quality threshold for content"""
        return self.topics.get("quality_threshold", 0.7)
    
    def get_max_daily_posts(self) -> int:
        """Get maximum posts to discover per day"""
        return self.topics.get("max_daily_posts", 50)
    
    def add_topic(self, topic_id: str, name: str, keywords: List[str], 
                  priority: str = "medium", enabled: bool = True):
        """Add a new topic to track"""
        new_topic = {
            "id": topic_id,
            "name": name,
            "keywords": keywords,
            "priority": priority,
            "enabled": enabled
        }
        
        self.topics.setdefault("topics", []).append(new_topic)
        self.save_topics()
    
    def remove_topic(self, topic_id: str):
        """Remove a topic"""
        self.topics["topics"] = [
            t for t in self.topics.get("topics", [])
            if t.get("id") != topic_id
        ]
        self.save_topics()
    
    def toggle_topic(self, topic_id: str, enabled: bool):
        """Enable or disable a topic"""
        for topic in self.topics.get("topics", []):
            if topic.get("id") == topic_id:
                topic["enabled"] = enabled
        self.save_topics()
    
    def get_summary(self) -> str:
        """Get human-readable summary of tracked topics"""
        enabled = self.get_enabled_topics()
        lines = [
            f"📋 Tracking {len(enabled)} topics:",
            ""
        ]
        
        for topic in enabled:
            priority_emoji = {
                "high": "🔥",
                "medium": "⭐",
                "low": "💡"
            }.get(topic.get("priority", "medium"), "⭐")
            
            lines.append(
                f"{priority_emoji} {topic.get('name')} "
                f"({len(topic.get('keywords', []))} keywords)"
            )
        
        lines.append("")
        lines.append(f"Quality threshold: {self.get_quality_threshold()}")
        lines.append(f"Max daily posts: {self.get_max_daily_posts()}")
        
        return "\n".join(lines)
