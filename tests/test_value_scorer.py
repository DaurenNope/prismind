#!/usr/bin/env python3
"""
Test suite for ValueScorer
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.analysis.value_scorer import ValueScorer


class TestValueScorer:
    """Test suite for ValueScorer class"""
    
    @pytest.fixture
    def scorer(self):
        """Create a ValueScorer instance"""
        return ValueScorer()
    
    @pytest.fixture
    def sample_post(self):
        """Sample post data for testing"""
        return {
            'content': 'This is a high quality educational post about artificial intelligence and machine learning concepts that provides valuable insights.',
            'author': 'Expert User',
            'engagement': {'likes': 50, 'shares': 10, 'comments': 5},
            'created_at': datetime.now().isoformat(),
            'hashtags': ['#AI', '#MachineLearning', '#Education'],
            'platform': 'twitter',
            'url': 'https://twitter.com/expert/status/123'
        }
    
    def test_init(self, scorer):
        """Test ValueScorer initialization"""
        assert scorer is not None
        assert hasattr(scorer, 'quality_indicators')
        assert hasattr(scorer, 'learning_keywords')
        assert hasattr(scorer, 'spam_indicators')
    
    def test_calculate_value_score(self, scorer, sample_post):
        """Test value score calculation"""
        score = scorer.calculate_value_score(sample_post)
        
        # Score should be between 1 and 10
        assert isinstance(score, float)
        assert 1.0 <= score <= 10.0
    
    def test_calculate_value_score_with_empty_content(self, scorer):
        """Test value score calculation with empty content"""
        post_data = {
            'content': '',
            'author': 'User',
            'engagement': {'likes': 0, 'shares': 0, 'comments': 0},
            'created_at': datetime.now().isoformat(),
            'hashtags': [],
            'platform': 'twitter'
        }
        
        score = scorer.calculate_value_score(post_data)
        
        # Should still return a valid score
        assert isinstance(score, float)
        assert 1.0 <= score <= 10.0
    
    def test_analyze_content_quality(self, scorer, sample_post):
        """Test content quality analysis"""
        quality_score = scorer._analyze_content_quality(sample_post)
        
        # Quality score should be between 0 and 10
        assert isinstance(quality_score, (int, float))
        assert 0 <= quality_score <= 10
    
    def test_analyze_engagement_quality(self, scorer, sample_post):
        """Test engagement quality analysis"""
        engagement_score = scorer._analyze_engagement_quality(sample_post)
        
        # Engagement score should be between 0 and 10
        assert isinstance(engagement_score, (int, float))
        assert 0 <= engagement_score <= 10
    
    def test_analyze_learning_potential(self, scorer, sample_post):
        """Test learning potential analysis"""
        learning_score = scorer._analyze_learning_potential(sample_post)
        
        # Learning score should be between 0 and 10
        assert isinstance(learning_score, (int, float))
        assert 0 <= learning_score <= 10
    
    def test_analyze_recency_relevance(self, scorer, sample_post):
        """Test recency and relevance analysis"""
        recency_score = scorer._analyze_recency_relevance(sample_post)
        
        # Recency score should be between 0 and 10
        assert isinstance(recency_score, (int, float))
        assert 0 <= recency_score <= 10
    
    def test_analyze_platform_factors(self, scorer, sample_post):
        """Test platform-specific factors analysis"""
        platform_score = scorer._analyze_platform_factors(sample_post)
        
        # Platform score should be between -2 and 2
        assert isinstance(platform_score, (int, float))
        assert -2 <= platform_score <= 2
    
    def test_calculate_penalties(self, scorer, sample_post):
        """Test penalty calculation"""
        penalty = scorer._calculate_penalties(sample_post)
        
        # Penalty should be non-negative
        assert isinstance(penalty, (int, float))
        assert penalty >= 0
    
    def test_high_quality_content(self, scorer):
        """Test scoring of high quality content"""
        high_quality_post = {
            'content': 'Comprehensive tutorial on machine learning algorithms with practical examples and code samples. Detailed explanation of neural networks and deep learning concepts.',
            'author': 'Expert User',
            'engagement': {'likes': 500, 'shares': 100, 'comments': 50},
            'created_at': datetime.now().isoformat(),
            'hashtags': ['#MachineLearning', '#AI', '#Tutorial', '#DeepLearning'],
            'platform': 'twitter'
        }
        
        score = scorer.calculate_value_score(high_quality_post)
        
        # High quality content should get a high score
        assert score >= 7.0
    
    def test_low_quality_content(self, scorer):
        """Test scoring of low quality content"""
        low_quality_post = {
            'content': 'Check this out!!! lolol',
            'author': 'User',
            'engagement': {'likes': 1, 'shares': 0, 'comments': 0},
            'created_at': (datetime.now() - timedelta(days=365)).isoformat(),
            'hashtags': ['#spam', '#checkitout'],
            'platform': 'twitter'
        }
        
        score = scorer.calculate_value_score(low_quality_post)
        
        # Low quality content should get a low score
        assert score <= 5.0

if __name__ == "__main__":
    pytest.main([__file__, "-v"])