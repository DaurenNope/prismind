#!/usr/bin/env python3
"""
Trend Analyzer - Proactive Content Suggestions
Analyzes collected posts to identify trends and suggests content based on your opinions
"""
import json
from typing import Dict, List, Any
from collections import Counter, defaultdict
from pathlib import Path
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class TrendAnalyzer:
    """
    Analyzes trends in collected posts and suggests content ideas.

    Features:
    - Identifies trending topics across platforms
    - Detects what people are discussing most
    - Matches trends with your opinions from config/opinions.json
    - Generates content suggestions: "People are talking about X, you could say Y"
    - Avoids political and religious topics
    """

    def __init__(self):
        self.opinions_path = Path("config/opinions.json")
        self.opinions = self._load_opinions()

        # Topics to avoid
        self.avoid_topics = {
            'political', 'politics', 'election', 'government', 'democrat',
            'republican', 'liberal', 'conservative', 'religion', 'religious',
            'islam', 'christianity', 'judaism', 'muslim', 'christian', 'jewish',
            'allah', 'god', 'bible', 'quran', 'church', 'mosque', 'temple',
            'prayer', 'worship', 'faith', 'belief', 'holy', 'sacred'
        }

    def _load_opinions(self) -> Dict:
        """Load your opinions from config"""
        if not self.opinions_path.exists():
            return {}

        with open(self.opinions_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('qronoya', {})

    def analyze_trends(
        self,
        posts: List[Dict[str, Any]],
        time_window_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Analyze trends in posts.

        Args:
            posts: List of posts from database
            time_window_hours: Only analyze posts from last N hours

        Returns:
            Trend analysis with suggestions
        """

        logger.info(f"🔍 Analyzing trends from {len(posts)} posts...")

        # Filter by time window
        cutoff_time = datetime.now() - timedelta(hours=time_window_hours)
        recent_posts = []

        for post in posts:
            created_at = post.get('created_at')
            if created_at:
                try:
                    post_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    if post_time >= cutoff_time:
                        recent_posts.append(post)
                except:
                    recent_posts.append(post)  # Include if can't parse time
            else:
                recent_posts.append(post)

        logger.info(f"   Found {len(recent_posts)} recent posts (last {time_window_hours}h)")

        # Extract topics and keywords
        topics = self._extract_topics(recent_posts)

        # Filter out political/religious topics
        safe_topics = self._filter_safe_topics(topics)

        # Find trending topics
        trending = self._identify_trending(safe_topics)

        # Match with your opinions
        suggestions = self._generate_suggestions(trending)

        return {
            'analyzed_at': datetime.now().isoformat(),
            'time_window_hours': time_window_hours,
            'total_posts': len(posts),
            'recent_posts': len(recent_posts),
            'trending_topics': trending[:10],  # Top 10
            'content_suggestions': suggestions[:5],  # Top 5
            'avoided_sensitive_topics': len(topics) - len(safe_topics)
        }

    def _extract_topics(self, posts: List[Dict]) -> List[Dict]:
        """Extract topics and keywords from posts"""

        topics = []

        # Common tech/AI keywords to look for
        tech_keywords = {
            'ai', 'artificial intelligence', 'ml', 'machine learning',
            'gpt', 'llm', 'chatgpt', 'gemini', 'claude', 'openai',
            'cursor', 'windsurf', 'cline', 'copilot', 'coding assistant',
            'python', 'javascript', 'typescript', 'rust', 'go',
            'startup', 'entrepreneurship', 'founder', 'building',
            'automation', 'productivity', 'workflow',
            'deepseek', 'qwen', 'llama', 'mistral', 'anthropic',
            'model', 'training', 'fine-tuning', 'prompt',
            'api', 'sdk', 'framework', 'library',
            'nextjs', 'react', 'vue', 'svelte',
            'saas', 'product', 'launch', 'mvp',
            'remote work', 'freelance', 'career', 'developer',
            'china', 'us', 'silicon valley', 'bay area',
            'threads', 'twitter', 'x', 'social media',
            'crypto', 'blockchain', 'web3', 'defi'
        }

        for post in posts:
            content = (post.get('content') or '') + ' ' + (post.get('title') or '')
            content_lower = content.lower()

            # Find matching keywords
            matched_keywords = []
            for keyword in tech_keywords:
                if keyword in content_lower:
                    matched_keywords.append(keyword)

            if matched_keywords:
                topics.append({
                    'keywords': matched_keywords,
                    'content_snippet': content[:200],
                    'platform': post.get('platform', 'unknown'),
                    'url': post.get('url', ''),
                    'created_at': post.get('created_at', '')
                })

        return topics

    def _filter_safe_topics(self, topics: List[Dict]) -> List[Dict]:
        """Filter out political and religious topics"""

        safe_topics = []

        for topic in topics:
            # Check if any keyword is in avoid list
            has_sensitive = False
            for keyword in topic['keywords']:
                if any(avoid in keyword.lower() for avoid in self.avoid_topics):
                    has_sensitive = True
                    break

            # Check content snippet
            snippet_lower = topic['content_snippet'].lower()
            if any(avoid in snippet_lower for avoid in self.avoid_topics):
                has_sensitive = True

            if not has_sensitive:
                safe_topics.append(topic)

        return safe_topics

    def _identify_trending(self, topics: List[Dict]) -> List[Dict]:
        """Identify trending topics by frequency"""

        # Count keyword frequencies
        keyword_counts = Counter()
        keyword_examples = defaultdict(list)

        for topic in topics:
            for keyword in topic['keywords']:
                keyword_counts[keyword] += 1
                if len(keyword_examples[keyword]) < 3:  # Keep max 3 examples
                    keyword_examples[keyword].append({
                        'snippet': topic['content_snippet'],
                        'platform': topic['platform'],
                        'url': topic['url']
                    })

        # Build trending list
        trending = []
        for keyword, count in keyword_counts.most_common(20):
            if count >= 2:  # At least 2 mentions to be "trending"
                trending.append({
                    'keyword': keyword,
                    'mention_count': count,
                    'examples': keyword_examples[keyword]
                })

        return trending

    def _generate_suggestions(self, trending: List[Dict]) -> List[Dict]:
        """Generate content suggestions based on trends + your opinions"""

        suggestions = []

        for trend in trending:
            keyword = trend['keyword']
            mention_count = trend['mention_count']

            # Match with your opinions
            matched_opinion = self._match_opinion(keyword)

            if matched_opinion:
                suggestion = {
                    'trend': keyword,
                    'mentions': mention_count,
                    'observation': f"People are discussing {keyword} ({mention_count} posts recently)",
                    'your_angle': matched_opinion['angle'],
                    'your_opinion': matched_opinion['opinion'],
                    'suggested_content': self._draft_content(keyword, matched_opinion),
                    'examples': trend['examples'][:2]  # Show 2 examples
                }
                suggestions.append(suggestion)

        return suggestions

    def _match_opinion(self, keyword: str) -> Dict:
        """Match keyword with your opinions"""

        # Map keywords to opinion categories
        opinion_map = {
            # AI Tools
            'cursor': 'tech_and_ai.ai_coding_tools',
            'windsurf': 'tech_and_ai.ai_coding_tools',
            'cline': 'tech_and_ai.ai_coding_tools',
            'copilot': 'tech_and_ai.ai_coding_tools',
            'coding assistant': 'tech_and_ai.ai_coding_tools',

            # AI Development
            'ai': 'tech_and_ai.ai_development_landscape',
            'gpt': 'tech_and_ai.ai_development_landscape',
            'chatgpt': 'tech_and_ai.ai_development_landscape',
            'gemini': 'tech_and_ai.ai_development_landscape',
            'claude': 'tech_and_ai.ai_development_landscape',
            'deepseek': 'tech_and_ai.ai_development_landscape',
            'china': 'tech_and_ai.ai_development_landscape',

            # Automation
            'automation': 'tech_and_ai.automation_philosophy',
            'productivity': 'tech_and_ai.automation_philosophy',
            'workflow': 'tech_and_ai.automation_philosophy',

            # Entrepreneurship
            'startup': 'business_approach.rahmet_labs_positioning',
            'entrepreneurship': 'business_approach.rahmet_labs_positioning',
            'founder': 'business_approach.rahmet_labs_positioning',
            'building': 'business_approach.rahmet_labs_positioning',

            # Career
            'career': 'tech_and_ai.ai_coding_tools',  # Default to coding career
            'developer': 'tech_and_ai.ai_coding_tools',
            'remote work': 'location_and_lifestyle.personal_travel',
            'freelance': 'business_approach.client_interaction_style',
        }

        opinion_path = opinion_map.get(keyword.lower())

        if not opinion_path:
            return None

        # Navigate opinion path
        opinion_parts = opinion_path.split('.')
        current = self.opinions

        for part in opinion_parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None

        if isinstance(current, str):
            return {
                'angle': f"Your perspective on {keyword}",
                'opinion': current
            }

        return None

    def _draft_content(self, keyword: str, matched_opinion: Dict) -> str:
        """Draft suggested content based on trend + opinion"""

        opinion = matched_opinion['opinion']

        # Extract key points from opinion
        # This is a simple draft - user will edit/approve
        draft = f"Вижу все обсуждают {keyword}.\n\n{opinion[:200]}...\n\nЧто думаете?"

        return draft


def demo_trend_analysis():
    """Demo trend analysis"""

    print("\n" + "="*100)
    print("🔍 TREND ANALYZER DEMO")
    print("="*100)

    analyzer = TrendAnalyzer()

    # Load posts from database
    from src.storage.db import StorageFacade

    db = StorageFacade()
    posts = db.get_posts(limit=100)

    # Filter out None
    posts = [p for p in posts if p is not None]

    print(f"\n📊 Analyzing {len(posts)} posts...")

    # Analyze trends
    analysis = analyzer.analyze_trends(posts, time_window_hours=72)  # Last 3 days

    print(f"\n{'='*100}")
    print("📈 TRENDING TOPICS")
    print("="*100)

    for idx, topic in enumerate(analysis['trending_topics'][:10], 1):
        print(f"\n{idx}. {topic['keyword'].upper()} ({topic['mention_count']} mentions)")

    print(f"\n{'='*100}")
    print("💡 CONTENT SUGGESTIONS")
    print("="*100)

    if not analysis['content_suggestions']:
        print("\n⚠️  No suggestions yet. Need more posts with matched opinions.")
        print("   Suggestions appear when trending topics match your opinions in config/opinions.json")
    else:
        for idx, suggestion in enumerate(analysis['content_suggestions'], 1):
            print(f"\n{idx}. TREND: {suggestion['trend'].upper()}")
            print(f"   Observation: {suggestion['observation']}")
            print(f"   Your angle: {suggestion['your_angle']}")
            print(f"\n   Your opinion:")
            print(f"   {suggestion['your_opinion'][:150]}...")
            print(f"\n   Suggested draft:")
            print(f"   {suggestion['suggested_content']}")
            print(f"\n   Examples of what people are saying:")
            for ex in suggestion['examples']:
                print(f"      • [{ex['platform']}] {ex['snippet'][:80]}...")

    print(f"\n{'='*100}")
    print(f"✅ Analysis complete")
    print(f"   Filtered out {analysis['avoided_sensitive_topics']} sensitive topics (political/religious)")
    print("="*100)


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    demo_trend_analysis()
