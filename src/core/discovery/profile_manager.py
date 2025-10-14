#!/usr/bin/env python3
"""
Profile Manager for PrisMind
Manage multiple personas/profiles with different topics and preferences
"""

import json
from typing import List, Dict, Any, Optional
from datetime import datetime


class ProfileManager:
    """Manage multiple user profiles/personas for content discovery"""
    
    def __init__(self, config_file: str = "config/profiles.json"):
        self.config_file = config_file
        self.profiles = self._load_profiles()
        self.active_profile = self._get_default_profile()
    
    def _load_profiles(self) -> Dict[str, Any]:
        """Load profiles from config"""
        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return self._get_default_profiles()
    
    def _get_default_profiles(self) -> Dict[str, Any]:
        """Default profiles configuration"""
        return {
            "profiles": [
                {
                    "id": "work",
                    "name": "Work & Professional",
                    "emoji": "💼",
                    "topics": [
                        {
                            "id": "ai_ml_deep",
                            "name": "AI & Machine Learning (Deep)",
                            "keywords": [
                                "artificial intelligence", "machine learning", "deep learning",
                                "neural networks", "transformers", "LLM", "language model",
                                "GPT", "Claude", "diffusion models", "reinforcement learning",
                                "AI agents", "autonomous systems", "research paper"
                            ],
                            "priority": "high"
                        },
                        {
                            "id": "dev_tools_pro",
                            "name": "Developer Tools & Infrastructure",
                            "keywords": [
                                "developer tools", "devtools", "IDE", "VSCode", "Cursor",
                                "CI/CD", "docker", "kubernetes", "cloud infrastructure",
                                "API", "SDK", "framework", "library", "open source"
                            ],
                            "priority": "high"
                        },
                        {
                            "id": "tech_architecture",
                            "name": "System Design & Architecture",
                            "keywords": [
                                "system design", "architecture", "scalability", "performance",
                                "distributed systems", "microservices", "database design",
                                "engineering best practices", "technical leadership"
                            ],
                            "priority": "medium"
                        }
                    ],
                    "quality_threshold": 0.6,
                    "max_daily_posts": 30,
                    "enabled": True
                },
                {
                    "id": "startup",
                    "name": "Startup & Business",
                    "emoji": "🚀",
                    "topics": [
                        {
                            "id": "startup_funding",
                            "name": "Startup Funding & VC",
                            "keywords": [
                                "startup", "venture capital", "VC", "funding", "seed round",
                                "series A", "YC", "Y Combinator", "accelerator", "pitch deck",
                                "valuation", "exit", "acquisition", "IPO"
                            ],
                            "priority": "high"
                        },
                        {
                            "id": "product_market",
                            "name": "Product & Market Strategy",
                            "keywords": [
                                "product market fit", "go-to-market", "GTM", "growth hacking",
                                "user acquisition", "retention", "metrics", "KPI", "SaaS",
                                "business model", "monetization", "pricing strategy"
                            ],
                            "priority": "high"
                        },
                        {
                            "id": "founder_stories",
                            "name": "Founder Stories & Lessons",
                            "keywords": [
                                "founder", "entrepreneurship", "startup journey", "lessons learned",
                                "failure", "pivot", "bootstrapping", "indie hacker",
                                "building in public", "zero to one"
                            ],
                            "priority": "medium"
                        }
                    ],
                    "quality_threshold": 0.5,
                    "max_daily_posts": 25,
                    "enabled": True
                },
                {
                    "id": "learning",
                    "name": "Learning & Education",
                    "emoji": "📚",
                    "topics": [
                        {
                            "id": "tutorials",
                            "name": "Tutorials & Guides",
                            "keywords": [
                                "tutorial", "guide", "how to", "learn", "course",
                                "beginner", "introduction", "getting started",
                                "step by step", "walkthrough", "example"
                            ],
                            "priority": "high"
                        },
                        {
                            "id": "cs_fundamentals",
                            "name": "CS Fundamentals",
                            "keywords": [
                                "algorithms", "data structures", "computer science",
                                "programming fundamentals", "complexity", "optimization",
                                "theory", "mathematics", "cryptography"
                            ],
                            "priority": "medium"
                        },
                        {
                            "id": "career_growth",
                            "name": "Career & Skills",
                            "keywords": [
                                "career", "career growth", "skills", "learning path",
                                "interview prep", "coding interview", "job search",
                                "resume", "portfolio", "networking"
                            ],
                            "priority": "medium"
                        }
                    ],
                    "quality_threshold": 0.4,
                    "max_daily_posts": 20,
                    "enabled": True
                },
                {
                    "id": "trends",
                    "name": "Tech Trends & News",
                    "emoji": "📰",
                    "topics": [
                        {
                            "id": "tech_news",
                            "name": "Tech News & Updates",
                            "keywords": [
                                "tech news", "technology", "announcement", "release",
                                "launch", "update", "breaking", "industry news",
                                "company news", "acquisition", "partnership"
                            ],
                            "priority": "medium"
                        },
                        {
                            "id": "emerging_tech",
                            "name": "Emerging Technologies",
                            "keywords": [
                                "emerging tech", "future", "innovation", "breakthrough",
                                "quantum computing", "AR", "VR", "web3", "blockchain",
                                "robotics", "biotech", "space tech"
                            ],
                            "priority": "low"
                        }
                    ],
                    "quality_threshold": 0.4,
                    "max_daily_posts": 15,
                    "enabled": True
                }
            ],
            "default_profile": "work"
        }
    
    def save_profiles(self):
        """Save profiles to config"""
        import os
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        
        with open(self.config_file, 'w') as f:
            json.dump(self.profiles, f, indent=2)
    
    def get_profile(self, profile_id: str) -> Optional[Dict[str, Any]]:
        """Get specific profile"""
        for profile in self.profiles.get("profiles", []):
            if profile.get("id") == profile_id:
                return profile
        return None
    
    def get_active_profile(self) -> Dict[str, Any]:
        """Get currently active profile"""
        if self.active_profile:
            return self.active_profile
        return self._get_default_profile()
    
    def _get_default_profile(self) -> Dict[str, Any]:
        """Get default profile"""
        default_id = self.profiles.get("default_profile", "work")
        return self.get_profile(default_id) or self.profiles.get("profiles", [{}])[0]
    
    def set_active_profile(self, profile_id: str) -> bool:
        """Switch to a different profile"""
        profile = self.get_profile(profile_id)
        if profile:
            self.active_profile = profile
            return True
        return False
    
    def list_profiles(self) -> List[Dict[str, Any]]:
        """List all available profiles"""
        return [
            {
                "id": p.get("id"),
                "name": p.get("name"),
                "emoji": p.get("emoji"),
                "topic_count": len(p.get("topics", [])),
                "enabled": p.get("enabled", True)
            }
            for p in self.profiles.get("profiles", [])
        ]
    
    def get_keywords_for_profile(self, profile_id: Optional[str] = None) -> List[str]:
        """Get all keywords for a profile"""
        if profile_id:
            profile = self.get_profile(profile_id)
        else:
            profile = self.get_active_profile()
        
        if not profile:
            return []
        
        keywords = []
        for topic in profile.get("topics", []):
            keywords.extend(topic.get("keywords", []))
        
        return keywords
    
    def get_quality_threshold(self, profile_id: Optional[str] = None) -> float:
        """Get quality threshold for profile"""
        if profile_id:
            profile = self.get_profile(profile_id)
        else:
            profile = self.get_active_profile()
        
        return profile.get("quality_threshold", 0.5) if profile else 0.5
    
    def get_max_daily_posts(self, profile_id: Optional[str] = None) -> int:
        """Get max daily posts for profile"""
        if profile_id:
            profile = self.get_profile(profile_id)
        else:
            profile = self.get_active_profile()
        
        return profile.get("max_daily_posts", 50) if profile else 50
    
    def create_profile(self, profile_id: str, name: str, emoji: str, topics: List[Dict]) -> bool:
        """Create a new profile"""
        # Check if profile already exists
        if self.get_profile(profile_id):
            return False
        
        new_profile = {
            "id": profile_id,
            "name": name,
            "emoji": emoji,
            "topics": topics,
            "quality_threshold": 0.5,
            "max_daily_posts": 30,
            "enabled": True
        }
        
        self.profiles.setdefault("profiles", []).append(new_profile)
        self.save_profiles()
        return True
    
    def get_summary(self, profile_id: Optional[str] = None) -> str:
        """Get human-readable summary of profile"""
        if profile_id:
            profile = self.get_profile(profile_id)
        else:
            profile = self.get_active_profile()
        
        if not profile:
            return "No profile found"
        
        lines = [
            f"{profile.get('emoji', '📋')} <b>{profile.get('name')}</b>",
            f"Profile ID: {profile.get('id')}",
            "",
            f"<b>Topics ({len(profile.get('topics', []))}):</b>"
        ]
        
        for topic in profile.get("topics", []):
            priority = topic.get("priority", "medium")
            priority_emoji = {"high": "🔥", "medium": "⭐", "low": "💡"}.get(priority, "⭐")
            
            lines.append(
                f"{priority_emoji} {topic.get('name')} "
                f"({len(topic.get('keywords', []))} keywords)"
            )
        
        lines.append("")
        lines.append(f"Quality threshold: {profile.get('quality_threshold', 0.5)}")
        lines.append(f"Max daily posts: {profile.get('max_daily_posts', 50)}")
        
        return "\n".join(lines)
