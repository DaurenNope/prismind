#!/usr/bin/env python3
"""
Test suite for SocialContentAnalyzer
"""

import os
import sys
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.analysis.social_content_analyzer import SocialContentAnalyzer
from core.extraction.social_extractor_base import SocialPost

class TestSocialContentAnalyzer:
    """Test suite for SocialContentAnalyzer class"""
    
    @pytest.fixture
    def analyzer(self):
        """Create a SocialContentAnalyzer instance"""
        return SocialContentAnalyzer()
    
    @pytest.fixture
    def sample_post(self):
        """Sample social post for testing"""
        return SocialPost(
            id="test_123",
            platform="twitter",
            author="Test User",
            author_handle="@testuser",
            content="This is a great post about AI and machine learning. Check out this link https://example.com",
            created_at="2023-01-01T12:00:00Z",
            url="https://twitter.com/testuser/status/123",
            hashtags=["AI", "MachineLearning"],
            post_type="text",
            engagement={"likes": 10, "retweets": 5, "comments": 2}
        )
    
    def test_init_without_api_key(self, monkeypatch):
        """Test initialization without API key"""
        # Remove GEMINI_API_KEY from environment
        monkeypatch.delenv('GEMINI_API_KEY', raising=False)
        
        analyzer = SocialContentAnalyzer()
        assert analyzer is not None
        # Should not crash even without API key
    
    def test_init_with_api_key(self):
        """Test initialization with API key"""
        with patch('core.analysis.social_content_analyzer.genai.configure') as mock_configure:
            analyzer = SocialContentAnalyzer(api_key="test-key")
            mock_configure.assert_called_once_with(api_key="test-key")
    
    def test_get_sentiment(self, analyzer):
        """Test sentiment analysis"""
        text = "This is a great post!"
        sentiment = analyzer._get_sentiment(text)
        
        # Check that we get the expected sentiment keys
        assert 'neg' in sentiment
        assert 'neu' in sentiment
        assert 'pos' in sentiment
        assert 'compound' in sentiment
        assert isinstance(sentiment['compound'], float)
    
    def test_analyze_social_post(self, analyzer, sample_post):
        """Test social post analysis"""
        with patch.object(analyzer, 'model') as mock_model:
            # Mock the Gemini response
            mock_response = Mock()
            mock_response.text = '''{
                "category": "Technology",
                "subcategory": "AI",
                "content_type": "Discussion",
                "key_points": ["AI is great", "Machine learning is useful"],
                "value_score": 8,
                "engagement_prediction": "High",
                "recommended_action": "Read and save for reference",
                "tags": ["AI", "MachineLearning", "Technology"],
                "summary": "This is a post about AI and machine learning."
            }'''
            mock_model.generate_content.return_value = mock_response
            
            result = analyzer.analyze_social_post(sample_post)
            
            # Check that we get the expected result structure
            assert isinstance(result, dict)
            assert 'category' in result
            assert 'subcategory' in result
            assert 'content_type' in result
            assert 'key_points' in result
            assert 'value_score' in result
            assert 'engagement_prediction' in result
            assert 'recommended_action' in result
            assert 'tags' in result
            assert 'summary' in result
            assert 'sentiment' in result
    
    def test_analyze_social_post_with_gemini_error(self, analyzer, sample_post):
        """Test social post analysis when Gemini fails"""
        with patch.object(analyzer, 'model') as mock_model:
            # Simulate a Gemini API error
            mock_model.generate_content.side_effect = Exception("API Error")
            
            result = analyzer.analyze_social_post(sample_post)
            
            # Should still return a result with fallback values
            assert isinstance(result, dict)
            assert 'category' in result
            assert 'sentiment' in result

if __name__ == "__main__":
    pytest.main([__file__, "-v"])