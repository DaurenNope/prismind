"""
Tweet Engagement Analyzer for PrisMind
Handles engagement metrics and content analysis
"""

import re
from typing import Dict, List, Optional, Any

from playwright.async_api import ElementHandle


class TweetEngagementAnalyzer:
    """Handles engagement metrics and content analysis"""
    
    def __init__(self):
        pass
    
    async def extract_engagement_metrics(self, tweet_element: ElementHandle) -> Dict:
        """Extract engagement metrics (likes, retweets, replies)"""
        engagement = {}
        try:
            # Extract likes
            like_elements = await tweet_element.query_selector_all('[data-testid="like"]')
            if like_elements:
                like_text = await like_elements[0].inner_text()
                engagement['likes'] = self._parse_engagement_count(like_text)
            
            # Extract retweets
            retweet_elements = await tweet_element.query_selector_all('[data-testid="retweet"]')
            if retweet_elements:
                retweet_text = await retweet_elements[0].inner_text()
                engagement['retweets'] = self._parse_engagement_count(retweet_text)
            
            # Extract replies
            reply_elements = await tweet_element.query_selector_all('[data-testid="reply"]')
            if reply_elements:
                reply_text = await reply_elements[0].inner_text()
                engagement['replies'] = self._parse_engagement_count(reply_text)
            
            return engagement
        except Exception as e:
            print(f"⚠️ Error extracting engagement metrics: {e}")
            return {}
    
    def _parse_engagement_count(self, text: str) -> int:
        """Parse engagement count from text (e.g., '1.2K' -> 1200)"""
        try:
            if not text or text.strip() == '':
                return 0
            
            text = text.strip().upper()
            
            # Handle K, M suffixes
            if 'K' in text:
                number = float(text.replace('K', ''))
                return int(number * 1000)
            elif 'M' in text:
                number = float(text.replace('M', ''))
                return int(number * 1000000)
            else:
                # Remove any non-numeric characters except decimal point
                cleaned = re.sub(r'[^\d.]', '', text)
                if cleaned:
                    return int(float(cleaned))
                return 0
        except:
            return 0
    
    def extract_hashtags(self, content: str) -> List[str]:
        """Extract hashtags from content"""
        if not content:
            return []
        
        hashtags = re.findall(r'#(\w+)', content)
        return list(set(hashtags))
    
    def extract_mentions(self, content: str) -> List[str]:
        """Extract mentions from content"""
        if not content:
            return []
        
        mentions = re.findall(r'@(\w+)', content)
        return list(set(mentions))
    
    def analyze_content_quality(self, content: str) -> Dict[str, Any]:
        """Analyze content quality indicators"""
        if not content:
            return {
                'length': 0,
                'has_hashtags': False,
                'has_mentions': False,
                'has_urls': False,
                'quality_score': 0.0
            }
        
        # Basic quality indicators
        length = len(content)
        has_hashtags = bool(re.search(r'#\w+', content))
        has_mentions = bool(re.search(r'@\w+', content))
        has_urls = bool(re.search(r'http[s]?://', content))
        
        # Calculate quality score
        quality_score = 0.0
        
        # Length factor
        if length > 100:
            quality_score += 0.3
        elif length > 50:
            quality_score += 0.2
        else:
            quality_score += 0.1
        
        # Engagement factors
        if has_hashtags:
            quality_score += 0.2
        if has_mentions:
            quality_score += 0.1
        if has_urls:
            quality_score += 0.2
        
        # Content depth factor
        if length > 200:
            quality_score += 0.2
        elif length > 100:
            quality_score += 0.1
        
        return {
            'length': length,
            'has_hashtags': has_hashtags,
            'has_mentions': has_mentions,
            'has_urls': has_urls,
            'quality_score': min(1.0, quality_score)
        }
    
    def calculate_engagement_score(self, engagement: Dict) -> float:
        """Calculate overall engagement score"""
        if not engagement:
            return 0.0
        
        likes = engagement.get('likes', 0)
        retweets = engagement.get('retweets', 0)
        replies = engagement.get('replies', 0)
        
        # Weighted engagement score
        total_engagement = likes + (retweets * 2) + (replies * 3)
        
        # Normalize score (0-1)
        if total_engagement > 1000:
            return 1.0
        elif total_engagement > 100:
            return 0.8
        elif total_engagement > 50:
            return 0.6
        elif total_engagement > 10:
            return 0.4
        elif total_engagement > 0:
            return 0.2
        else:
            return 0.0
    
    def extract_content_insights(self, content: str) -> Dict[str, Any]:
        """Extract insights from tweet content"""
        if not content:
            return {
                'word_count': 0,
                'sentence_count': 0,
                'readability_score': 0.0,
                'sentiment_indicators': [],
                'topics': []
            }
        
        # Basic text analysis
        words = content.split()
        sentences = re.split(r'[.!?]+', content)
        
        word_count = len(words)
        sentence_count = len([s for s in sentences if s.strip()])
        
        # Simple readability score
        if sentence_count > 0:
            avg_words_per_sentence = word_count / sentence_count
            if avg_words_per_sentence < 10:
                readability_score = 0.8
            elif avg_words_per_sentence < 20:
                readability_score = 0.6
            else:
                readability_score = 0.4
        else:
            readability_score = 0.5
        
        # Sentiment indicators
        positive_words = ['great', 'awesome', 'excellent', 'amazing', 'love', 'best', 'good']
        negative_words = ['bad', 'terrible', 'awful', 'hate', 'worst', 'horrible']
        
        sentiment_indicators = []
        content_lower = content.lower()
        
        for word in positive_words:
            if word in content_lower:
                sentiment_indicators.append('positive')
                break
        
        for word in negative_words:
            if word in content_lower:
                sentiment_indicators.append('negative')
                break
        
        if not sentiment_indicators:
            sentiment_indicators.append('neutral')
        
        # Topic extraction (simple keyword-based)
        topics = []
        tech_keywords = ['python', 'javascript', 'ai', 'machine learning', 'coding', 'programming']
        business_keywords = ['startup', 'business', 'entrepreneur', 'marketing', 'sales']
        design_keywords = ['design', 'ui', 'ux', 'graphic', 'visual']
        
        for keyword in tech_keywords:
            if keyword in content_lower:
                topics.append('technology')
                break
        
        for keyword in business_keywords:
            if keyword in content_lower:
                topics.append('business')
                break
        
        for keyword in design_keywords:
            if keyword in content_lower:
                topics.append('design')
                break
        
        if not topics:
            topics.append('general')
        
        return {
            'word_count': word_count,
            'sentence_count': sentence_count,
            'readability_score': readability_score,
            'sentiment_indicators': sentiment_indicators,
            'topics': topics
        }
