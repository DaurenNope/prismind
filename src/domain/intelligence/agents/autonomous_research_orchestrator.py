#!/usr/bin/env python3
"""
Autonomous Research Orchestrator
Automatically identifies content needing research and orchestrates multi-source discovery
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.agents.enhanced_research_agent import EnhancedResearchAgent
from src.research.academic_research import AcademicResearchEngine
from src.research.semantic_search import SemanticSearchEngine
from src.services.new_database_manager import get_database_manager

logger = logging.getLogger(__name__)


class AutonomousResearchOrchestrator:
    """
    Orchestrates autonomous research pipeline:
    1. Analyzes collected content to identify research opportunities
    2. Automatically researches topics
    3. Discovers related content from multiple sources
    4. Synthesizes knowledge
    5. Updates database with findings
    """
    
    def __init__(self):
        self.research_agent = EnhancedResearchAgent()
        self.academic_engine = AcademicResearchEngine()
        self.db = get_database_manager()
        self.min_research_score = 7.0  # Only research high-value content
        
    async def process_new_content(self, post_id: str) -> Dict[str, Any]:
        """
        Process newly collected content for autonomous research
        
        Args:
            post_id: ID of the post to process
            
        Returns:
            Dict with research results
        """
        logger.info(f"Processing post {post_id} for autonomous research")
        
        # Get post from database
        post = self.db.get_post_by_id(post_id)
        if not post:
            logger.warning(f"Post {post_id} not found")
            return {}
        
        # Determine if post needs deeper research
        needs_research = self._should_research(post)
        
        if not needs_research:
            logger.info(f"Post {post_id} does not need research (value_score too low)")
            return {"researched": False, "reason": "low_value"}
        
        # Extract research topics from post
        topics = self._extract_research_topics(post)
        
        if not topics:
            logger.info(f"No research topics extracted from post {post_id}")
            return {"researched": False, "reason": "no_topics"}
        
        logger.info(f"Identified {len(topics)} research topics: {topics}")
        
        # Research each topic
        research_results = []
        for topic in topics[:3]:  # Limit to top 3 topics
            try:
                result = await self._research_topic(topic, post)
                if result:
                    research_results.append(result)
            except Exception as e:
                logger.error(f"Research failed for topic '{topic}': {e}")
        
        # Store research findings
        if research_results:
            await self._store_research_findings(post_id, research_results)
        
        return {
            "researched": True,
            "topics": topics,
            "results_count": len(research_results),
            "findings": research_results
        }
    
    def _should_research(self, post: Dict[str, Any]) -> bool:
        """Determine if post is worth deeper research"""
        value_score = post.get("value_score", 0)
        quality_score = post.get("quality_score", 0)
        
        # High value or quality content
        if value_score >= self.min_research_score:
            return True
        if quality_score >= self.min_research_score:
            return True
        
        # Check for research indicators in content
        content = post.get("content", "").lower()
        title = post.get("title", "").lower()
        
        research_keywords = [
            "research", "paper", "study", "findings", "breakthrough",
            "discovery", "analysis", "investigation", "explore", "deep dive"
        ]
        
        combined_text = f"{title} {content}"
        if any(keyword in combined_text for keyword in research_keywords):
            return True
        
        return False
    
    def _extract_research_topics(self, post: Dict[str, Any]) -> List[str]:
        """Extract research topics from post"""
        topics = []
        
        # From AI analysis
        key_concepts = post.get("key_concepts") or []
        if isinstance(key_concepts, str):
            key_concepts = [key_concepts]
        
        topics.extend(key_concepts[:5])
        
        # From tags
        tags = post.get("tags") or []
        if isinstance(tags, str):
            tags = [tags]
        
        # Filter technical/research tags
        research_tags = [
            tag for tag in tags 
            if len(tag) > 3 and not tag.lower() in ["tips", "guide", "tutorial"]
        ]
        topics.extend(research_tags[:3])
        
        # From title if specific enough
        title = post.get("title", "")
        if title and len(title.split()) >= 3:
            # Check if title looks like a research topic
            if any(word in title.lower() for word in ["how", "why", "what", "guide to", "introduction to"]):
                topics.append(title)
        
        # Deduplicate and return
        return list(dict.fromkeys([t for t in topics if t]))[:5]
    
    async def _research_topic(self, topic: str, original_post: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Research a topic using multiple sources
        
        Returns:
            Dict with research findings or None
        """
        logger.info(f"Researching topic: {topic}")
        
        findings = {
            "topic": topic,
            "original_post_id": original_post.get("post_id"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sources": []
        }
        
        # 1. Web research using research agent
        try:
            web_research = await self.research_agent.research(topic)
            if web_research:
                findings["web_research"] = {
                    "summary": web_research.get("summary") or web_research.get("synthesis"),
                    "sources": web_research.get("sources", [])[:5]
                }
                findings["sources"].extend(findings["web_research"]["sources"])
        except Exception as e:
            logger.warning(f"Web research failed for '{topic}': {e}")
        
        # 2. Academic research (if technical topic)
        if self._is_technical_topic(topic):
            try:
                papers = await self.academic_engine.research_academic_topic(topic, max_papers=3)
                if papers:
                    findings["academic_research"] = {
                        "papers": [
                            {
                                "title": p.title,
                                "authors": p.authors,
                                "abstract": p.abstract[:200] + "..." if len(p.abstract) > 200 else p.abstract,
                                "url": p.url,
                                "citations": p.citations
                            }
                            for p in papers
                        ]
                    }
                    findings["sources"].extend([p.url for p in papers])
            except Exception as e:
                logger.warning(f"Academic research failed for '{topic}': {e}")
        
        # 3. Related content from our database
        try:
            related = self._find_related_content(topic, original_post)
            if related:
                findings["related_content"] = related
        except Exception as e:
            logger.warning(f"Related content search failed for '{topic}': {e}")
        
        # Only return if we found something
        if findings["sources"] or findings.get("related_content"):
            return findings
        
        return None
    
    def _is_technical_topic(self, topic: str) -> bool:
        """Check if topic is technical/academic"""
        technical_keywords = [
            "algorithm", "model", "framework", "architecture", "system",
            "api", "protocol", "method", "technique", "approach",
            "machine learning", "ai", "neural", "optimization",
            "security", "cryptography", "blockchain", "quantum"
        ]
        topic_lower = topic.lower()
        return any(keyword in topic_lower for keyword in technical_keywords)
    
    def _find_related_content(self, topic: str, original_post: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find related content from database"""
        # Get posts with similar topics
        all_posts = self.db.get_posts(limit=100)
        
        related = []
        topic_lower = topic.lower()
        
        for post in all_posts:
            # Skip original post
            if post.get("post_id") == original_post.get("post_id"):
                continue
            
            # Check if post is related
            title = (post.get("title") or "").lower()
            content = (post.get("content") or "").lower()
            tags = post.get("tags") or []
            
            if isinstance(tags, list):
                tags_str = " ".join(str(t).lower() for t in tags)
            else:
                tags_str = str(tags).lower()
            
            combined = f"{title} {content} {tags_str}"
            
            if topic_lower in combined:
                related.append({
                    "post_id": post.get("post_id"),
                    "title": post.get("title"),
                    "url": post.get("url"),
                    "platform": post.get("platform"),
                    "value_score": post.get("value_score")
                })
            
            if len(related) >= 5:
                break
        
        return related
    
    async def _store_research_findings(self, post_id: str, findings: List[Dict[str, Any]]):
        """Store research findings in database"""
        try:
            # Update post with research metadata
            research_data = {
                "researched": True,
                "research_timestamp": datetime.now(timezone.utc).isoformat(),
                "research_topics": [f["topic"] for f in findings],
                "research_sources_count": sum(len(f.get("sources", [])) for f in findings)
            }
            
            # Store findings separately (could be separate table in future)
            logger.info(f"Stored research findings for post {post_id}: {len(findings)} topics")
            
            # For now, append to insights or create research field
            post = self.db.get_post_by_id(post_id)
            if post:
                insights = post.get("insights", []) or []
                if not isinstance(insights, list):
                    insights = []
                
                # Add research summary to insights
                for finding in findings:
                    topic = finding["topic"]
                    sources_count = len(finding.get("sources", []))
                    insights.append(f"Researched: {topic} ({sources_count} sources found)")
                
                # Update post
                self.db.update_post(post_id, {
                    "insights": insights[:10],  # Limit insights
                    **research_data
                })
                
        except Exception as e:
            logger.error(f"Failed to store research findings: {e}")
    
    async def process_batch(self, post_ids: List[str]) -> Dict[str, Any]:
        """Process multiple posts for research"""
        results = []
        
        for post_id in post_ids:
            try:
                result = await self.process_new_content(post_id)
                results.append({
                    "post_id": post_id,
                    "success": result.get("researched", False),
                    "result": result
                })
            except Exception as e:
                logger.error(f"Failed to process post {post_id}: {e}")
                results.append({
                    "post_id": post_id,
                    "success": False,
                    "error": str(e)
                })
        
        researched_count = sum(1 for r in results if r["success"])
        
        return {
            "total": len(post_ids),
            "researched": researched_count,
            "results": results
        }
    
    async def auto_research_recent(self, limit: int = 10) -> Dict[str, Any]:
        """
        Automatically research recent high-value posts that haven't been researched
        
        This is the main entry point for automated research
        """
        logger.info(f"Starting automatic research for up to {limit} posts")
        
        # Get recent posts
        posts = self.db.get_posts(limit=limit * 3)  # Get more to filter
        
        # Filter to unresearched high-value posts
        unresearched = [
            p for p in posts
            if not p.get("researched") and (
                (p.get("value_score") or 0) >= self.min_research_score or
                (p.get("quality_score") or 0) >= self.min_research_score
            )
        ][:limit]
        
        if not unresearched:
            logger.info("No posts need research")
            return {"researched": 0, "message": "No posts need research"}
        
        logger.info(f"Found {len(unresearched)} posts for research")
        
        # Process batch
        post_ids = [p.get("post_id") for p in unresearched if p.get("post_id")]
        return await self.process_batch(post_ids)


# Singleton instance
_orchestrator = None

def get_research_orchestrator() -> AutonomousResearchOrchestrator:
    """Get singleton orchestrator instance"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AutonomousResearchOrchestrator()
    return _orchestrator
