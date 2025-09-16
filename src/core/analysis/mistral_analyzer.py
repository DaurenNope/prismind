import json
import os
from typing import Any, Dict, List

import requests
from loguru import logger


class MistralAnalyzer:
    """AI content analyzer using official Mistral AI API"""
    
    def __init__(self):
        self.api_key = os.getenv('MISTRAL_API_KEY')
        self.base_url = "https://api.mistral.ai/v1"
        self.model = "mistral-small-latest"  # Let's try latest instead of version
        
        if not self.api_key:
            logger.warning("MISTRAL_API_KEY not found in environment")
    
    def analyze_content(self, content: str, url: str = "", platform: str = "") -> Dict[str, Any]:
        """Analyze social media content using Mistral AI"""
        if not self.api_key:
            logger.error("Mistral API key not available")
            return self._basic_analysis(content, platform)
        
        try:
            logger.info(f"Analyzing content with Mistral AI ({self.model})...")
            
            prompt = self._create_analysis_prompt(content, url, platform)
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "You are an expert content analyzer specializing in social media posts."},
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 1000,
                    "temperature": 0.1
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                logger.success("Mistral AI analysis completed")
                return self._parse_ai_response(content)
            else:
                logger.error(f"Mistral API error {response.status_code}: {response.text}")
                return self._basic_analysis(content, platform)
                
        except Exception as e:
            logger.error(f"Mistral analysis failed: {e}")
            return self._basic_analysis(content, platform)
    
    def _create_analysis_prompt(self, content: str, url: str, platform: str) -> str:
        """Create a more detailed and structured analysis prompt for Mistral AI."""
        return f"""As an expert content analyst, please analyze the following post from {platform.title()}.

[POST CONTENT]
---
{content}
---
[POST URL]
{url}

Your task is to deconstruct this content and provide a structured analysis in JSON format. The JSON object should have the following keys:

- "main_topic": A 1-3 word summary of the post's central theme.
- "primary_category": The single most relevant category. Choose from: Technology, Business, AI, Marketing, Finance, Science, Health, Art, Entertainment, Lifestyle, Politics, News, Education, Other.
- "sub_categories": A list of 1-3 relevant sub-categories.
- "key_concepts": A list of 3-5 key terms, concepts, or entities mentioned.
- "summary": A concise, 2-3 sentence summary of the key message or information.
- "sentiment": The overall sentiment. Choose from: Positive, Negative, Neutral, Mixed.
- "value_score": An integer from 1 to 10, based on the following criteria:
    - 1-2: Spam, irrelevant, or very low value.
    - 3-4: Mildly interesting, but not particularly useful.
    - 5-6: Generally interesting, worth a quick read.
    - 7-8: High-quality, insightful, and actionable content.
    - 9-10: Exceptional, must-read content with significant value.

Please provide ONLY the JSON object in your response.
"""
    
    def _parse_ai_response(self, response: str) -> Dict[str, Any]:
        """Parse the JSON response from Mistral AI into a structured dictionary."""
        try:
            # Clean up the response to ensure it's valid JSON
            # The model sometimes includes markdown backticks
            clean_response = response.strip().replace('```json', '').replace('```', '')
            data = json.loads(clean_response)
            
            # Validate and structure the data
            return {
                'topic': data.get('main_topic', 'Uncategorized'),
                'category': data.get('primary_category', 'Uncategorized'),
                'key_concepts': data.get('key_concepts', []),
                'summary': data.get('summary', ''),
                'sentiment': data.get('sentiment', 'Neutral'),
                'value_score': int(data.get('value_score', 5)),
            }
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from Mistral response: {e}")
            logger.debug(f"Raw response was: {response}")
            return self._basic_analysis(response, "unknown") # Fallback to basic parsing
        except Exception as e:
            logger.error(f"An unexpected error occurred while parsing the AI response: {e}")
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
    
    def analyze_batch(self, posts: List) -> List[Dict]:
        """Analyze a batch of posts, compatible with main application"""
        analyzed_posts = []
        
        for i, post in enumerate(posts):
            logger.info(f"Analyzing post {i+1}/{len(posts)} from {post.platform}")
            
            try:
                # Use the analyze_content method
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
                        'value_score': analysis.get('value_score', 5),  # Use AI-generated score
                        'tags': analysis.get('key_concepts', [])[:5],
                        'confidence_score': 0.9  # Mistral is reliable
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
    
    def test_connection(self) -> bool:
        """Test connection to Mistral API"""
        if not self.api_key:
            logger.error("No Mistral API key provided")
            return False
            
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "user", "content": "Say 'Hello Mistral!' if you're working"}
                    ],
                    "max_tokens": 10
                }
            )
            
            if response.status_code == 200:
                logger.success("✅ Mistral AI connection successful")
                return True
            else:
                logger.error(f"❌ Mistral API error: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Mistral connection failed: {e}")
            return False 