#!/usr/bin/env python3
"""
Comprehensive Discovery System for PrisMind
Massive multi-source intelligence gathering with AI analysis
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
from src.core.discovery.topic_tracker import TopicTracker
from src.core.discovery.discovery_engine import DiscoveryEngine
from src.core.extraction.social_extractor_base import SocialPost


class ComprehensiveDiscovery:
    """Massive multi-source discovery with research and curation"""
    
    def __init__(self, topic_tracker: Optional[TopicTracker] = None, profile_id: Optional[str] = None):
        self.topic_tracker = topic_tracker or TopicTracker()
        self.discovery_engine = DiscoveryEngine(self.topic_tracker)
        
        # Profile support
        from src.core.discovery.profile_manager import ProfileManager
        self.profile_manager = ProfileManager()
        
        if profile_id:
            self.profile_manager.set_active_profile(profile_id)
        
        self.active_profile = self.profile_manager.get_active_profile()
    
    async def _generate_summary(self, content: str, scorer) -> str:
        """Generate AI summary of content"""
        try:
            import httpx
            
            # Use Ollama for fast summarization
            if scorer.ollama_available:
                prompt = f"""Summarize this content in 2-3 clear sentences. Focus on:
- What is the main point?
- Why does this matter?
- What's the key takeaway?

Content:
{content[:1500]}

