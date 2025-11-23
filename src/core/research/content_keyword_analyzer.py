#!/usr/bin/env python3
"""
Content Keyword Analyzer
Handles keyword extraction and sentiment analysis
"""

import re
from collections import Counter
from typing import Any, Dict, List

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


class ContentKeywordAnalyzer:
    """Handles keyword extraction and sentiment analysis"""
    
    def __init__(self):
        self.sentiment_analyzer = SentimentIntensityAnalyzer()
        self.stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
            'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did',
            'will', 'would', 'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these',
            'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them'
        }
    
    def extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """Extract keywords from text"""
        if not text or not text.strip():
            return []
        
        # Clean and tokenize text
        cleaned_text = self._clean_text(text)
        words = self._tokenize(cleaned_text)
        
        # Filter out stop words and short words
        filtered_words = [
            word for word in words 
            if len(word) > 2 and word.lower() not in self.stop_words
        ]
        
        # Count word frequencies
        word_counts = Counter(filtered_words)
        
        # Return top keywords
        return [word for word, count in word_counts.most_common(max_keywords)]
    
    def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment of text"""
        if not text or not text.strip():
            return {
                'compound': 0.0,
                'positive': 0.0,
                'negative': 0.0,
                'neutral': 1.0,
                'label': 'neutral'
            }
        
        # Get sentiment scores
        scores = self.sentiment_analyzer.polarity_scores(text)
        
        # Determine label
        compound = scores['compound']
        if compound >= 0.05:
            label = 'positive'
        elif compound <= -0.05:
            label = 'negative'
        else:
            label = 'neutral'
        
        return {
            'compound': compound,
            'positive': scores['pos'],
            'negative': scores['neg'],
            'neutral': scores['neu'],
            'label': label
        }
    
    def _clean_text(self, text: str) -> str:
        """Clean text for processing"""
        # Remove URLs
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        
        # Remove mentions and hashtags (keep content)
        text = re.sub(r'@\w+', '', text)
        text = re.sub(r'#\w+', '', text)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into words"""
        # Simple tokenization - split on whitespace and punctuation
        words = re.findall(r'\b\w+\b', text.lower())
        return words
