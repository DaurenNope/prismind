#!/usr/bin/env python3
"""
Local Media Analyzer for Social Posts
Uses OCR + Local AI to analyze images and enhance post value
"""

import requests
import os
from pathlib import Path
from PIL import Image
import pytesseract
import json
import re
import logging
from typing import Dict, List, Optional

# Set up logging
logging.basicConfig(level=logging.INFO)

class LocalMediaAnalyzer:
    """Analyzes media content using local OCR + AI"""
    
    def __init__(self, ollama_url: str = "http://localhost:11434"):
        self.ollama_url = ollama_url
        self.model = "qwen3:8b"
        
    def analyze_post_media(self, post: Dict) -> Dict:
        """Analyze all media in a post and enhance its value score"""
        media_urls = post.get('media_urls', [])
        if not media_urls:
            return post
        
        logging.info(f"Analyzing {len(media_urls)} media items for post {post.get('post_id', 'unknown')}")
        
        media_analysis = []
        total_value_boost = 0
        
        for i, media_url in enumerate(media_urls):
            try:
                # Download and analyze media
                analysis = self._analyze_single_media(media_url, f"media_{i}")
                if analysis:
                    media_analysis.append(analysis)
                    # Boost value score based on media content
                    value_boost = self._calculate_value_boost(analysis)
                    total_value_boost += value_boost
                    
            except Exception as e:
                logging.error(f"Failed to analyze media {i}: {e}")
        
        # Enhance the post with media analysis
        enhanced_post = post.copy()
        enhanced_post['media_analysis'] = media_analysis
        enhanced_post['media_value_boost'] = total_value_boost
        
        # Recalculate value score
        original_score = post.get('value_score', 5)
        new_score = min(10, original_score + total_value_boost)
        enhanced_post['value_score'] = new_score
        
        # Add media insights to key_insights
        media_insights = self._extract_media_insights(media_analysis)
        if media_insights:
            existing_insights = enhanced_post.get('key_insights', [])
            enhanced_post['key_insights'] = existing_insights + media_insights
        
        return enhanced_post
    
    def _analyze_single_media(self, media_url: str, media_id: str) -> Optional[Dict]:
        """Analyze a single media item"""
        try:
            # Handle local files vs URLs
            if media_url.startswith('http'):
                # Download media
                response = requests.get(media_url, timeout=30)
                if response.status_code != 200:
                    return None
                
                # Save to temporary file
                temp_path = f"/tmp/{media_id}.png"
                with open(temp_path, 'wb') as f:
                    f.write(response.content)
                
                # Analyze with OCR + AI
                analysis = self._analyze_image_file(temp_path)
                
                # Clean up
                os.remove(temp_path)
                
                return analysis
            else:
                # Local file path
                if Path(media_url).exists():
                    return self._analyze_image_file(media_url)
                else:
                    logging.error(f"Local file not found: {media_url}")
                    return None
            
        except Exception as e:
            logging.error(f"Failed to analyze media {media_id}: {e}")
            return None
    
    def _analyze_image_file(self, file_path: str) -> Dict:
        """Analyze an image file using OCR + AI"""
        try:
            # Load image
            image = Image.open(file_path)
            
            # Extract text using OCR
            ocr_text = pytesseract.image_to_string(image)
            lines = [line.strip() for line in ocr_text.split('\n') if line.strip()]
            clean_text = '\n'.join(lines)
            
            if not clean_text:
                return {
                    "media_type": "image",
                    "ocr_text": "",
                    "analysis": {
                        "description": "Image with no readable text",
                        "content_type": "visual_only",
                        "value_score": 3
                    }
                }
            
            # Analyze with AI
            ai_analysis = self._analyze_text_with_ai(clean_text)
            
            return {
                "media_type": "image",
                "ocr_text": clean_text,
                "analysis": ai_analysis
            }
            
        except Exception as e:
            logging.error(f"Failed to analyze image {file_path}: {e}")
            return None
    
    def _analyze_text_with_ai(self, text: str) -> Dict:
        """Analyze extracted text with local AI"""
        try:
            prompt = f"""
            Analyze this text extracted from a social media post image:
            
            TEXT:
            {text}
            
            Provide analysis in this exact format:
            
            DESCRIPTION: Brief description of the content
            TECHNICAL_ELEMENTS: List of technical terms, code, tools found
            CONTENT_TYPE: Type (code, tutorial, meme, showcase, etc.)
            VALUE_SCORE: How valuable this content is (1-10)
            KEY_INSIGHTS: Important takeaways (max 3 points)
            """
            
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                ai_response = result.get('response', '')
                
                # Parse the structured response
                analysis = self._parse_ai_response(ai_response)
                return analysis
            else:
                return {"error": f"AI analysis failed: {response.status_code}"}
                
        except Exception as e:
            return {"error": f"AI analysis failed: {e}"}
    
    def _parse_ai_response(self, response: str) -> Dict:
        """Parse structured AI response"""
        analysis = {
            "description": "",
            "technical_elements": [],
            "content_type": "unknown",
            "value_score": 5,
            "key_insights": []
        }
        
        # Extract description
        desc_match = re.search(r'DESCRIPTION:\s*(.*?)(?=\n[A-Z_]+:|$)', response, re.DOTALL | re.IGNORECASE)
        if desc_match:
            analysis["description"] = desc_match.group(1).strip()
        
        # Extract technical elements
        tech_match = re.search(r'TECHNICAL_ELEMENTS:\s*(.*?)(?=\n[A-Z_]+:|$)', response, re.DOTALL | re.IGNORECASE)
        if tech_match:
            tech_text = tech_match.group(1).strip()
            analysis["technical_elements"] = [item.strip() for item in tech_text.split(',') if item.strip()]
        
        # Extract content type
        type_match = re.search(r'CONTENT_TYPE:\s*(.*?)(?=\n[A-Z_]+:|$)', response, re.DOTALL | re.IGNORECASE)
        if type_match:
            analysis["content_type"] = type_match.group(1).strip()
        
        # Extract value score
        score_match = re.search(r'VALUE_SCORE:\s*(\d+)', response, re.IGNORECASE)
        if score_match:
            score = int(score_match.group(1))
            if 1 <= score <= 10:
                analysis["value_score"] = score
        
        # Extract key insights
        insights_match = re.search(r'KEY_INSIGHTS:\s*(.*?)(?=\n[A-Z_]+:|$)', response, re.DOTALL | re.IGNORECASE)
        if insights_match:
            insights_text = insights_match.group(1).strip()
            analysis["key_insights"] = [insight.strip() for insight in insights_text.split('\n') if insight.strip()]
        
        return analysis
    
    def _calculate_value_boost(self, media_analysis: Dict) -> int:
        """Calculate how much to boost the post's value score based on media content"""
        analysis = media_analysis.get('analysis', {})
        content_type = analysis.get('content_type', '').lower()
        value_score = analysis.get('value_score', 5)
        
        # Base boost from AI value score
        boost = max(0, value_score - 5)  # Boost if AI thinks it's valuable
        
        # Additional boosts for specific content types
        if 'code' in content_type or 'tutorial' in content_type:
            boost += 2  # Code and tutorials are very valuable
        elif 'showcase' in content_type:
            boost += 1  # Showcases are moderately valuable
        elif 'meme' in content_type:
            boost -= 1  # Memes are less valuable for learning
        
        return min(3, boost)  # Cap at +3 boost
    
    def _extract_media_insights(self, media_analysis: List[Dict]) -> List[str]:
        """Extract key insights from media analysis"""
        insights = []
        for analysis in media_analysis:
            ai_analysis = analysis.get('analysis', {})
            key_insights = ai_analysis.get('key_insights', [])
            insights.extend(key_insights[:2])  # Take top 2 insights per media
        
        return insights[:5]  # Limit to 5 total insights
    
    def batch_analyze_posts(self, posts: List[Dict]) -> List[Dict]:
        """Analyze media for multiple posts"""
        enhanced_posts = []
        
        for post in posts:
            enhanced_post = self.analyze_post_media(post)
            enhanced_posts.append(enhanced_post)
        
        return enhanced_posts

