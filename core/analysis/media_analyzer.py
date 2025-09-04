"""
Intelligent Media Analysis for PrisMind
Analyzes images and videos from social media posts to extract insights
"""

import io
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from PIL import Image


class MediaAnalyzer:
    """Analyzes media content from social media posts"""
    
    def __init__(self):
        self.cache_file = Path("output/data/media_analysis_cache.json")
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self.analysis_cache = self._load_cache()
        
        # Initialize AI services
        self.gemini_api_key = os.getenv('GEMINI_API_KEY')
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        
    def _load_cache(self) -> Dict:
        """Load cached media analyses"""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"⚠️ Error loading media cache: {e}")
        return {}
    
    def _save_cache(self):
        """Save media analyses to cache"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.analysis_cache, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ Error saving media cache: {e}")
    
    def analyze_media_urls(self, media_urls: List[str], post_context: str = "") -> Dict[str, Any]:
        """Analyze a list of media URLs and extract insights"""
        if not media_urls:
            return {"insights": [], "summary": "No media content", "media_count": 0}
        
        # Create cache key
        cache_key = self._generate_cache_key(media_urls, post_context)
        
        # Check cache first
        if cache_key in self.analysis_cache:
            return self.analysis_cache[cache_key]
        
        analysis = self._perform_media_analysis(media_urls, post_context)
        
        # Cache the result
        self.analysis_cache[cache_key] = analysis
        self._save_cache()
        
        return analysis
    
    def _generate_cache_key(self, media_urls: List[str], post_context: str) -> str:
        """Generate a unique cache key for media analysis"""
        url_hash = str(hash(''.join(media_urls[:3])))  # Use first 3 URLs
        context_hash = str(hash(post_context[:100]))
        return f"media_{url_hash}_{context_hash}"
    
    def _perform_media_analysis(self, media_urls: List[str], post_context: str) -> Dict[str, Any]:
        """Perform actual media analysis"""
        insights = []
        analyzed_count = 0
        total_value_score = 0
        
        for url in media_urls[:5]:  # Analyze max 5 media items
            try:
                media_analysis = self._analyze_single_media(url, post_context)
                if media_analysis:
                    insights.append(media_analysis)
                    total_value_score += media_analysis.get('value_score', 0)
                    analyzed_count += 1
            except Exception as e:
                print(f"⚠️ Error analyzing media {url}: {e}")
        
        # Generate summary
        summary = self._generate_media_summary(insights, analyzed_count)
        
        # Calculate overall value score
        avg_score = total_value_score / analyzed_count if analyzed_count > 0 else 0
        
        return {
            "insights": insights,
            "summary": summary,
            "media_count": len(media_urls),
            "analyzed_count": analyzed_count,
            "value_score": round(avg_score, 1),
            "analysis_timestamp": datetime.now().isoformat()
        }
    
    def _analyze_single_media(self, media_url: str, post_context: str) -> Optional[Dict[str, Any]]:
        """Analyze a single media item"""
        try:
            # Determine media type
            media_type = self._get_media_type(media_url)
            
            if media_type == 'image':
                return self._analyze_image(media_url, post_context)
            elif media_type == 'video':
                return self._analyze_video(media_url, post_context)
            else:
                return None
                
        except Exception as e:
            print(f"❌ Error analyzing media {media_url}: {e}")
            return None
    
    def _get_media_type(self, url: str) -> str:
        """Determine if URL is image or video"""
        url_lower = url.lower()
        
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']
        video_extensions = ['.mp4', '.webm', '.mov', '.avi', '.mkv']
        
        for ext in image_extensions:
            if ext in url_lower:
                return 'image'
        
        for ext in video_extensions:
            if ext in url_lower:
                return 'video'
        
        # Check for platform-specific patterns
        if 'reddit.com' in url_lower and 'preview' in url_lower:
            return 'image'
        elif 'v.redd.it' in url_lower:
            return 'video'
        elif 'pbs.twimg.com' in url_lower:
            return 'image'
        
        return 'unknown'
    
    def _analyze_image(self, image_url: str, post_context: str) -> Dict[str, Any]:
        """Analyze an image using available AI services"""
        
        # Try Gemini Vision first
        if self.gemini_api_key:
            try:
                return self._analyze_image_with_gemini(image_url, post_context)
            except Exception as e:
                print(f"⚠️ Gemini analysis failed: {e}")
        
        # Try OpenAI Vision
        if self.openai_api_key:
            try:
                return self._analyze_image_with_openai(image_url, post_context)
            except Exception as e:
                print(f"⚠️ OpenAI analysis failed: {e}")
        
        # Fallback to basic analysis
        return self._basic_image_analysis(image_url, post_context)
    
    def _analyze_image_with_gemini(self, image_url: str, post_context: str) -> Dict[str, Any]:
        """Analyze image using Google Gemini Vision"""
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.gemini_api_key)
            
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            # Download and prepare image
            response = requests.get(image_url, timeout=10)
            image = Image.open(io.BytesIO(response.content))
            
            prompt = f"""
            Analyze this image in the context of this social media post: "{post_context[:200]}"
            
            Provide a structured analysis including:
            1. What's shown in the image (brief description)
            2. Key insights or information conveyed
            3. Relevance to the post context
            4. Educational or informational value (1-10)
            5. Any text, charts, or data visible
            
            Be concise and focus on extracting valuable information.
            """
            
            result = model.generate_content([prompt, image])
            
            return {
                'type': 'image',
                'url': image_url,
                'analysis': result.text,
                'value_score': self._extract_value_score(result.text),
                'insights': self._extract_key_insights(result.text),
                'analyzer': 'gemini-vision'
            }
            
        except Exception as e:
            print(f"❌ Gemini vision analysis failed: {e}")
            raise
    
    def _analyze_image_with_openai(self, image_url: str, post_context: str) -> Dict[str, Any]:
        """Analyze image using OpenAI Vision"""
        try:
            import openai
            client = openai.OpenAI(api_key=self.openai_api_key)
            
            response = client.chat.completions.create(
                model="gpt-4-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": f"""Analyze this image in context of: "{post_context[:200]}"
                                
                                Provide:
                                1. Brief description
                                2. Key insights
                                3. Educational value (1-10)
                                4. Relevance to context
                                """
                            },
                            {
                                "type": "image_url",
                                "image_url": {"url": image_url}
                            }
                        ]
                    }
                ],
                max_tokens=300
            )
            
            analysis_text = response.choices[0].message.content
            
            return {
                'type': 'image',
                'url': image_url,
                'analysis': analysis_text,
                'value_score': self._extract_value_score(analysis_text),
                'insights': self._extract_key_insights(analysis_text),
                'analyzer': 'openai-vision'
            }
            
        except Exception as e:
            print(f"❌ OpenAI vision analysis failed: {e}")
            raise
    
    def _basic_image_analysis(self, image_url: str, post_context: str) -> Dict[str, Any]:
        """Basic image analysis without AI vision"""
        try:
            # Download and analyze basic properties
            response = requests.get(image_url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
            image = Image.open(io.BytesIO(response.content))
            
            width, height = image.size
            format_type = image.format
            
            # Basic scoring based on image properties
            value_score = 3.0  # Base score
            
            # Size-based scoring (larger images often more detailed)
            if width > 1000 and height > 1000:
                value_score += 2.0
            elif width > 500 and height > 500:
                value_score += 1.0
            
            # Format bonus
            if format_type in ['PNG', 'JPEG']:
                value_score += 0.5
            
            insights = []
            if width > height * 2:  # Wide image, might be infographic
                insights.append("Wide format - possibly infographic or chart")
                value_score += 1.0
            
            analysis = f"{format_type} image ({width}x{height}). "
            if insights:
                analysis += " ".join(insights)
            
            return {
                'type': 'image',
                'url': image_url,
                'analysis': analysis,
                'value_score': min(value_score, 10.0),
                'insights': insights,
                'analyzer': 'basic',
                'properties': {
                    'width': width,
                    'height': height,
                    'format': format_type
                }
            }
            
        except Exception as e:
            print(f"❌ Basic image analysis failed: {e}")
            return {
                'type': 'image',
                'url': image_url,
                'analysis': 'Image analysis unavailable',
                'value_score': 2.0,
                'insights': [],
                'analyzer': 'failed'
            }
    
    def _analyze_video(self, video_url: str, post_context: str) -> Dict[str, Any]:
        """Analyze video content (basic implementation)"""
        # For now, provide basic video analysis
        # In the future, this could extract frames and analyze with AI
        
        return {
            'type': 'video',
            'url': video_url,
            'analysis': 'Video content detected. Full video analysis coming soon.',
            'value_score': 5.0,  # Default score for videos
            'insights': ['Video content may contain valuable visual information'],
            'analyzer': 'basic'
        }
    
    def _extract_value_score(self, analysis_text: str) -> float:
        """Extract value score from AI analysis text"""
        import re
        
        # Look for patterns like "value: 8/10", "8 out of 10", "score: 7"
        patterns = [
            r'value.*?(\d+)/10',
            r'(\d+)\s*out\s*of\s*10',
            r'score.*?(\d+)',
            r'educational.*?(\d+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, analysis_text.lower())
            if match:
                score = int(match.group(1))
                return min(max(score, 1), 10)  # Clamp between 1-10
        
        # Default scoring based on content quality indicators
        quality_indicators = ['chart', 'graph', 'data', 'diagram', 'infographic', 'tutorial', 'educational']
        score = 5.0  # Base score
        
        for indicator in quality_indicators:
            if indicator in analysis_text.lower():
                score += 0.5
        
        return min(score, 10.0)
    
    def _extract_key_insights(self, analysis_text: str) -> List[str]:
        """Extract key insights from analysis text"""
        insights = []
        
        # Look for common insight patterns
        lines = analysis_text.split('\n')
        for line in lines:
            line = line.strip()
            if any(starter in line.lower() for starter in ['shows', 'displays', 'contains', 'depicts', 'illustrates']):
                if len(line) > 20 and len(line) < 150:  # Reasonable length
                    insights.append(line)
        
        return insights[:3]  # Return top 3 insights
    
    def _generate_media_summary(self, insights: List[Dict], analyzed_count: int) -> str:
        """Generate a summary of media analysis"""
        if not insights:
            return "No media analysis available"
        
        image_count = sum(1 for insight in insights if insight.get('type') == 'image')
        video_count = sum(1 for insight in insights if insight.get('type') == 'video')
        
        summary_parts = []
        
        if image_count > 0:
            summary_parts.append(f"{image_count} image{'s' if image_count > 1 else ''}")
        
        if video_count > 0:
            summary_parts.append(f"{video_count} video{'s' if video_count > 1 else ''}")
        
        media_desc = " and ".join(summary_parts) if summary_parts else "media items"
        
        # Check for high-value content
        high_value_count = sum(1 for insight in insights if insight.get('value_score', 0) >= 7)
        
        if high_value_count > 0:
            return f"Analyzed {media_desc} with {high_value_count} high-value visual insights"
        elif analyzed_count > 0:
            return f"Analyzed {media_desc} with visual information"
        else:
            return f"Found {len(insights)} media items"