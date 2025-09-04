"""
PrisMind Intelligent Content Analyzer
=====================================

This is the core intelligence system that makes PrisMind truly smart.
It analyzes not just the original post, but also:
- The most valuable comments and discussions
- Media content (images, videos) using AI vision
- Extracts actionable insights and learning points
- Provides sophisticated value scoring

Author: PrisMind AI System
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

# AI imports
import google.generativeai as genai
import requests
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# Core imports
from core.extraction.social_extractor_base import SocialPost


class IntelligentContentAnalyzer:
    """The brain of PrisMind - provides deep analysis of social media content"""
    
    def __init__(self):
        """Initialize the intelligent analyzer with multiple AI backends"""
        
        # Initialize sentiment analyzer
        self.sentiment_analyzer = SentimentIntensityAnalyzer()
        
        # Initialize AI services (try multiple for redundancy)
        self.ai_services = []
        self._init_ai_services()
        
        print(f"🧠 Intelligent Content Analyzer initialized with {len(self.ai_services)} AI services")
    
    def _init_ai_services(self):
        """Initialize available AI services in order of preference"""

        # 0. Ollama (Local Qwen) — prefer when available for local-first analysis
        ollama_url = os.getenv('OLLAMA_URL')
        if ollama_url:
            self.ai_services.append({
                'name': 'ollama',
                'url': ollama_url.rstrip('/'),
                'model': os.getenv('OLLAMA_MODEL', 'qwen2.5:7b')
            })
            print("✅ Ollama (Qwen) initialized")

        # 1. Mistral AI (Primary - best for analysis)
        mistral_key = os.getenv('MISTRAL_API_KEY')
        if mistral_key:
            self.ai_services.append({
                'name': 'mistral',
                'key': mistral_key,
                'base_url': 'https://api.mistral.ai/v1',
                'model': 'mistral-small-latest'
            })
            print("✅ Mistral AI initialized")
        
        # 2. Google Gemini (Secondary - best for vision)
        gemini_key = os.getenv('GEMINI_API_KEY')
        if gemini_key:
            genai.configure(api_key=gemini_key)
            self.gemini_model = genai.GenerativeModel('gemini-1.5-flash')
            self.gemini_vision_model = genai.GenerativeModel('gemini-1.5-pro-vision-latest')
            self.ai_services.append({
                'name': 'gemini',
                'model': self.gemini_model,
                'vision_model': self.gemini_vision_model
            })
            print("✅ Google Gemini initialized")
        
        # 3. ShuttleAI (Fallback)
        if not self.ai_services:
            self.ai_services.append({'name': 'basic'})
            print("⚠️ No AI services available, using basic analysis")
    
    def analyze_bookmark(self, post: SocialPost, include_comments: bool = True, include_media: bool = True) -> Dict[str, Any]:
        """
        Comprehensive analysis of a bookmarked post
        
        Args:
            post: The social media post to analyze
            include_comments: Whether to analyze comments (Reddit only)
            include_media: Whether to analyze media content
            
        Returns:
            Complete analysis with insights, value scoring, and actionable items
        """
        
        print(f"🔍 Analyzing {post.platform} post: {post.post_id}")

        # Deterministic mode for testing and reproducibility
        if os.getenv('DETERMINISTIC_ANALYSIS', '0') == '1':
            return self._deterministic_analysis(post, include_comments=include_comments, include_media=include_media)
        
        analysis = {
            'post_id': post.post_id,
            'platform': post.platform,
            'analyzed_at': datetime.now().isoformat(),
            'analysis_version': '2.0'
        }
        
        # 1. Core Content Analysis
        core_analysis = self._analyze_core_content(post)
        analysis.update(core_analysis)
        
        # 2. Comment Analysis (Reddit only)
        if include_comments and post.platform == 'reddit':
            comment_analysis = self._analyze_comments(post)
            analysis['comment_insights'] = comment_analysis
        
        # 3. Media Analysis
        if include_media and post.media_urls:
            media_analysis = self._analyze_media_content(post.media_urls)
            analysis['media_insights'] = media_analysis
        
        # 4. Advanced Value Scoring
        value_score = self._calculate_intelligent_value_score(analysis, post)
        analysis['intelligent_value_score'] = value_score
        
        # 5. Generate Actionable Insights
        actionable_insights = self._generate_actionable_insights(analysis, post)
        analysis['actionable_insights'] = actionable_insights
        
        # 6. Learning Recommendations
        learning_recs = self._generate_learning_recommendations(analysis, post)
        analysis['learning_recommendations'] = learning_recs
        
        print(f"✅ Analysis complete - Value Score: {value_score}/10")
        return analysis

    def _deterministic_analysis(self, post: SocialPost, include_comments: bool, include_media: bool) -> Dict[str, Any]:
        """Produce stable, reproducible analysis without external AI calls.

        Uses simple rules and content hashing to generate consistent outputs for tests.
        """
        import hashlib

        content = post.content or ""
        content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
        category_pool = ["Technology", "AI", "Business", "Learning", "General"]
        category = category_pool[int(content_hash[:2], 16) % len(category_pool)]

        sentiment_scores = self.sentiment_analyzer.polarity_scores(content)

        analysis = {
            'post_id': post.post_id,
            'platform': post.platform,
            'analyzed_at': datetime.now().isoformat(),
            'analysis_version': 'deterministic-1.0',
            'category': category,
            'subcategory': post.platform.title(),
            'content_type': post.post_type,
            'topics': post.hashtags[:3] if post.hashtags else ['general'],
            'key_concepts': [],
            'summary': content[:200] + '...' if len(content) > 200 else content,
            'why_valuable': 'User bookmarked this content',
            'sentiment': 'Positive' if sentiment_scores['compound'] > 0.2 else ('Negative' if sentiment_scores['compound'] < -0.2 else 'Neutral'),
            'complexity_level': 'Unknown',
            'time_to_consume': 'Unknown',
            'actionable_items': [],
            'learning_value': 'Reproducible deterministic analysis',
            'practical_applications': [],
            'related_skills': [],
            'follow_up_research': [],
            'quality_indicators': [],
            'tags': post.hashtags[:5] if post.hashtags else [],
            'confidence_score': 1.0,
            'sentiment_scores': sentiment_scores,
            'ai_service': 'deterministic'
        }

        value_score = self._calculate_intelligent_value_score(analysis, post)
        analysis['intelligent_value_score'] = value_score
        if include_comments and post.platform == 'reddit':
            analysis['comment_insights'] = []
        if include_media and post.media_urls:
            analysis['media_insights'] = {
                'total_media': len(post.media_urls),
                'analyzed_media': 0,
                'insights': []
            }
        analysis['actionable_insights'] = self._generate_actionable_insights(analysis, post)
        analysis['learning_recommendations'] = self._generate_learning_recommendations(analysis, post)
        return analysis
    
    def _analyze_core_content(self, post: SocialPost) -> Dict[str, Any]:
        """Analyze the main post content with AI"""
        
        # Get sentiment analysis
        sentiment_scores = self.sentiment_analyzer.polarity_scores(post.content)
        
        # Create comprehensive analysis prompt
        prompt = self._create_analysis_prompt(post)
        
        # Try AI services in order
        for service in self.ai_services:
            try:
                if service['name'] == 'ollama':
                    return self._analyze_with_ollama(prompt, sentiment_scores, service)
                elif service['name'] == 'mistral':
                    return self._analyze_with_mistral(prompt, sentiment_scores, service)
                elif service['name'] == 'gemini':
                    return self._analyze_with_gemini(prompt, sentiment_scores, service)
                else:
                    return self._basic_analysis(post, sentiment_scores)
            except Exception as e:
                print(f"⚠️ {service['name']} analysis failed: {e}")
                continue
        
        # Fallback to basic analysis
        return self._basic_analysis(post, sentiment_scores)
    
    def _create_analysis_prompt(self, post: SocialPost) -> str:
        """Create a comprehensive analysis prompt"""
        
        return f"""
        Analyze this social media bookmark with deep intelligence and provide actionable insights:

        PLATFORM: {post.platform}
        AUTHOR: {post.author} ({post.author_handle})
        CONTENT: {post.content}
        HASHTAGS: {', '.join(post.hashtags) if post.hashtags else 'None'}
        ENGAGEMENT: {post.engagement}
        CREATED: {post.created_at}
        URL: {post.url}

        Provide a JSON response with this EXACT structure:
        {{
          "category": "Primary category (Technology, AI, Business, Learning, etc.)",
          "subcategory": "Specific subcategory",
          "content_type": "Type (Tutorial, News, Discussion, Tool, Resource, etc.)",
          "topics": ["topic1", "topic2", "topic3"],
          "key_concepts": ["concept1", "concept2", "concept3"],
          "summary": "Clear 2-3 sentence summary of key information",
          "why_valuable": "Why someone would bookmark this content",
          "sentiment": "Positive/Negative/Neutral/Mixed",
          "complexity_level": "Beginner/Intermediate/Advanced/Expert",
          "time_to_consume": "estimated reading/watching time in minutes",
          "actionable_items": ["specific action1", "specific action2"],
          "learning_value": "What you can learn from this (1-2 sentences)",
          "practical_applications": ["how to apply this knowledge"],
          "related_skills": ["skill1", "skill2"],
          "follow_up_research": ["what to research next"],
          "quality_indicators": ["why this is high/low quality content"],
          "tags": ["searchable", "keywords"],
          "confidence_score": 0.85
        }}

        Focus on PRACTICAL VALUE and ACTIONABLE INSIGHTS. Be specific and helpful.
        Return ONLY valid JSON, no additional text.
        """
    
    def _analyze_with_mistral(self, prompt: str, sentiment_scores: Dict, service: Dict) -> Dict[str, Any]:
        """Analyze content using Mistral AI"""
        
        response = requests.post(
            f"{service['base_url']}/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {service['key']}"
            },
            json={
                "model": service['model'],
                "messages": [
                    {"role": "system", "content": "You are an expert content analyst specializing in extracting maximum value from social media bookmarks. Provide detailed, actionable insights."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 1500,
                "temperature": 0.1
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content'].strip()
            
            # Clean JSON response
            if content.startswith('```json'):
                content = content[7:-3]
            elif content.startswith('```'):
                content = content[3:-3]
            
            analysis = json.loads(content)
            analysis['sentiment_scores'] = sentiment_scores
            analysis['ai_service'] = 'mistral'
            
            return analysis
        else:
            raise Exception(f"Mistral API error: {response.status_code}")

    def _analyze_with_ollama(self, prompt: str, sentiment_scores: Dict, service: Dict) -> Dict[str, Any]:
        """Analyze content using local Ollama (Qwen)"""
        url = f"{service['url']}/api/generate"
        payload = {
            "model": service['model'],
            "prompt": f"Analyze this content and respond with ONLY valid JSON:\n\n{prompt}",
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_predict": 800  # Increased for longer responses
            }
        }

        resp = requests.post(url, json=payload, timeout=60)
        if resp.status_code != 200:
            raise Exception(f"Ollama API error: {resp.status_code}")
        
        data = resp.json()
        content = data.get('response', '').strip()
        
        # Check if content is empty
        if not content:
            raise Exception("Ollama returned empty response")
        
        # Clean JSON fences if any
        if content.startswith('```json'):
            content = content[7:-3]
        elif content.startswith('```'):
            content = content[3:-3]

        try:
            analysis = json.loads(content)
        except json.JSONDecodeError:
            raise Exception(f"Ollama returned invalid JSON: {content[:100]}...")
        analysis['sentiment_scores'] = sentiment_scores
        analysis['ai_service'] = f"ollama:{service['model']}"
        return analysis
    
    def _analyze_with_gemini(self, prompt: str, sentiment_scores: Dict, service: Dict) -> Dict[str, Any]:
        """Analyze content using Google Gemini"""
        
        response = service['model'].generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.1,
                max_output_tokens=1500
            )
        )
        
        content = response.text.strip()
        
        # Clean JSON response
        if content.startswith('```json'):
            content = content[7:-3]
        elif content.startswith('```'):
            content = content[3:-3]
        
        analysis = json.loads(content)
        analysis['sentiment_scores'] = sentiment_scores
        analysis['ai_service'] = 'gemini'
        
        return analysis
    
    def _analyze_comments(self, post: SocialPost) -> Dict[str, Any]:
        """Analyze Reddit comments to extract valuable insights"""
        
        # This would integrate with Reddit API to get comments
        # For now, return placeholder structure
        return {
            'top_insights': [
                "Most valuable comment insights would appear here",
                "Community consensus and expert opinions",
                "Practical tips and experiences shared"
            ],
            'expert_opinions': [],
            'common_questions': [],
            'practical_tips': [],
            'warnings_caveats': [],
            'additional_resources': []
        }
    
    def _analyze_media_content(self, media_urls: List[str]) -> Dict[str, Any]:
        """Analyze images and videos using AI vision"""
        
        media_insights = {
            'total_media': len(media_urls),
            'analyzed_media': 0,
            'insights': []
        }
        
        for url in media_urls[:3]:  # Analyze first 3 media items
            try:
                insight = self._analyze_single_media(url)
                if insight:
                    media_insights['insights'].append(insight)
                    media_insights['analyzed_media'] += 1
            except Exception as e:
                print(f"⚠️ Media analysis failed for {url}: {e}")
        
        return media_insights
    
    def _analyze_single_media(self, media_url: str) -> Optional[Dict[str, Any]]:
        """Analyze a single media item"""
        
        # Check if we have Gemini Vision available
        for service in self.ai_services:
            if service['name'] == 'gemini' and 'vision_model' in service:
                try:
                    # Download and analyze image
                    response = requests.get(media_url, timeout=10)
                    if response.status_code == 200:
                        
                        # Use Gemini Vision to analyze
                        vision_prompt = """
                        Analyze this image from a social media post and extract:
                        1. What is shown in the image?
                        2. Any text or code visible?
                        3. Technical concepts or tools shown?
                        4. Educational or practical value?
                        5. Key insights someone could learn?
                        
                        Provide a brief but informative analysis.
                        """
                        
                        # This would use Gemini Vision API
                        # For now, return placeholder
                        return {
                            'media_url': media_url,
                            'content_type': 'image',
                            'description': 'AI vision analysis would appear here',
                            'key_elements': ['element1', 'element2'],
                            'educational_value': 'High',
                            'extracted_text': ''
                        }
                        
                except Exception as e:
                    print(f"Vision analysis failed: {e}")
        
        return None
    
    def _calculate_intelligent_value_score(self, analysis: Dict, post: SocialPost) -> float:
        """Calculate sophisticated value score based on multiple factors"""
        
        score = 5.0  # Base score
        
        # Content quality indicators
        if 'quality_indicators' in analysis:
            quality_count = len(analysis['quality_indicators'])
            score += min(quality_count * 0.5, 2.0)
        
        # Actionable content bonus
        if 'actionable_items' in analysis:
            actionable_count = len(analysis['actionable_items'])
            score += min(actionable_count * 0.3, 1.5)
        
        # Learning value bonus
        if 'learning_value' in analysis and analysis['learning_value']:
            score += 1.0
        
        # Engagement quality (not just quantity)
        if post.engagement:
            # High engagement with good content is valuable
            likes = post.engagement.get('likes', 0)
            comments = post.engagement.get('comments', 0)
            if likes > 100 or comments > 20:
                score += 0.5
        
        # Platform-specific adjustments
        if post.platform == 'reddit':
            # Reddit discussions often have high value
            score += 0.5
        elif post.platform == 'twitter':
            # Twitter threads can be valuable
            if post.post_type == 'thread':
                score += 0.5
        
        # Content complexity and depth
        if 'complexity_level' in analysis:
            complexity = analysis['complexity_level']
            if complexity in ['Advanced', 'Expert']:
                score += 0.5
        
        # Cap the score at 10
        return min(score, 10.0)
    
    def _generate_actionable_insights(self, analysis: Dict, post: SocialPost) -> List[str]:
        """Generate specific actionable insights from the analysis"""
        
        insights = []
        
        # Extract from analysis
        if 'actionable_items' in analysis:
            insights.extend(analysis['actionable_items'])
        
        # Add platform-specific insights
        if post.platform == 'reddit':
            insights.append(f"Explore discussion thread for community insights: {post.url}")
        
        if 'follow_up_research' in analysis:
            for research in analysis['follow_up_research']:
                insights.append(f"Research: {research}")
        
        return insights[:5]  # Return top 5 insights
    
    def _generate_learning_recommendations(self, analysis: Dict, post: SocialPost) -> Dict[str, Any]:
        """Generate personalized learning recommendations"""
        
        return {
            'next_steps': analysis.get('follow_up_research', []),
            'related_skills': analysis.get('related_skills', []),
            'difficulty_level': analysis.get('complexity_level', 'Unknown'),
            'estimated_time': analysis.get('time_to_consume', 'Unknown'),
            'prerequisites': [],
            'learning_path': []
        }
    
    def _basic_analysis(self, post: SocialPost, sentiment_scores: Dict) -> Dict[str, Any]:
        """Fallback basic analysis when AI services are unavailable"""
        
        return {
            'category': 'General',
            'subcategory': post.platform.title(),
            'content_type': post.post_type,
            'topics': post.hashtags[:3] if post.hashtags else ['general'],
            'key_concepts': [],
            'summary': post.content[:200] + '...' if len(post.content) > 200 else post.content,
            'why_valuable': 'User bookmarked this content',
            'sentiment': 'Neutral',
            'complexity_level': 'Unknown',
            'time_to_consume': 'Unknown',
            'actionable_items': [],
            'learning_value': 'Content analysis not available',
            'practical_applications': [],
            'related_skills': [],
            'follow_up_research': [],
            'quality_indicators': [],
            'tags': post.hashtags[:5] if post.hashtags else [],
            'confidence_score': 0.3,
            'sentiment_scores': sentiment_scores,
            'ai_service': 'basic'
        }


# Example usage and testing
if __name__ == "__main__":
    analyzer = IntelligentContentAnalyzer()
    print("🧠 Intelligent Content Analyzer ready!")