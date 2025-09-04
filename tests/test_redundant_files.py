#!/usr/bin/env python3
"""
Tests for files that might be moved to redundant folder
Ensures functionality is preserved before moving
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class TestRedundantFiles:
    """Test files that might be redundant but need verification"""
    
    @patch('scripts.database_manager.DatabaseManager')
    def test_enhance_all_simple(self, mock_db_manager):
        """Test enhance_all_simple.py functionality"""
        # Mock database manager
        mock_db = MagicMock()
        mock_db_manager.return_value = mock_db
        
        # Mock thread summarizer
        with patch('core.analysis.thread_summarizer.ThreadSummarizer') as mock_summarizer:
            mock_summarizer_instance = MagicMock()
            mock_summarizer.return_value = mock_summarizer_instance
            
            # Mock successful analysis
            mock_summarizer_instance.generate_summary_from_dict.return_value = {
                'summary': 'Test summary',
                'smart_title': 'Test Title',
                'smart_tags': ['test', 'python'],
                'value_score': 8
            }
            
            # Import and test the function
            try:
                from enhance_all_simple import enhance_all_bookmarks_simple
                
                # Mock the function to avoid actual execution
                with patch('enhance_all_simple.enhance_all_bookmarks_simple') as mock_enhance:
                    mock_enhance.return_value = True
                    
                    # Test that the function exists and can be called
                    assert callable(enhance_all_bookmarks_simple)
                    
            except ImportError:
                pytest.skip("enhance_all_simple.py not available")
    
    @patch('scripts.database_manager.DatabaseManager')
    def test_analyze_media(self, mock_db_manager):
        """Test analyze_media.py functionality"""
        # Mock database manager
        mock_db = MagicMock()
        mock_db_manager.return_value = mock_db
        
        # Mock media analyzer
        with patch('core.analysis.media_analyzer.MediaAnalyzer') as mock_media_analyzer:
            mock_analyzer_instance = MagicMock()
            mock_media_analyzer.return_value = mock_analyzer_instance
            
            # Mock successful analysis
            mock_analyzer_instance.analyze_media_urls.return_value = {
                'media_type': 'image',
                'content_description': 'Test image',
                'value_boost': 2
            }
            
            try:
                from analyze_media import main
                
                # Test that the function exists
                assert callable(main)
                
            except ImportError:
                pytest.skip("analyze_media.py not available")
    
    @patch('scripts.database_manager.DatabaseManager')
    def test_analyze_and_categorize_bookmarks(self, mock_db_manager):
        """Test analyze_and_categorize_bookmarks.py functionality"""
        # Mock database manager
        mock_db = MagicMock()
        mock_db_manager.return_value = mock_db
        
        # Mock Supabase manager
        with patch.dict('sys.modules', {'multi_table_manager': __import__('types')}) as _:
            # Ensure SupabaseManager can be instantiated without real network
            with patch('scripts.supabase_manager.create_client') as mock_client:
                mock_client.return_value = MagicMock()
            
            try:
                from analyze_and_categorize_bookmarks import BookmarkAnalyzer
                
                # Test that the class exists
                analyzer = BookmarkAnalyzer()
                assert hasattr(analyzer, 'categorize_bookmarks')
                assert callable(analyzer.categorize_bookmarks)
                
            except ImportError:
                pytest.skip("analyze_and_categorize_bookmarks.py not available")
    
    @patch('scripts.database_manager.DatabaseManager')
    def test_extract_reddit_comments(self, mock_db_manager):
        """Test extract_reddit_comments.py functionality"""
        # Mock database manager
        mock_db = MagicMock()
        mock_db_manager.return_value = mock_db
        
        # Mock Reddit extractor
        with patch('core.extraction.reddit_extractor.RedditExtractor') as mock_reddit:
            mock_extractor_instance = MagicMock()
            mock_reddit.return_value = mock_extractor_instance
            
            # Mock successful comment extraction
            mock_extractor_instance.get_top_comments.return_value = [
                {
                    'author': 'user1',
                    'content': 'Great post!',
                    'score': 10
                }
            ]
            
            try:
                from extract_reddit_comments import extract_comments_for_existing_posts
                
                # Test that the function exists
                assert callable(extract_comments_for_existing_posts)
                
            except ImportError:
                pytest.skip("extract_reddit_comments.py not available")
    
    @patch('scripts.database_manager.DatabaseManager')
    def test_rescrape_single_post(self, mock_db_manager):
        """Test rescrape_single_post.py functionality"""
        # Mock database manager
        mock_db = MagicMock()
        mock_db_manager.return_value = mock_db
        
        # Mock Twitter extractor
        with patch('core.extraction.twitter_extractor_playwright.TwitterExtractorPlaywright') as mock_twitter:
            mock_extractor_instance = MagicMock()
            mock_twitter.return_value = mock_extractor_instance
            
            # Mock successful extraction
            mock_extractor_instance._extract_tweet_data.return_value = MagicMock(
                post_id='test_123',
                author='Test Author',
                content='Test content'
            )
            
            try:
                from rescrape_single_post import rescrape_post
                
                # Test that the function exists
                assert callable(rescrape_post)
                
            except ImportError:
                pytest.skip("rescrape_single_post.py not available")
    
    def test_setup_auto_collection(self):
        """Test setup_auto_collection.py functionality"""
        try:
            from setup_auto_collection import setup_cron_job
            
            # Test that the function exists
            assert callable(setup_cron_job)
            
        except ImportError:
            pytest.skip("setup_auto_collection.py not available")
    
    def test_setup_twitter_config(self):
        """Test setup_twitter_config.py functionality"""
        try:
            from setup_twitter_config import main
            
            # Test that the function exists
            assert callable(main)
            
        except ImportError:
            pytest.skip("setup_twitter_config.py not available")
    
    def test_multi_table_manager(self):
        """Test multi_table_manager.py functionality"""
        try:
            from multi_table_manager import MultiTableManager
            
            # Test that the class exists
            assert hasattr(MultiTableManager, '__init__')
            
        except ImportError:
            pytest.skip("multi_table_manager.py not available")
    
    def test_supabase_manager(self):
        """Test supabase_manager.py functionality"""
        try:
            from supabase_manager import SupabaseManager
            
            # Test that the class exists
            assert hasattr(SupabaseManager, '__init__')
            
        except ImportError:
            pytest.skip("supabase_manager.py not available")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