Summary:"""
                
                response = httpx.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": "qwen2.5:7b",
                        "prompt": prompt,
                        "stream": False,
                        "options": {"temperature": 0.3, "num_predict": 150}
                    },
                    timeout=15
                )
                
                if response.status_code == 200:
                    result = response.json()
                    summary = result.get("response", "").strip()
                    if summary and len(summary) > 20:
                        return summary
            
            # Fallback to Gemini
            if scorer.gemini_available:
                import google.generativeai as genai
                import os
                
                genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                response = model.generate_content(prompt)
                if response and response.text:
                    return response.text.strip()
            
        except Exception as e:
            print(f"   Summary generation failed: {e}")
        
        # Return first 200 chars as fallback
        return content[:200].replace("\n", " ") + "..."
    
    async def crawl_web_sources(self, keywords: List[str]) -> List[SocialPost]:
        """Crawl web using Crawl4AI"""
        print("🌐 Crawling web sources...")
        
        try:
            from src.core.discovery.web_crawler import WebCrawler
            
            crawler = WebCrawler()
            
            # Crawl specific high-value sites
            web_posts = await crawler.crawl_specific_sites(keywords)
            
            # Close crawler
            await crawler.close()
            
            print(f"   ✅ Found {len(web_posts)} web sources")
            return web_posts
            
        except Exception as e:
            print(f"   ❌ Web crawling error: {e}")
            return []
    
    async def discover_github_trending(self, keywords: List[str]) -> List[SocialPost]:
        """Discover trending GitHub repositories"""
        print("🐙 Discovering GitHub trending...")
        
        try:
            # Use existing GitHub collector
            from scripts.scheduled_github_trending_job import scrape_github_trending
            
            repos = await scrape_github_trending()
            
            posts = []
            for repo in repos:
                # Check if repo matches keywords
                repo_text = f"{repo.get('name', '')} {repo.get('description', '')}".lower()
                
                matches = any(kw.lower() in repo_text for kw in keywords[:20])
                
                if matches:
                    post = SocialPost(
                        post_id=f"github_{repo.get('name', '')}",
                        platform="github",
                        author=repo.get('author', 'Unknown'),
                        author_handle=repo.get('author', 'Unknown'),
                        content=f"{repo.get('name', 'Unknown')}\n\n{repo.get('description', '')}",
                        url=repo.get('url', ''),
                        created_at=datetime.now(),
                        post_type="repository"
                    )
                    posts.append(post)
            
            print(f"   ✅ Found {len(posts)} relevant GitHub repos")
            return posts
            
        except Exception as e:
            print(f"   ❌ GitHub discovery error: {e}")
            return []
    
    async def discover_articles_deep(self, keywords: List[str]) -> List[SocialPost]:
        """Deep article discovery from multiple RSS feeds"""
        print("📰 Deep article discovery...")
        
        try:
            from src.core.extraction.article_extractor import ArticleExtractor
            
            # Expanded RSS feed list
            feeds = [
                "https://news.ycombinator.com/rss",
                "https://www.theverge.com/rss/index.xml",
                "https://techcrunch.com/feed/",
                "https://feeds.arstechnica.com/arstechnica/index",
                "https://www.wired.com/feed/rss",
                "https://rss.slashdot.org/Slashdot/slashdotMain",
                "https://www.reddit.com/r/technology/.rss",
                "https://www.reddit.com/r/programming/.rss",
                "https://www.reddit.com/r/MachineLearning/.rss",
            ]
            
            extractor = ArticleExtractor()
            all_articles = extractor.extract_from_multiple_feeds(feeds, limit_per_feed=10)
            
            # Filter by keywords
            relevant = []
            for article in all_articles:
                content_lower = article.content.lower()
                if any(kw.lower() in content_lower for kw in keywords[:30]):
                    relevant.append(article)
            
            print(f"   ✅ Found {len(relevant)} relevant articles from {len(feeds)} sources")
            return relevant
            
        except Exception as e:
            print(f"   ❌ Article discovery error: {e}")
            return []
    
    async def discover_reddit_deep(self, queries: List[str]) -> List[SocialPost]:
        """Deep Reddit discovery across multiple subreddits"""
        print("🤖 Deep Reddit discovery...")
        
        try:
            import praw
            import os
            
            reddit = praw.Reddit(
                client_id=os.getenv("REDDIT_CLIENT_ID"),
                client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
                user_agent=os.getenv("REDDIT_USER_AGENT", "PrisMind/1.0")
            )
            
            # Expanded subreddit list
            subreddits = [
                "artificial", "MachineLearning", "deeplearning", "LocalLLaMA",
                "programming", "webdev", "javascript", "Python",
                "startups", "Entrepreneur", "SaaS",
                "technology", "Futurology", "coding",
            ]
            
            posts = []
            
            for subreddit_name in subreddits[:8]:  # Search top 8
                try:
                    subreddit = reddit.subreddit(subreddit_name)
                    
                    # Get hot posts
                    for submission in subreddit.hot(limit=10):
                        # Check if matches any query
                        text = f"{submission.title} {submission.selftext}".lower()
                        
                        if any(q.lower() in text for q in queries):
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
                    print(f"   Error in r/{subreddit_name}: {str(e)[:50]}")
                    continue
            
            print(f"   ✅ Found {len(posts)} relevant Reddit posts from {len(subreddits)} subreddits")
            return posts
            
        except Exception as e:
            print(f"   ❌ Reddit discovery error: {e}")
            return []
    
    async def research_trending_topics(self, discovered_posts: List[SocialPost]) -> Dict[str, Any]:
        """Use research agent to analyze discovered content"""
        print("\n🔬 Research Agent: Analyzing trends...")
        
        try:
            from src.agents.enhanced_research_agent import EnhancedResearchAgent
            
            agent = EnhancedResearchAgent()
            
            # Extract trending topics
            topics = {}
            for post in discovered_posts[:50]:  # Analyze top 50
                content = post.content.lower()
                
                # Count mentions
                for topic in self.topic_tracker.get_enabled_topics():
                    topic_name = topic.get("name")
                    keywords = topic.get("keywords", [])
                    
                    mentions = sum(1 for kw in keywords if kw.lower() in content)
                    
                    if mentions > 0:
                        if topic_name not in topics:
                            topics[topic_name] = {"count": 0, "posts": []}
                        topics[topic_name]["count"] += mentions
                        topics[topic_name]["posts"].append(post.post_id)
            
            # Sort by count
            trending = sorted(topics.items(), key=lambda x: x[1]["count"], reverse=True)
            
            # Research top 3 trending topics
            insights = {}
            for topic_name, data in trending[:3]:
                print(f"   Researching: {topic_name} ({data['count']} mentions)")
                
                # Use research agent
                research_result = await agent.research_topic(
                    topic=topic_name,
                    depth="medium"
                )
                
                insights[topic_name] = {
                    "mentions": data["count"],
                    "research": research_result,
                    "related_posts": len(data["posts"])
                }
            
            print(f"   ✅ Completed research on {len(insights)} trending topics")
            return {
                "trending_topics": trending[:10],
                "deep_research": insights
            }
            
        except Exception as e:
            print(f"   ❌ Research error: {e}")
            return {}
    
    async def curate_with_librarian(self, posts: List[Dict[str, Any]]) -> Dict[str, List]:
        """Use librarian agent to organize discovered content"""
        print("\n📚 Librarian Agent: Curating content...")
        
        try:
            from src.agents.librarian_agent import LibrarianAgent
            
            agent = LibrarianAgent()
            
            # Organize by topic and quality
            curated = {
                "must_read": [],
                "interesting": [],
                "reference": [],
                "by_topic": {}
            }
            
            for item in posts:
                post = item["post"]
                quality = item.get("quality_score", 0)
                topics = item.get("topics", [])
                
                # Categorize by quality (lowered thresholds)
                if quality >= 0.65:
                    curated["must_read"].append(item)
                elif quality >= 0.45:
                    curated["interesting"].append(item)
                else:
                    curated["reference"].append(item)
                
                # Organize by topic
                for topic in topics:
                    topic_name = topic.get("topic_name")
                    if topic_name not in curated["by_topic"]:
                        curated["by_topic"][topic_name] = []
                    curated["by_topic"][topic_name].append(item)
            
            print(f"   ✅ Curated: {len(curated['must_read'])} must-read, "
                  f"{len(curated['interesting'])} interesting")
            
            return curated
            
        except Exception as e:
            print(f"   ❌ Curation error: {e}")
            return {"must_read": posts[:10], "interesting": posts[10:], "reference": []}
    
    async def comprehensive_discovery(self, max_per_source: int = 50) -> Dict[str, Any]:
        """
        MASSIVE comprehensive discovery across all sources
        
        Returns:
            Complete intelligence report with:
            - Discovered posts
            - Research insights
            - Curated collections
            - Trending topics
        """
        print("\n" + "="*70)
        print("🚀 COMPREHENSIVE INTELLIGENCE GATHERING")
        print("="*70)
        
        keywords = self.topic_tracker.get_all_keywords()
        queries = [" ".join(kw.split()[:2]) for kw in keywords[:10]]
        
        print(f"\n📋 Tracking: {len(keywords)} keywords")
        print(f"🔎 Using: {len(queries)} search queries\n")
        
        # Parallel discovery from all sources
        print("Phase 1: Multi-Source Discovery")
        print("-"*70)
        
        tasks = [
            self.discover_github_trending(keywords),
            self.discover_articles_deep(keywords),
            self.discover_reddit_deep(queries),
            self.crawl_web_sources(keywords),
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Combine all posts
        all_posts = []
        for result in results:
            if isinstance(result, list):
                all_posts.extend(result)
        
        print(f"\n📊 Total discovered: {len(all_posts)} posts")
        
        # Phase 2: AI Analysis & Summarization
        print("\nPhase 2: AI Analysis & Summarization")
        print("-"*70)
        
        # First filter by relevance
        relevant = self.discovery_engine.filter_by_relevance(all_posts)
        print(f"   📊 {len(relevant)} relevant posts")
        
        # Use AI to analyze and summarize
        try:
            from src.core.discovery.ai_scorer import AIContentScorer
            
            scorer = AIContentScorer()
            print(f"   🤖 AI Analysis (Ollama: {scorer.ollama_available}, Gemini: {scorer.gemini_available})")
            
            # Score and summarize top content
            analyzed = []
            for item in relevant[:30]:  # Analyze top 30
                post = item["post"]
                
                # Get AI score
                score = await scorer.score_content(post.content, item.get("topics", []))
                
                # Generate summary if high quality (use profile threshold)
                threshold = self.profile_manager.get_quality_threshold()
                if score >= threshold:
                    summary = await self._generate_summary(post.content, scorer)
                    
                    analyzed.append({
                        **item,
                        "quality_score": score,
                        "ai_summary": summary
                    })
            
            print(f"   ✅ Analyzed {len(analyzed)} posts with AI")
            discovered = analyzed
            
        except Exception as e:
            print(f"   ⚠️ AI analysis failed: {e}")
            ai_scores = {}
            discovered = self.discovery_engine.filter_by_quality(relevant, ai_scores)
        
        # Phase 3: Research trending topics
        research_insights = await self.research_trending_topics(
            [item["post"] for item in discovered]
        )
        
        # Phase 4: Curate with librarian
        curated = await self.curate_with_librarian(discovered)
        
        # Build comprehensive report
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_discovered": len(all_posts),
            "high_quality": len(discovered),
            "sources": {
                "github": len([p for p in all_posts if p.platform == "github"]),
                "reddit": len([p for p in all_posts if p.platform == "reddit"]),
                "articles": len([p for p in all_posts if p.platform == "article"]),
                "web": len([p for p in all_posts if p.platform == "web"]),
            },
            "discovered_posts": discovered,
            "research": research_insights,
            "curated": curated,
            "stats": self.discovery_engine.get_discovery_stats()
        }
        
        print("\n" + "="*70)
        print("✅ COMPREHENSIVE DISCOVERY COMPLETE")
        print("="*70)
        print(f"📊 Found: {len(all_posts)} total | {len(discovered)} high-quality")
        print(f"🔥 Must-read: {len(curated['must_read'])}")
        print(f"🔬 Research: {len(research_insights.get('deep_research', {}))} topics analyzed")
        print("="*70 + "\n")
        
        return report
