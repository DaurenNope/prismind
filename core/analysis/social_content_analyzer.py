import google.generativeai as genai
from typing import Dict, List
import json
import time
import sys
import os
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'extraction'))
from social_extractor_base import SocialPost

class SocialContentAnalyzer:
    def __init__(self, api_key: str = None):
        if api_key:
            genai.configure(api_key=api_key)
        else:
            # Try to get from environment
            api_key = os.getenv('GEMINI_API_KEY')
            if api_key:
                genai.configure(api_key=api_key)
            else:
                print("⚠️ No Gemini API key provided. Analyzer will use fallback analysis.")
        
        self.model = genai.GenerativeModel('gemini-1.5-pro')
        self.sentiment_analyzer = SentimentIntensityAnalyzer()
        
    def _get_sentiment(self, text: str) -> Dict[str, float]:
        """Get sentiment scores for a given text."""
        return self.sentiment_analyzer.polarity_scores(text)
        
    def analyze_social_post(self, post: SocialPost) -> Dict:
        """Analyze social media post using Gemini and VADER for sentiment analysis."""
        
        # Get sentiment scores from VADER
        sentiment_scores = self._get_sentiment(post.content)
        
        analysis_prompt = f"""
        Analyze this social media post and extract structured information:

        Platform: {post.platform}
        Author: {post.author} ({post.author_handle})
        Content: {post.content}
        Hashtags: {', '.join(post.hashtags) if post.hashtags else 'None'}
        Post Type: {post.post_type}
        Created: {post.created_at}
        Engagement: {post.engagement}

        Return a JSON object with the following structure:
        {{
          "category": "primary category (Technology, Learning, News, Entertainment, Personal, Business, etc.)",
          "subcategory": "more specific category",
          "content_type": "type of content (Article Link, Tutorial, News, Opinion, Meme, Discussion, etc.)",
          "topics": ["topic1", "topic2", "topic3"],
          "key_insights": ["insight1", "insight2"],
          "summary": "2-3 sentence summary of the key information",
          "sentiment": "Positive, Negative, Neutral, Mixed",
          "value_score": "score from 1-10 indicating how valuable this content is for knowledge building",
          "action_items": ["action1", "action2"],
          "related_concepts": ["concept1", "concept2"],
          "save_reason": "why someone might have saved this content",
          "tags": ["tag1", "tag2", "tag3"],
          "confidence_score": 0.85
        }}

        Focus on extracting maximum value for knowledge management and future reference.
        Only return valid JSON, no additional text.
        """
        
        max_retries = 2  # Reduced from 3
        retry_delay = 10  # Reduced from 60 seconds
        
        for attempt in range(max_retries):
            try:
                print(f"🤖 Analyzing post with Gemini (attempt {attempt + 1}/{max_retries})...")
                
                # Add timeout to prevent hanging
                # Allow mocked model to be called simply as model.generate_content(prompt)
                try:
                    response = self.model.generate_content(
                        analysis_prompt,
                        generation_config=genai.types.GenerationConfig(
                            temperature=0.1,
                            max_output_tokens=1000,
                            timeout=30  # 30 second timeout
                        )
                    )
                except TypeError:
                    # Fallback for mocked call signature
                    response = self.model.generate_content(analysis_prompt)
                
                # Clean and parse response
                response_text = response.text.strip()
                if response_text.startswith('```json'):
                    response_text = response_text[7:-3]
                elif response_text.startswith('```'):
                    response_text = response_text[3:-3]
                
                analysis = json.loads(response_text)
                # Normalize keys expected by tests
                if 'key_points' not in analysis and 'key_insights' in analysis:
                    analysis['key_points'] = analysis.get('key_insights', [])
                # Ensure sentiment exists
                if 'sentiment' not in analysis:
                    # Derive simple sentiment label from VADER compound
                    compound = self._get_sentiment(post.content).get('compound', 0.0)
                    analysis['sentiment'] = 'Positive' if compound > 0.2 else ('Negative' if compound < -0.2 else 'Neutral')
                
                # Add sentiment scores and other metadata
                analysis['sentiment_scores'] = sentiment_scores
                analysis['analyzed_at'] = time.time()
                analysis['platform'] = post.platform
                analysis['original_author'] = post.author
                analysis['post_url'] = post.url
                analysis['engagement_metrics'] = post.engagement
                
                print(f"✅ Gemini analysis completed successfully")
                return analysis
                
            except json.JSONDecodeError as e:
                print(f"❌ JSON parsing error: {e}")
                if attempt < max_retries - 1:
                    print(f"⏳ Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 1.5  # Gentler backoff
                    continue
                else:
                    print(f"❌ Failed to parse JSON after {max_retries} attempts")
                    return self._get_fallback_analysis(post)
                
            except Exception as e:
                error_str = str(e)
                if "429" in error_str and attempt < max_retries - 1:
                    print(f"⏳ Rate limit hit, waiting {retry_delay} seconds before retry {attempt + 2}/{max_retries}")
                    time.sleep(retry_delay)
                    retry_delay *= 1.5  # Gentler backoff
                    continue
                elif "timeout" in error_str.lower() or "deadline" in error_str.lower():
                    print(f"⏰ Timeout occurred, retrying in {retry_delay} seconds...")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        retry_delay *= 1.5
                    continue
                else:
                    print(f"❌ Error analyzing social post: {e}")
                    return self._get_fallback_analysis(post)
    
        # If we get here, all retries failed
        print(f"❌ All {max_retries} attempts failed, using fallback analysis")
        return self._get_fallback_analysis(post)
    
    def analyze_batch(self, posts: List[SocialPost], batch_size: int = 2) -> List[Dict]:  # Reduced batch size
        """Analyze multiple posts in batches"""
        analyzed_posts = []
        
        for i in range(0, len(posts), batch_size):
            batch = posts[i:i + batch_size]
            
            print(f"🧠 Analyzing batch {i//batch_size + 1} ({len(batch)} posts)...")
            
            for post in batch:
                analysis = self.analyze_social_post(post)
                analyzed_posts.append({
                    'post': post,
                    'analysis': analysis
                })
                
                # Shorter delay between posts
                time.sleep(1)  # Reduced from 2 seconds
        
        return analyzed_posts
    
    def generate_content_summary(self, analyzed_posts: List[Dict]) -> Dict:
        """Generate overall summary of saved content"""
        
        if not analyzed_posts:
            return {}
        
        # Aggregate data
        categories = {}
        platforms = {}
        total_value = 0
        sentiment_counts = {'Positive': 0, 'Negative': 0, 'Neutral': 0, 'Mixed': 0}
        
        for item in analyzed_posts:
            analysis = item['analysis']
            post = item['post']
            
            # Count categories
            category = analysis.get('category', 'Unknown')
            categories[category] = categories.get(category, 0) + 1
            
            # Count platforms
            platform = post.platform
            platforms[platform] = platforms.get(platform, 0) + 1
            
            # Sum value scores
            total_value += analysis.get('value_score', 5)
            
            # Count sentiments
            sentiment = analysis.get('sentiment', 'Neutral')
            if sentiment in sentiment_counts:
                sentiment_counts[sentiment] += 1
        
        avg_value = total_value / len(analyzed_posts) if analyzed_posts else 0
        
        return {
            'total_posts': len(analyzed_posts),
            'platforms': platforms,
            'top_categories': sorted(categories.items(), key=lambda x: x[1], reverse=True)[:5],
            'average_value_score': round(avg_value, 2),
            'sentiment_distribution': sentiment_counts,
            'analysis_date': time.time()
        }
    
    def _get_fallback_analysis(self, post: SocialPost) -> Dict:
        """Fallback analysis when AI fails"""
        return {
            "category": "Uncategorized",
            "subcategory": "Unknown",
            "content_type": post.post_type.title(),
            "topics": post.hashtags[:3] if post.hashtags else [],
            "key_insights": [],
            "summary": post.content[:200] + "..." if len(post.content) > 200 else post.content,
            "sentiment": "Neutral",
            "value_score": 5,
            "action_items": [],
            "related_concepts": [],
            "save_reason": "User saved this content",
            "tags": post.hashtags[:5] if post.hashtags else [],
            "confidence_score": 0.0,
            "analyzed_at": time.time(),
            "platform": post.platform,
            "original_author": post.author,
            "post_url": post.url,
            "engagement_metrics": post.engagement
        } 