"""
Rewrite Angle Suggester

Analyzes collected posts and suggests optimal rewrite angles for a profile.
This helps users understand what content works best for their voice/audience.
"""

import os
from typing import List, Dict, Any, Optional
import google.generativeai as genai
from dotenv import load_dotenv
from src.services.new_database_manager import get_database_manager

load_dotenv()

# Configure Gemini
gemini_key = os.getenv('GEMINI_API_KEY')
if gemini_key:
    genai.configure(api_key=gemini_key)


class RewriteAngleSuggester:
    """Analyzes posts and suggests rewrite angles for profiles"""

    def __init__(self):
        model_name = os.getenv('ANALYZER_GEMINI_MODEL', 'gemini-2.0-flash-exp')
        self.model = genai.GenerativeModel(model_name)
        self.db = get_database_manager()

    async def suggest_angles_for_profile(
        self,
        profile_description: str,
        target_audience: str,
        tone_tags: List[str],
        sample_size: int = 20
    ) -> Dict[str, Any]:
        """
        Analyze recent posts and suggest rewrite angles for a profile.

        Returns:
        {
            'recommended_angles': [
                {
                    'angle': 'Technical Deep Dive',
                    'description': 'Break down complex topics with data and code',
                    'example_posts': [ids],
                    'score': 0.9
                }
            ],
            'content_gaps': ['Missing X', 'Could add Y'],
            'voice_suggestions': ['More casual', 'Add data points']
        }
        """

        # Get recent high-quality posts
        posts = await self._get_sample_posts(sample_size)

        if not posts:
            # No posts yet - generate generic best practice angles
            return await self._generate_generic_angles(
                profile_description,
                target_audience,
                tone_tags
            )

        # Analyze posts and suggest angles
        analysis = await self._analyze_posts_for_angles(
            posts,
            profile_description,
            target_audience,
            tone_tags
        )

        return analysis

    async def _get_sample_posts(self, limit: int) -> List[Dict]:
        """Get high-quality posts for analysis"""

        # Get usable posts (high quality, diverse sources)
        posts = self.db.get_posts(limit=limit * 3)  # Get extra to filter

        if not posts:
            return []

        # Filter for quality
        quality_posts = []
        for post in posts:
            # Skip low quality
            if not post.get('content'):
                continue

            # Prefer posts with engagement
            engagement = post.get('engagement_score', 0)

            # Prefer analyzed posts
            has_analysis = bool(post.get('ai_summary') or post.get('analysis_summary'))

            quality_posts.append({
                'id': post.get('id'),
                'content': post.get('content', '')[:500],  # Truncate long posts
                'platform': post.get('platform'),
                'author': post.get('author'),
                'ai_summary': post.get('ai_summary', ''),
                'category': post.get('category', ''),
                'topics': post.get('topics', []),
                'engagement': engagement,
                'has_analysis': has_analysis,
                'url': post.get('url', '')
            })

        # Sort by quality indicators
        quality_posts.sort(
            key=lambda p: (p['has_analysis'], p['engagement']),
            reverse=True
        )

        return quality_posts[:limit]

    def _analyze_post_statistics(self, posts: List[Dict]) -> Dict[str, Any]:
        """
        Analyze posts statistically to find real patterns.
        This provides concrete data for smarter suggestions.
        """
        from collections import Counter

        # Analyze categories
        categories = [p.get('category', 'uncategorized') for p in posts if p.get('category')]
        category_counts = Counter(categories)

        # Analyze topics
        all_topics = []
        for p in posts:
            topics = p.get('topics', [])
            if isinstance(topics, list):
                all_topics.extend(topics)
        topic_counts = Counter(all_topics)

        # Analyze platforms
        platforms = [p.get('platform', 'unknown') for p in posts]
        platform_counts = Counter(platforms)

        # Analyze engagement patterns
        posts_with_engagement = [p for p in posts if p.get('engagement', 0) > 0]
        avg_engagement = sum(p.get('engagement', 0) for p in posts_with_engagement) / max(len(posts_with_engagement), 1)

        # Find high performers
        high_performers = sorted(
            [p for p in posts if p.get('engagement', 0) > avg_engagement],
            key=lambda x: x.get('engagement', 0),
            reverse=True
        )[:5]

        high_performer_categories = [p.get('category', '') for p in high_performers]
        high_performer_topics = []
        for p in high_performers:
            topics = p.get('topics', [])
            if isinstance(topics, list):
                high_performer_topics.extend(topics)

        # Analyze content characteristics
        avg_length = sum(len(p.get('content', '')) for p in posts) / max(len(posts), 1)
        has_questions = sum(1 for p in posts if '?' in p.get('content', ''))
        has_data = sum(1 for p in posts if any(char.isdigit() for char in p.get('content', '')))
        has_links = sum(1 for p in posts if 'http' in p.get('content', ''))

        # Build summary
        summary = f"""Analyzed {len(posts)} posts:
- Average engagement: {avg_engagement:.1f}
- Average length: {int(avg_length)} characters
- Posts with questions: {has_questions} ({has_questions/max(len(posts),1)*100:.0f}%)
- Posts with data/numbers: {has_data} ({has_data/max(len(posts),1)*100:.0f}%)
- Posts with links: {has_links} ({has_links/max(len(posts),1)*100:.0f}%)
- High performers are about: {', '.join(set(high_performer_categories)) or 'various topics'}"""

        engagement_insight = "No clear pattern"
        if high_performer_topics:
            top_performing_topics = Counter(high_performer_topics).most_common(3)
            engagement_insight = f"High engagement on: {', '.join([t[0] for t in top_performing_topics])}"

        return {
            'summary': summary,
            'top_categories': [cat for cat, _ in category_counts.most_common(5)],
            'top_topics': [topic for topic, _ in topic_counts.most_common(10)],
            'platform_breakdown': ', '.join([f"{plat}: {count}" for plat, count in platform_counts.most_common()]),
            'engagement_insight': engagement_insight,
            'avg_engagement': avg_engagement,
            'high_performers': high_performers,
            'content_characteristics': {
                'avg_length': avg_length,
                'question_rate': has_questions/max(len(posts),1),
                'data_rate': has_data/max(len(posts),1),
                'link_rate': has_links/max(len(posts),1)
            }
        }

    async def _analyze_posts_for_angles(
        self,
        posts: List[Dict],
        profile_description: str,
        target_audience: str,
        tone_tags: List[str]
    ) -> Dict[str, Any]:
        """Use AI to analyze posts and suggest rewrite angles"""

        # First, do statistical analysis of the posts
        stats = self._analyze_post_statistics(posts)

        # Build detailed analysis prompt with real data patterns
        posts_summary = "\n\n".join([
            f"Post {i+1} ({p['platform']}):\n{p['content'][:300]}\nEngagement: {p.get('engagement', 'N/A')}\nCategory: {p.get('category', 'N/A')}\nTopics: {', '.join(p.get('topics', [])[:5])}"
            for i, p in enumerate(posts[:15])  # Limit to avoid token overflow
        ])

        prompt = f"""Analyze these REAL social media posts and suggest SPECIFIC rewrite angles based on actual patterns.

DATA INSIGHTS:
{stats['summary']}

Top Performing Content Types: {', '.join(stats['top_categories'][:3])}
Most Common Topics: {', '.join(stats['top_topics'][:5])}
Platform Distribution: {stats['platform_breakdown']}
Engagement Patterns: {stats['engagement_insight']}

Now analyze the posts and suggest angles based on WHAT'S ACTUALLY WORKING in this data.

PROFILE INFO:
- Description: {profile_description}
- Target Audience: {target_audience}
- Desired Tone: {', '.join(tone_tags)}

COLLECTED POSTS:
{posts_summary}

YOUR TASK: Suggest SPECIFIC, DATA-DRIVEN rewrite angles. DO NOT give generic AI advice.

REQUIREMENTS:
1. **Recommended Angles** - Base these on ACTUAL patterns in the data above
   - Reference specific content types that performed well
   - Cite actual topics from the top_topics list
   - Explain WHY based on engagement data
   - Score based on how well it matches the profile AND the data patterns

2. **Content Gaps** - Identify SPECIFIC missing opportunities
   - What topics are your audience asking about but not covered?
   - What formats work well but aren't being used?
   - What angles would differentiate from existing content?
   - Be concrete, not vague

3. **Voice Tactics** - Give ACTIONABLE recommendations
   - Reference the content characteristics data (questions, data, links)
   - Suggest specific changes based on what's working
   - Don't say "be more engaging" - say exactly HOW based on data

Return ONLY a JSON object:
{{
  "recommended_angles": [
    {{
      "angle": "angle name",
      "description": "what this angle is",
      "when_to_use": "which posts work with this",
      "example_approach": "how to rewrite",
      "score": 0.9
    }}
  ],
  "content_gaps": [
    "gap 1 description",
    "gap 2 description"
  ],
  "voice_suggestions": [
    "suggestion 1",
    "suggestion 2"
  ]
}}"""

        try:
            response = self.model.generate_content(prompt)
            response_text = response.text

            # Extract JSON
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                json_str = response_text[json_start:json_end].strip()
            else:
                json_str = response_text

            import json
            result = json.loads(json_str)

            # Add post references
            result['analyzed_posts_count'] = len(posts)
            result['sample_posts'] = [
                {
                    'platform': p['platform'],
                    'content_preview': p['content'][:100],
                    'url': p.get('url', '')
                }
                for p in posts[:5]
            ]

            return result

        except Exception as e:
            return {
                'error': f'Analysis failed: {str(e)}',
                'recommended_angles': [],
                'content_gaps': [],
                'voice_suggestions': []
            }

    async def suggest_angle_for_post(
        self,
        post: Dict,
        profile_voice: str,
        profile_topics: List[str]
    ) -> Dict[str, Any]:
        """
        Suggest the best rewrite angle for a specific post.

        Returns:
        {
            'suggested_angle': 'Technical Deep Dive',
            'reasoning': 'Post contains data that fits your analytical style',
            'approach': 'Extract the key metrics and explain implications',
            'confidence': 0.85
        }
        """

        prompt = f"""Suggest the best rewrite angle for this post.

POST:
Platform: {post.get('platform')}
Content: {post.get('content', '')[:500]}
Category: {post.get('category', 'N/A')}
Topics: {', '.join(post.get('topics', [])[:5])}

PROFILE:
Voice: {profile_voice}
Topics: {', '.join(profile_topics[:20])}

Based on this post and profile, suggest:
1. The best angle/approach to rewrite this
2. Why this angle works
3. How to execute it
4. Confidence score (0-1)

Return ONLY a JSON object:
{{
  "suggested_angle": "angle name",
  "reasoning": "why this works",
  "approach": "how to execute",
  "key_points": ["point 1", "point 2"],
  "confidence": 0.85
}}"""

        try:
            response = self.model.generate_content(prompt)
            response_text = response.text

            # Extract JSON
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                json_str = response_text[json_start:json_end].strip()
            else:
                json_str = response_text

            import json
            return json.loads(json_str)

        except Exception as e:
            return {
                'suggested_angle': 'General Commentary',
                'reasoning': f'Analysis failed: {str(e)}',
                'approach': 'Provide your perspective on this topic',
                'confidence': 0.5
            }

    async def compare_rewrite_angles(
        self,
        post: Dict,
        angles: List[str],
        profile_voice: str
    ) -> Dict[str, float]:
        """
        Compare multiple rewrite angles for a post and score them.

        Returns: {'angle1': 0.9, 'angle2': 0.7, ...}
        """

        prompt = f"""Score these rewrite angles for this post (0-1 scale).

POST:
{post.get('content', '')[:500]}

PROFILE VOICE:
{profile_voice}

ANGLES TO COMPARE:
{chr(10).join([f'- {angle}' for angle in angles])}

Score each angle based on:
- Fit with profile voice
- Audience interest
- Content potential
- Engagement likelihood

Return ONLY a JSON object:
{{
  "angle_name_1": 0.9,
  "angle_name_2": 0.7
}}"""

        try:
            response = self.model.generate_content(prompt)
            response_text = response.text

            # Extract JSON
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                json_str = response_text[json_start:json_end].strip()
            else:
                json_str = response_text

            import json
            return json.loads(json_str)

        except Exception as e:
            # Return equal scores if analysis fails
            return {angle: 0.5 for angle in angles}

    async def _generate_generic_angles(
        self,
        profile_description: str,
        target_audience: str,
        tone_tags: List[str]
    ) -> Dict[str, Any]:
        """
        Generate generic best practice angles when no posts are available.
        Based purely on profile description and target audience.
        """

        prompt = f"""You're helping someone create a social media profile. They don't have any posts collected yet.

Based on their profile info, suggest the best rewrite angles they should use when they start collecting content.

PROFILE INFO:
- Description: {profile_description}
- Target Audience: {target_audience}
- Desired Tone: {', '.join(tone_tags)}

Suggest:
1. **Recommended Rewrite Angles** (5-7 angles that would work well)
   - What angle/approach to take
   - Why it fits this profile
   - When to use it
   - Success score (0-1 based on how well it fits)

2. **Content Strategy** (what types of content to collect/create)
   - Topics to focus on
   - Content formats that work
   - Platforms to prioritize

3. **Voice Recommendations** (how to execute the desired tone)
   - Specific voice tactics
   - Examples of what to do/avoid
   - Engagement strategies

Return ONLY a JSON object:
{{
  "recommended_angles": [
    {{
      "angle": "angle name",
      "description": "what this angle is",
      "when_to_use": "which content works with this",
      "example_approach": "how to execute",
      "score": 0.9
    }}
  ],
  "content_strategy": [
    "strategy 1",
    "strategy 2"
  ],
  "voice_suggestions": [
    "suggestion 1",
    "suggestion 2"
  ],
  "no_posts_available": true
}}"""

        try:
            response = self.model.generate_content(prompt)
            response_text = response.text

            # Extract JSON
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                json_str = response_text[json_start:json_end].strip()
            else:
                json_str = response_text

            import json
            result = json.loads(json_str)

            # Mark as generic
            result['no_posts_available'] = True
            result['content_gaps'] = result.get('content_strategy', [])

            return result

        except Exception as e:
            return {
                'error': f'Could not generate angles: {str(e)}',
                'recommended_angles': [],
                'content_gaps': [],
                'voice_suggestions': [],
                'no_posts_available': True
            }
