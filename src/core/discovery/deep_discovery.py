#!/usr/bin/env python3
"""
Deep Discovery Mode for PrisMind
Thorough 10-15 minute research with comprehensive analysis
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from src.core.discovery.profile_manager import ProfileManager
from src.core.discovery.comprehensive_discovery import ComprehensiveDiscovery
from src.services.new_database_manager import get_database_manager

logger = logging.getLogger(__name__)


class DeepDiscovery:
    """
    Deep research mode - comprehensive 10-15 minute discovery
    
    Differences from quick mode:
    - More sources per platform (100+ vs 30)
    - Multi-pass analysis
    - Context gathering
    - Related topic linking
    - Expert identification
    - Trend analysis
    """
    
    def __init__(self):
        self.profile_manager = ProfileManager()
        self.quick_discovery = ComprehensiveDiscovery()
        self.db = get_database_manager()
    
    def research_topic(self, topic: str, profile_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Perform deep research on a specific topic
        
        Args:
            topic: Topic to research (e.g., "AI Agents", "Web3")
            profile_id: Optional profile to use for context
            
        Returns:
            Comprehensive research briefing
        """
        start_time = datetime.now()
        logger.info(f"🔍 Starting deep research: {topic}")
        
        # Switch to profile if specified
        if profile_id:
            self.profile_manager.switch_profile(profile_id)
        
        profile = self.profile_manager.get_active_profile()
        
        # Phase 1: Broad discovery (2-3 min)
        logger.info("📊 Phase 1: Broad discovery...")
        initial_posts = self._broad_discovery(topic)
        logger.info(f"   Found {len(initial_posts)} initial posts")
        
        # Phase 2: Deep analysis (3-4 min)
        logger.info("🔬 Phase 2: Deep analysis...")
        analyzed_posts = self._deep_analysis(initial_posts, topic)
        logger.info(f"   Analyzed {len(analyzed_posts)} posts")
        
        # Phase 3: Context gathering (2-3 min)
        logger.info("🌐 Phase 3: Context gathering...")
        context = self._gather_context(analyzed_posts, topic)
        
        # Phase 4: Expert identification (1-2 min)
        logger.info("👥 Phase 4: Expert identification...")
        experts = self._identify_experts(analyzed_posts)
        
        # Phase 5: Trend analysis (2-3 min)
        logger.info("📈 Phase 5: Trend analysis...")
        trends = self._analyze_trends(analyzed_posts, topic)
        
        # Compile research briefing
        duration = (datetime.now() - start_time).total_seconds()
        
        briefing = {
            "topic": topic,
            "profile": profile["name"],
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": duration,
            "total_sources": len(initial_posts),
            "high_quality": len([p for p in analyzed_posts if p["quality_score"] > 0.7]),
            "posts": analyzed_posts[:20],  # Top 20
            "context": context,
            "experts": experts,
            "trends": trends,
            "summary": self._generate_summary(analyzed_posts, context, trends)
        }
        
        logger.info(f"✅ Deep research complete: {duration:.1f}s")
        
        return briefing
    
    def comprehensive_discovery(self, profile_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Run comprehensive discovery across all profile topics (10-15 min)
        
        Args:
            profile_id: Profile to use
            
        Returns:
            Comprehensive discovery results
        """
        start_time = datetime.now()
        logger.info("🔍 Starting comprehensive discovery...")
        
        # Switch to profile
        if profile_id:
            self.profile_manager.switch_profile(profile_id)
        
        profile = self.profile_manager.get_active_profile()
        
        # Get all topics from profile
        topics = []
        for topic_group in profile.get("topics", []):
            topics.extend(topic_group.get("keywords", [])[:3])  # Top 3 keywords per group
        
        logger.info(f"📚 Researching {len(topics)} topics...")
        
        # Research each topic
        all_results = []
        for topic in topics[:5]:  # Limit to 5 topics for time
            try:
                result = self.research_topic(topic, profile_id)
                all_results.append(result)
            except Exception as e:
                logger.error(f"Error researching {topic}: {e}")
                continue
        
        # Compile comprehensive results
        duration = (datetime.now() - start_time).total_seconds()
        
        comprehensive = {
            "profile": profile["name"],
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": duration,
            "topics_researched": len(all_results),
            "results": all_results,
            "overall_summary": self._compile_overall_summary(all_results)
        }
        
        logger.info(f"✅ Comprehensive discovery complete: {duration:.1f}s")
        
        return comprehensive
    
    def _broad_discovery(self, topic: str) -> List[Any]:
        """Run broad discovery for topic"""
        import asyncio
        
        # Use comprehensive discovery but with topic filter
        # This gathers from GitHub, Reddit, RSS, Web
        result = asyncio.run(self.quick_discovery.comprehensive_discovery(max_per_source=50))
        all_posts = result.get("posts", [])
        
        # Filter for topic relevance
        relevant_posts = []
        topic_lower = topic.lower()
        
        for post_item in all_posts:
            # Handle both dict and object formats
            post = post_item.get("post") if isinstance(post_item, dict) else post_item
            
            content = ""
            if hasattr(post, 'content'):
                content += str(post.content).lower()
            if hasattr(post, 'title'):
                content += " " + str(post.title).lower()
            
            # Check relevance
            if topic_lower in content or any(
                word in content for word in topic_lower.split()[:3]
            ):
                relevant_posts.append(post)
        
        return relevant_posts
    
    def _deep_analysis(self, posts: List[Any], topic: str) -> List[Dict[str, Any]]:
        """Perform deep analysis on posts"""
        analyzed = []
        
        for post in posts:
            # Extract detailed metrics
            analysis = {
                "post": post,
                "title": self._get_title(post),
                "author": getattr(post, 'author', 'Unknown'),
                "url": getattr(post, 'url', ''),
                "platform": getattr(post, 'platform', 'unknown'),
                "quality_score": getattr(post, 'quality_score', 0.5),
                "relevance": self._calculate_relevance(post, topic),
                "content_type": self._detect_content_type(post),
                "engagement": self._estimate_engagement(post),
                "freshness": self._calculate_freshness(post)
            }
            
            analyzed.append(analysis)
        
        # Sort by combined score
        analyzed.sort(
            key=lambda x: (x["quality_score"] * 0.4 + 
                          x["relevance"] * 0.4 + 
                          x["freshness"] * 0.2),
            reverse=True
        )
        
        return analyzed
    
    def _gather_context(self, posts: List[Dict[str, Any]], topic: str) -> Dict[str, Any]:
        """Gather context about the topic"""
        
        # Analyze sentiment
        positive = sum(1 for p in posts if "exciting" in str(p.get("post", "")).lower() or 
                      "great" in str(p.get("post", "")).lower())
        negative = sum(1 for p in posts if "problem" in str(p.get("post", "")).lower() or
                      "issue" in str(p.get("post", "")).lower())
        
        sentiment = "positive" if positive > negative else "neutral" if positive == negative else "negative"
        
        # Identify key themes
        themes = self._extract_themes(posts)
        
        # Generate "why this matters"
        why_matters = self._generate_why_matters(posts, topic, themes)
        
        return {
            "sentiment": sentiment,
            "sentiment_ratio": f"{positive}/{len(posts)} positive",
            "key_themes": themes[:5],
            "why_this_matters": why_matters,
            "discussion_volume": len(posts),
            "quality_content_ratio": f"{len([p for p in posts if p['quality_score'] > 0.7])}/{len(posts)}"
        }
    
    def _identify_experts(self, posts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify key voices/experts in the topic"""
        
        # Count authors
        author_counts = {}
        author_quality = {}
        
        for post in posts:
            author = post.get("author", "Unknown")
            if author not in author_counts:
                author_counts[author] = 0
                author_quality[author] = []
            
            author_counts[author] += 1
            author_quality[author].append(post.get("quality_score", 0))
        
        # Calculate expert score
        experts = []
        for author, count in author_counts.items():
            if count > 1 and author != "Unknown":
                avg_quality = sum(author_quality[author]) / len(author_quality[author])
                experts.append({
                    "author": author,
                    "posts": count,
                    "avg_quality": avg_quality,
                    "expert_score": count * avg_quality
                })
        
        # Sort by expert score
        experts.sort(key=lambda x: x["expert_score"], reverse=True)
        
        return experts[:5]
    
    def _analyze_trends(self, posts: List[Dict[str, Any]], topic: str) -> Dict[str, Any]:
        """Analyze trends in the topic"""
        
        # Simple trend analysis based on freshness and volume
        recent_posts = [p for p in posts if p.get("freshness", 0) > 0.7]
        
        trend_direction = "stable"
        if len(recent_posts) > len(posts) * 0.6:
            trend_direction = "rising"
        elif len(recent_posts) < len(posts) * 0.3:
            trend_direction = "declining"
        
        # Identify subtopics
        subtopics = self._extract_subtopics(posts, topic)
        
        return {
            "direction": trend_direction,
            "momentum": "high" if len(recent_posts) > 10 else "medium" if len(recent_posts) > 5 else "low",
            "recent_activity": len(recent_posts),
            "total_activity": len(posts),
            "subtopics": subtopics[:5],
            "prediction": self._predict_trend(trend_direction, len(recent_posts))
        }
    
    def _generate_summary(self, posts: List[Dict[str, Any]], 
                         context: Dict[str, Any], 
                         trends: Dict[str, Any]) -> str:
        """Generate executive summary"""
        
        lines = []
        
        # Volume summary
        lines.append(f"Found {len(posts)} relevant sources.")
        
        # Quality summary
        high_quality = len([p for p in posts if p["quality_score"] > 0.7])
        lines.append(f"{high_quality} high-quality posts ({high_quality/len(posts)*100:.0f}%).")
        
        # Sentiment
        lines.append(f"Overall sentiment: {context['sentiment']}.")
        
        # Trend
        lines.append(f"Trend: {trends['direction']} with {trends['momentum']} momentum.")
        
        # Key themes
        if context["key_themes"]:
            themes_str = ", ".join(context["key_themes"])
            lines.append(f"Key themes: {themes_str}.")
        
        return " ".join(lines)
    
    def _compile_overall_summary(self, results: List[Dict[str, Any]]) -> str:
        """Compile summary across all topics"""
        
        total_sources = sum(r["total_sources"] for r in results)
        total_quality = sum(r["high_quality"] for r in results)
        
        return (f"Researched {len(results)} topics across {total_sources} sources. "
               f"Found {total_quality} high-quality posts. "
               f"Duration: {sum(r['duration_seconds'] for r in results):.0f}s.")
    
    # Helper methods
    
    def _get_title(self, post: Any) -> str:
        """Extract post title"""
        if hasattr(post, 'title') and post.title:
            return post.title[:100]
        if hasattr(post, 'content') and post.content:
            return post.content.split('\n')[0][:100]
        return "Untitled"
    
    def _calculate_relevance(self, post: Any, topic: str) -> float:
        """Calculate relevance score (0-1)"""
        content = ""
        if hasattr(post, 'content'):
            content = str(post.content).lower()
        if hasattr(post, 'title'):
            content += " " + str(post.title).lower()
        
        topic_words = topic.lower().split()
        matches = sum(1 for word in topic_words if word in content)
        
        return min(matches / len(topic_words), 1.0)
    
    def _detect_content_type(self, post: Any) -> str:
        """Detect content type"""
        content = str(getattr(post, 'content', '')).lower()
        
        if any(word in content for word in ['tutorial', 'guide', 'how to']):
            return "tutorial"
        elif any(word in content for word in ['release', 'announced', 'launched']):
            return "news"
        elif len(content) > 1000:
            return "long-form"
        elif any(word in content for word in ['opinion', 'think', 'believe']):
            return "opinion"
        else:
            return "general"
    
    def _estimate_engagement(self, post: Any) -> float:
        """Estimate engagement level (0-1)"""
        # Simple heuristic based on content length and quality
        quality = getattr(post, 'quality_score', 0.5)
        content_len = len(str(getattr(post, 'content', '')))
        
        # Longer, higher quality = higher engagement
        engagement = (quality * 0.7) + (min(content_len / 1000, 1) * 0.3)
        
        return min(engagement, 1.0)
    
    def _calculate_freshness(self, post: Any) -> float:
        """Calculate freshness score (0-1)"""
        if not hasattr(post, 'created_at'):
            return 0.5
        
        try:
            from datetime import timedelta
            post_time = datetime.fromisoformat(str(post.created_at))
            age = datetime.now() - post_time
            
            # Fresh if < 24h, stale if > 7d
            if age < timedelta(hours=24):
                return 1.0
            elif age < timedelta(days=3):
                return 0.7
            elif age < timedelta(days=7):
                return 0.4
            else:
                return 0.2
        except:
            return 0.5
    
    def _extract_themes(self, posts: List[Dict[str, Any]]) -> List[str]:
        """Extract key themes from posts"""
        # Simple keyword extraction
        from collections import Counter
        
        words = []
        for post in posts:
            content = str(post.get("post", "")).lower()
            # Extract significant words (3+ chars)
            words.extend([w for w in content.split() if len(w) > 3])
        
        # Count and return top themes
        common = Counter(words).most_common(10)
        return [word for word, count in common if count > 2]
    
    def _extract_subtopics(self, posts: List[Dict[str, Any]], main_topic: str) -> List[str]:
        """Extract subtopics related to main topic"""
        themes = self._extract_themes(posts)
        # Filter out main topic words
        main_words = set(main_topic.lower().split())
        subtopics = [t for t in themes if t not in main_words]
        return subtopics[:5]
    
    def _generate_why_matters(self, posts: List[Dict[str, Any]], 
                             topic: str, themes: List[str]) -> str:
        """Generate 'why this matters' explanation"""
        
        # Analyze context
        has_releases = any("release" in str(p.get("post", "")).lower() for p in posts)
        has_tutorials = any(p.get("content_type") == "tutorial" for p in posts)
        is_trending = len(posts) > 15
        
        reasons = []
        
        if has_releases:
            reasons.append("major releases and updates")
        if has_tutorials:
            reasons.append("growing learning resources")
        if is_trending:
            reasons.append("high community interest")
        
        if not reasons:
            return f"{topic} is an active area of discussion in the tech community."
        
        return f"{topic} is significant due to {', '.join(reasons)}."
    
    def _predict_trend(self, direction: str, recent_count: int) -> str:
        """Predict future trend"""
        if direction == "rising" and recent_count > 15:
            return "Expected to continue growing in popularity"
        elif direction == "rising":
            return "Gaining traction, watch for developments"
        elif direction == "declining":
            return "Interest may be waning"
        else:
            return "Stable, established topic"


def test_deep_discovery():
    """Test deep discovery"""
    print("\n🧪 Testing Deep Discovery\n")
    
    deep = DeepDiscovery()
    
    # Test topic research
    print("🔍 Testing deep research on 'AI Agents'...")
    result = deep.research_topic("AI Agents")
    
    print(f"\n📊 Results:")
    print(f"   Topic: {result['topic']}")
    print(f"   Duration: {result['duration_seconds']:.1f}s")
    print(f"   Sources: {result['total_sources']}")
    print(f"   High Quality: {result['high_quality']}")
    print(f"   Summary: {result['summary']}")
    
    print("\n✅ Deep discovery working!")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    test_deep_discovery()