def main():
    """Test the local media analyzer"""
    print("🔍 Testing Local Media Analyzer")
    print("=" * 40)
    
    analyzer = LocalMediaAnalyzer()
    
    # Test with a sample post
    sample_post = {
        'post_id': 'test_123',
        'content': 'cursor nerds this is for you',
        'value_score': 3,
        'media_urls': [
            'https://example.com/image1.png'  # This would be a real URL
        ]
    }
    
    # For testing, we'll use the downloaded images
    media_dir = Path("downloaded_media")
    if media_dir.exists():
        for image_file in media_dir.glob("*.png"):
            print(f"\n🔍 Testing with: {image_file.name}")
            
            # Create a test post with this image
            test_post = {
                'post_id': f'test_{image_file.stem}',
                'content': 'cursor nerds this is for you',
                'value_score': 3,
                'media_urls': [str(image_file)]
            }
            
            enhanced_post = analyzer.analyze_post_media(test_post)
            
            print(f"✅ Original Score: {test_post['value_score']}")
            print(f"⭐ Enhanced Score: {enhanced_post['value_score']}")
            print(f"🚀 Value Boost: +{enhanced_post.get('media_value_boost', 0)}")
            
            media_analysis = enhanced_post.get('media_analysis', [])
            if media_analysis:
                analysis = media_analysis[0].get('analysis', {})
                print(f"📝 Description: {analysis.get('description', 'N/A')}")
                print(f"🏷️ Content Type: {analysis.get('content_type', 'N/A')}")

if __name__ == "__main__":
    main() 