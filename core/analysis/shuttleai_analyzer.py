import requests
import json
import time
from typing import List, Dict, Any
from dataclasses import asdict
import sys
from pathlib import Path
import openai
import os
from loguru import logger
sys.path.append(str(Path(__file__).parent.parent))
from core.extraction.social_extractor_base import SocialPost

class ShuttleAIAnalyzer:
    """AI content analyzer using ShuttleAI API as primary, with CometAPI and Gemini fallbacks"""
    
    def __init__(self):
        self.shuttleai_api_key = os.getenv('SHUTTLEAI_API_KEY')
        self.cometapi_api_key = os.getenv('COMETAPI_API_KEY')
        
        # ShuttleAI client
        self.shuttleai_client = None
        if self.shuttleai_api_key:
            self.shuttleai_client = openai.OpenAI(
                api_key=self.shuttleai_api_key,
                base_url="https://api.shuttleai.com/v1"
            )
        
        # CometAPI client
        self.cometapi_client = None
        if self.cometapi_api_key:
            self.cometapi_client = openai.OpenAI(
                api_key=self.cometapi_api_key,
                base_url="https://api.cometapi.com"
            )
            
        # Gemini fallback
        self.gemini_analyzer = None
        try:
            from .social_content_analyzer import SocialContentAnalyzer
            self.gemini_analyzer = SocialContentAnalyzer()
            logger.info("Fallback Gemini analyzer initialized")
        except Exception as e:
            logger.warning(f"Could not initialize Gemini fallback: {e}")
        
    def analyze_post(self, post: SocialPost) -> Dict:
        """Analyze a single social media post using ShuttleAI"""
        
        prompt = f"""
Analyze this social media post and provide a JSON response with the following structure:

{{
    "category": "Main category (Technology, Business, Entertainment, News, Education, etc.)",
    "subcategory": "Specific subcategory within the main category",
    "content_type": "Type of content (Tweet, Thread, Video, Image, Article, etc.)",
    "summary": "Brief 2-3 sentence summary of the key points",
    "sentiment": "Overall sentiment (Positive, Negative, Neutral)",
    "value_score": "Usefulness/importance score from 1-10",
    "tags": ["relevant", "keywords", "and", "topics"],
    "confidence_score": "Confidence in analysis from 0.0-1.0"
}}

Post Details:
- Platform: {post.platform}
- Author: {post.author} ({post.author_handle})
- Content: {post.content}
- Hashtags: {post.hashtags}
- Engagement: {post.engagement}
- URL: {post.url}

Provide only the JSON response, no additional text.
"""

        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.shuttleai_api_key}"
            }
            
            payload = {
                "model": "shuttle-3",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert social media content analyst. Analyze posts and categorize them accurately. Always respond with valid JSON only."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                "max_tokens": 500,
                "temperature": 0.3
            }
            
            response = requests.post(
                "https://api.shuttleai.com/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content'].strip()
                
                # Clean up the response to extract JSON
                if content.startswith('```json'):
                    content = content[7:]
                if content.endswith('```'):
                    content = content[:-3]
                content = content.strip()
                
                try:
                    analysis = json.loads(content)
                    return analysis
                except json.JSONDecodeError as e:
                    print(f"⚠️ JSON decode error: {e}")
                    print(f"Raw content: {content}")
                    return self._get_fallback_analysis(post)
                    
            elif response.status_code == 429:
                print("⏳ Rate limit hit, waiting 10 seconds...")
                time.sleep(10)
                return self.analyze_post(post)  # Retry
            else:
                print(f"❌ ShuttleAI API error: {response.status_code} - {response.text}")
                return self._get_fallback_analysis(post)
                
        except Exception as e:
            print(f"❌ Error calling ShuttleAI API: {e}")
            return self._get_fallback_analysis(post)
    
    def _get_fallback_analysis(self, post: SocialPost) -> Dict:
        """Provide basic analysis when AI fails"""
        return {
            "category": "Uncategorized",
            "subcategory": "Unknown", 
            "content_type": post.post_type.title(),
            "summary": post.content[:200] + "..." if len(post.content) > 200 else post.content,
            "sentiment": "Neutral",
            "value_score": 5,
            "tags": post.hashtags[:5] if post.hashtags else [],
            "confidence_score": 0.1
        }
    
    def analyze_batch(self, posts: List[SocialPost], batch_size: int = 5) -> List[Dict]:
        """Analyze multiple posts in batches"""
        analyzed_posts = []
        
        print(f"🧠 Analyzing {len(posts)} posts with ShuttleAI...")
        
        for i in range(0, len(posts), batch_size):
            batch = posts[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(posts) + batch_size - 1) // batch_size
            
            print(f"🧠 Analyzing batch {batch_num}/{total_batches} ({len(batch)} posts)...")
            
            for post in batch:
                try:
                    analysis = self.analyze_post(post)
                    analyzed_posts.append({
                        'post': post,
                        'analysis': analysis
                    })
                    
                    # Small delay to be nice to the API
                    time.sleep(0.5)
                    
                except Exception as e:
                    print(f"❌ Error analyzing post {post.post_id}: {e}")
                    analyzed_posts.append({
                        'post': post,
                        'analysis': self._get_fallback_analysis(post)
                    })
            
            # Longer delay between batches
            if i + batch_size < len(posts):
                print("⏳ Pausing between batches...")
                time.sleep(2)
        
        return analyzed_posts
    
    def test_connection(self) -> bool:
        """Test if the ShuttleAI API is working"""
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.shuttleai_api_key}"
            }
            
            payload = {
                "model": "shuttle-3",
                "messages": [
                    {"role": "user", "content": "Say 'Hello ShuttleAI!' if you're working"}
                ],
                "max_tokens": 10
            }
            
            response = requests.post(
                "https://api.shuttleai.com/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                print("✅ ShuttleAI connection successful!")
                return True
            else:
                print(f"❌ ShuttleAI connection failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ ShuttleAI connection error: {e}")
            return False

    def analyze_content(self, content: str, url: str = "", platform: str = "") -> Dict[str, Any]:
        """Analyze social media content with multiple AI service fallbacks"""
        
        # Try ShuttleAI first
        if self.shuttleai_client:
            try:
                return self._analyze_with_shuttleai(content, url, platform)
            except Exception as e:
                logger.warning(f"ShuttleAI failed: {e}, trying CometAPI...")
        
        # Try CometAPI second
        if self.cometapi_client:
            try:
                return self._analyze_with_cometapi(content, url, platform)
            except Exception as e:
                logger.warning(f"CometAPI failed: {e}, trying Gemini...")
        
        # Fall back to Gemini
        if self.gemini_analyzer:
            try:
                # Create a mock SocialPost object for Gemini analyzer
                from core.extraction.social_extractor_base import SocialPost
                mock_post = SocialPost(
                    platform=platform,
                    post_id="fallback",
                    author="Unknown",
                    author_handle="unknown",
                    content=content,
                    created_at="",
                    url=url,
                    post_type="post",
                    media_urls=[],
                    hashtags=[],
                    mentions=[],
                    engagement={},
                    is_saved=True,
                    saved_at="",
                    folder_category=""
                )
                
                # Use the correct method name
                analysis = self.gemini_analyzer.analyze_social_post(mock_post)
                
                # Convert to expected format
                return {
                    'category': analysis.get('category', 'Uncategorized'),
                    'topic': analysis.get('subcategory', ''),
                    'key_concepts': analysis.get('topics', [])[:3],
                    'summary': analysis.get('summary', ''),
                    'sentiment': analysis.get('sentiment', 'Neutral')
                }
                
            except Exception as e:
                logger.error(f"All AI services failed, Gemini error: {e}")
        
        # Return basic analysis if all fail
        logger.error("All AI analysis services failed, returning basic analysis")
        return self._basic_analysis(content, platform)
    
    def _analyze_with_shuttleai(self, content: str, url: str, platform: str) -> Dict[str, Any]:
        """Analyze content using ShuttleAI"""
        logger.info("Analyzing content with ShuttleAI...")
        
        prompt = self._create_analysis_prompt(content, url, platform)
        
        response = self.shuttleai_client.chat.completions.create(
            model="shuttle-3-mini",  # Use the mini model for better rate limits
            messages=[
                {"role": "system", "content": "You are an expert content analyzer specializing in social media posts."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.1,
            timeout=30  # Add 30 second timeout
        )
        
        result = response.choices[0].message.content
        logger.success("ShuttleAI analysis completed")
        return self._parse_ai_response(result)
    
    def _analyze_with_cometapi(self, content: str, url: str, platform: str) -> Dict[str, Any]:
        """Analyze content using CometAPI"""
        logger.info("Analyzing content with CometAPI...")
        
        prompt = self._create_analysis_prompt(content, url, platform)
        
        response = self.cometapi_client.chat.completions.create(
            model="gpt-4o-mini",  # Use efficient model
            messages=[
                {"role": "system", "content": "You are an expert content analyzer specializing in social media posts."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.1,
            timeout=30  # Add 30 second timeout
        )
        
        result = response.choices[0].message.content
        logger.success("CometAPI analysis completed")
        return self._parse_ai_response(result)
    
    def _create_analysis_prompt(self, content: str, url: str, platform: str) -> str:
        """Create analysis prompt for AI services"""
        return f"""Analyze this {platform} post and extract key information:

Content: {content}
URL: {url}

Please provide:
1. Main topic/theme (1-3 words)
2. Category (Technology, Business, AI, Marketing, Finance, etc.)
3. Key concepts (2-4 important terms)
4. Brief summary (1-2 sentences)
5. Sentiment (Positive/Negative/Neutral)

Format your response as:
TOPIC: [topic]
CATEGORY: [category]  
CONCEPTS: [concept1, concept2, concept3]
SUMMARY: [summary]
SENTIMENT: [sentiment]"""
    
    def _parse_ai_response(self, response: str) -> Dict[str, Any]:
        """Parse AI response into structured data"""
        try:
            result = {
                'category': 'Uncategorized',
                'topic': '',
                'key_concepts': [],
                'summary': '',
                'sentiment': 'Neutral'
            }
            
            for line in response.split('\n'):
                line = line.strip()
                if line.startswith('TOPIC:'):
                    result['topic'] = line.replace('TOPIC:', '').strip()
                elif line.startswith('CATEGORY:'):
                    result['category'] = line.replace('CATEGORY:', '').strip()
                elif line.startswith('CONCEPTS:'):
                    concepts_str = line.replace('CONCEPTS:', '').strip()
                    result['key_concepts'] = [c.strip() for c in concepts_str.split(',') if c.strip()]
                elif line.startswith('SUMMARY:'):
                    result['summary'] = line.replace('SUMMARY:', '').strip()
                elif line.startswith('SENTIMENT:'):
                    result['sentiment'] = line.replace('SENTIMENT:', '').strip()
            
            return result
            
        except Exception as e:
            logger.error(f"Error parsing AI response: {e}")
            return self._basic_analysis(response, "unknown")
    
    def _basic_analysis(self, content: str, platform: str) -> Dict[str, Any]:
        """Provide basic analysis when AI services fail"""
        return {
            'category': 'Uncategorized',
            'topic': platform.title() if platform else 'Social Media',
            'key_concepts': ['social', 'media', 'content'],
            'summary': f'Content from {platform}' if platform else 'Social media content',
            'sentiment': 'Neutral'
        }
    
    def analyze_batch(self, posts: list) -> list:
        """Analyze a batch of posts, compatible with main application"""
        from typing import List, Dict
        analyzed_posts = []
        
        for i, post in enumerate(posts):
            logger.info(f"Analyzing post {i+1}/{len(posts)} from {post.platform}")
            
            try:
                # Use the new analyze_content method
                analysis = self.analyze_content(
                    content=post.content,
                    url=post.url,
                    platform=post.platform
                )
                
                # Convert to expected format for main application
                analyzed_posts.append({
                    'post': post,
                    'analysis': {
                        'category': analysis.get('category', 'Uncategorized'),
                        'subcategory': analysis.get('topic', ''),
                        'content_type': post.post_type.title() if hasattr(post, 'post_type') else 'Post',
                        'summary': analysis.get('summary', ''),
                        'sentiment': analysis.get('sentiment', 'Neutral'),
                        'value_score': 7,  # Default score
                        'tags': analysis.get('key_concepts', [])[:5],
                        'confidence_score': 0.8
                    }
                })
                
            except Exception as e:
                logger.error(f"Failed to analyze post {i+1}: {e}")
                # Add basic analysis for failed posts
                analyzed_posts.append({
                    'post': post,
                    'analysis': {
                        'category': 'Uncategorized',
                        'subcategory': 'Error',
                        'content_type': post.post_type.title() if hasattr(post, 'post_type') else 'Post',
                        'summary': post.content[:200] + "..." if len(post.content) > 200 else post.content,
                        'sentiment': 'Neutral',
                        'value_score': 5,
                        'tags': [],
                        'confidence_score': 0.0
                    }
                })
        
        return analyzed_posts 