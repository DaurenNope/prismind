import os
import requests
import time
from loguru import logger
from typing import Dict, Any, List, Optional
import json


class DeepResearchAnalyzer:
    """Enhanced analyzer that performs deep research on high-value content"""
    
    def __init__(self):
        self.perplexity_api_key = os.getenv('PERPLEXITY_API_KEY')
        self.mistral_api_key = os.getenv('MISTRAL_API_KEY')
        
        # Research thresholds
        self.auto_research_threshold = 7  # Automatically research 7+ scored content
        self.optional_research_threshold = 5  # Optional research for 5-6 scored content
        
    def should_research(self, value_score: int, force_research: bool = False) -> str:
        """Determine if content should be researched"""
        if force_research or value_score >= self.auto_research_threshold:
            return "auto"
        elif value_score >= self.optional_research_threshold:
            return "optional"
        else:
            return "skip"
    
    def enhance_analysis_with_research(self, analyzed_posts: List[Dict]) -> List[Dict]:
        """Enhance analyzed posts with deep research for high-value content"""
        enhanced_posts = []
        
        for item in analyzed_posts:
            post = item['post']
            analysis = item['analysis']
            value_score = analysis.get('value_score', 5)
            
            research_decision = self.should_research(value_score)
            
            if research_decision == "auto":
                logger.info(f"🔍 Auto-researching high-value post (score: {value_score}/10)")
                research_data = self.deep_research_content(post, analysis)
                analysis['deep_research'] = research_data
                analysis['research_status'] = 'completed'
            elif research_decision == "optional":
                logger.info(f"💡 Marking for optional research (score: {value_score}/10)")
                analysis['research_status'] = 'recommended'
                analysis['deep_research'] = None
            else:
                analysis['research_status'] = 'skipped'
                analysis['deep_research'] = None
            
            enhanced_posts.append({
                'post': post,
                'analysis': analysis
            })
            
            # Rate limiting
            if research_decision == "auto":
                time.sleep(2)  # Respect API limits
        
        return enhanced_posts
    
    def deep_research_content(self, post, analysis: Dict) -> Optional[Dict]:
        """Perform deep research on a piece of content"""
        try:
            # Extract key topics for research
            topics = analysis.get('tags', [])
            category = analysis.get('category', '')
            summary = analysis.get('summary', '')
            
            # Create research queries
            research_queries = self._generate_research_queries(topics, category, summary, post)
            
            research_results = {}
            
            # Try Perplexity first (best for research)
            if self.perplexity_api_key:
                logger.info("🔍 Using Perplexity for deep research...")
                for i, query in enumerate(research_queries[:2]):  # Limit to 2 queries
                    result = self._research_with_perplexity(query)
                    if result:
                        research_results[f'research_{i+1}'] = {
                            'query': query,
                            'source': 'perplexity',
                            'findings': result
                        }
            
            # Fallback to Mistral for analysis enhancement
            elif self.mistral_api_key:
                logger.info("🧠 Using Mistral for content enhancement...")
                enhanced_analysis = self._enhance_with_mistral(post, analysis)
                research_results['enhanced_analysis'] = {
                    'source': 'mistral',
                    'findings': enhanced_analysis
                }
            
            return {
                'researched_at': time.time(),
                'research_queries': research_queries,
                'results': research_results,
                'research_summary': self._summarize_research(research_results)
            }
            
        except Exception as e:
            logger.error(f"Research failed: {e}")
            return None
    
    def _generate_research_queries(self, topics: List[str], category: str, summary: str, post) -> List[str]:
        """Generate intelligent research queries based on content"""
        queries = []
        
        # Query 1: Deep dive into main tools/concepts
        main_concepts = topics[:3]  # Top 3 concepts
        if main_concepts:
            queries.append(f"Latest developments and best practices for {', '.join(main_concepts)} in {category}")
        
        # Query 2: Alternative tools/approaches
        if topics:
            queries.append(f"Alternative tools and approaches to {topics[0]} - comprehensive comparison 2024")
        
        # Query 3: Implementation guides
        if 'AI' in category or 'Technology' in category:
            queries.append(f"Step-by-step implementation guide for {topics[0] if topics else category}")
        
        # Query 4: Market analysis and trends
        queries.append(f"Market trends and future outlook for {category} - {topics[0] if topics else 'industry analysis'}")
        
        return queries[:3]  # Limit to 3 queries to manage costs
    
    def _research_with_perplexity(self, query: str) -> Optional[str]:
        """Research using Perplexity API"""
        try:
            response = requests.post(
                "https://api.perplexity.ai/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.perplexity_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "llama-3.1-sonar-small-128k-online",  # Good for research
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a research assistant. Provide comprehensive, factual information with specific examples and current data."
                        },
                        {
                            "role": "user", 
                            "content": f"Research: {query}. Provide detailed findings with specific tools, techniques, and recent developments."
                        }
                    ],
                    "max_tokens": 1000,
                    "temperature": 0.1
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content']
            else:
                logger.error(f"Perplexity API error: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Perplexity research failed: {e}")
            return None
    
    def _enhance_with_mistral(self, post, analysis: Dict) -> Optional[str]:
        """Use Mistral to enhance analysis when Perplexity is unavailable"""
        try:
            prompt = f"""
            Enhance this analysis with deeper insights:
            
            Original Post: {post.content[:500]}
            Current Analysis: {analysis.get('summary', '')}
            Topics: {', '.join(analysis.get('tags', []))}
            
            Provide:
            1. Deeper technical insights
            2. Related tools and alternatives
            3. Implementation considerations
            4. Potential challenges and solutions
            5. Next steps for learning/implementation
            """
            
            response = requests.post(
                "https://api.mistral.ai/v1/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.mistral_api_key}"
                },
                json={
                    "model": "mistral-small-latest",
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 800,
                    "temperature": 0.2
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content']
            else:
                return None
                
        except Exception as e:
            logger.error(f"Mistral enhancement failed: {e}")
            return None
    
    def _summarize_research(self, research_results: Dict) -> str:
        """Create a summary of research findings"""
        if not research_results:
            return "No research data available"
        
        summaries = []
        for key, result in research_results.items():
            if isinstance(result, dict) and 'findings' in result:
                # Don't truncate - show full research findings
                summaries.append(f"• **{result.get('source', 'Research').title()}:** {result['findings']}")
        
        return "\n\n".join(summaries)  # Full summaries with better formatting
    
    def generate_research_report(self, enhanced_posts: List[Dict]) -> str:
        """Generate a comprehensive research report"""
        high_value_posts = [
            item for item in enhanced_posts 
            if item['analysis'].get('value_score', 0) >= self.auto_research_threshold
        ]
        
        report = f"""# 🔍 Deep Research Report
        
Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}
High-Value Content Analyzed: {len(high_value_posts)} posts

## 📊 Research Summary

"""
        
        for i, item in enumerate(high_value_posts[:5], 1):  # Top 5
            analysis = item['analysis']
            research = analysis.get('deep_research', {})
            
            report += f"""### {i}. {item['post'].author} - {analysis.get('category', 'Unknown')}
**Score:** {analysis.get('value_score', 0)}/10
**Platform:** {item['post'].platform}
**Summary:** {analysis.get('summary', 'No summary')}

"""
            if research and research.get('research_summary'):
                report += f"**🔍 Deep Research Findings:**\n{research['research_summary']}\n\n"
                
                # Also include the research queries that were used
                if research.get('research_queries'):
                    report += f"**📋 Research Queries:**\n"
                    for j, query in enumerate(research['research_queries'], 1):
                        report += f"{j}. {query}\n"
                    report += "\n"
                    
            report += "---\n\n"
        
        return report 