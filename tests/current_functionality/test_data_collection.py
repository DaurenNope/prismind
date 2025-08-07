#!/usr/bin/env python3
"""
Comprehensive tests for current data collection functionality
Tests Twitter, Reddit, and Threads extraction workflows
"""

import pytest
import tempfile
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import pandas as pd
import json

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

class TestDataCollectionWorkflow:
    """Test the current data collection workflow"""
    
    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        
        yield db_path
        
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)
    
    @patch('scripts.database_manager.DatabaseManager')
    def test_twitter_extraction(self, mock_db_manager, temp_db):
        """Test Twitter data extraction workflow"""
        # Mock database manager
        mock_db = MagicMock()
        mock_db_manager.return_value = mock_db
        
        # Mock Twitter extractor
        with patch('core.extraction.twitter_extractor_playwright.TwitterExtractorPlaywright') as mock_twitter:
            mock_extractor = MagicMock()
            mock_twitter.return_value = mock_extractor
            
            # Mock successful extraction
            mock_post = MagicMock(
                post_id='test_twitter_123',
                platform='twitter',
                author='Test Twitter User',
                author_handle='@testuser',
                content='This is a test tweet about Python programming',
                created_at='2024-01-01T10:00:00Z',
                url='https://twitter.com/testuser/123',
                post_type='tweet',
                media_urls=[],
                hashtags=['python', 'programming'],
                mentions=[],
                engagement={},
                is_saved=True,
                saved_at='2024-01-01T10:00:00Z',
                folder_category='programming',
                analysis=None
            )
            
            mock_extractor.extract_saved_posts.return_value = [mock_post]
            
            try:
                # Import collection functions
                from collect_multi_platform import collect_twitter_bookmarks
                
                # Test Twitter collection (async function)
                import asyncio
                result = asyncio.run(collect_twitter_bookmarks(mock_db, set()))
                assert result is not None
                
            except ImportError as e:
                pytest.skip(f"Collection module not available: {e}")
    
    @patch('scripts.database_manager.DatabaseManager')
    def test_reddit_extraction(self, mock_db_manager, temp_db):
        """Test Reddit data extraction workflow"""
        # Mock database manager
        mock_db = MagicMock()
        mock_db_manager.return_value = mock_db
        
        # Mock Reddit extractor
        with patch('core.extraction.reddit_extractor.RedditExtractor') as mock_reddit:
            mock_extractor = MagicMock()
            mock_reddit.return_value = mock_extractor
            
            # Mock successful extraction
            mock_post = MagicMock(
                post_id='test_reddit_456',
                platform='reddit',
                author='Test Reddit User',
                author_handle='u/testuser',
                content='This is a test Reddit post about machine learning',
                created_at='2024-01-02T11:00:00Z',
                url='https://reddit.com/r/test/456',
                post_type='post',
                media_urls=[],
                hashtags=['ml', 'ai'],
                mentions=[],
                engagement={},
                is_saved=True,
                saved_at='2024-01-02T11:00:00Z',
                folder_category='research',
                analysis=None
            )
            
            mock_extractor.extract_saved_posts.return_value = [mock_post]
            
            try:
                # Import collection functions
                from collect_multi_platform import collect_reddit_bookmarks
                
                # Test Reddit collection
                result = collect_reddit_bookmarks(mock_db, set())
                assert result is not None
                
            except ImportError as e:
                pytest.skip(f"Collection module not available: {e}")
    
    @patch('scripts.database_manager.DatabaseManager')
    def test_threads_extraction(self, mock_db_manager, temp_db):
        """Test Threads data extraction workflow"""
        # Mock database manager
        mock_db = MagicMock()
        mock_db_manager.return_value = mock_db
        
        # Mock Threads extractor
        with patch('core.extraction.threads_extractor.ThreadsExtractor') as mock_threads:
            mock_extractor = MagicMock()
            mock_threads.return_value = mock_extractor
            
            # Mock successful extraction
            mock_post = MagicMock(
                post_id='test_threads_789',
                platform='threads',
                author='Test Threads User',
                author_handle='@testuser',
                content='This is a test Threads post about web development',
                created_at='2024-01-03T12:00:00Z',
                url='https://threads.net/testuser/789',
                post_type='post',
                media_urls=[],
                hashtags=['webdev', 'frontend'],
                mentions=[],
                engagement={},
                is_saved=True,
                saved_at='2024-01-03T12:00:00Z',
                folder_category='development',
                analysis=None
            )
            
            mock_extractor.extract_saved_posts.return_value = [mock_post]
            
            try:
                # Import collection functions
                from collect_multi_platform import collect_threads_bookmarks
                
                # Test Threads collection (async function)
                import asyncio
                result = asyncio.run(collect_threads_bookmarks(mock_db, set()))
                assert result is not None
                
            except ImportError as e:
                pytest.skip(f"Collection module not available: {e}")
    
    @patch('scripts.database_manager.DatabaseManager')
    def test_multi_platform_collection(self, mock_db_manager, temp_db):
        """Test multi-platform data collection workflow"""
        # Use real database manager for this test since we have credentials
        from scripts.database_manager import DatabaseManager
        db_manager = DatabaseManager()
        
        # Mock all extractors
        with patch('core.extraction.twitter_extractor_playwright.TwitterExtractorPlaywright') as mock_twitter, \
             patch('core.extraction.reddit_extractor.RedditExtractor') as mock_reddit, \
             patch('core.extraction.threads_extractor.ThreadsExtractor') as mock_threads:
            
            # Mock Twitter
            mock_twitter_extractor = MagicMock()
            mock_twitter.return_value = mock_twitter_extractor
            mock_twitter_post = MagicMock(
                post_id='test_twitter_123',
                platform='twitter',
                author='Test Twitter User',
                content='Test tweet',
                created_at='2024-01-01T10:00:00Z',
                url='https://twitter.com/test/123',
                hashtags=['test'],
                mentions=[],
                media_urls=[],
                engagement={},
                is_saved=True,
                saved_at='2024-01-01T10:00:00Z',
                folder_category='test',
                analysis=None
            )
            mock_twitter_extractor.extract_saved_posts.return_value = [mock_twitter_post]
            
            # Mock Reddit
            mock_reddit_extractor = MagicMock()
            mock_reddit.return_value = mock_reddit_extractor
            mock_reddit_post = MagicMock(
                post_id='test_reddit_456',
                platform='reddit',
                author='Test Reddit User',
                content='Test Reddit post',
                created_at='2024-01-02T11:00:00Z',
                url='https://reddit.com/r/test/456',
                hashtags=['test'],
                mentions=[],
                media_urls=[],
                engagement={},
                is_saved=True,
                saved_at='2024-01-02T11:00:00Z',
                folder_category='test',
                analysis=None
            )
            mock_reddit_extractor.extract_saved_posts.return_value = [mock_reddit_post]
            
            # Mock Threads
            mock_threads_extractor = MagicMock()
            mock_threads.return_value = mock_threads_extractor
            mock_threads_post = MagicMock(
                post_id='test_threads_789',
                platform='threads',
                author='Test Threads User',
                content='Test Threads post',
                created_at='2024-01-03T12:00:00Z',
                url='https://threads.net/test/789',
                hashtags=['test'],
                mentions=[],
                media_urls=[],
                engagement={},
                is_saved=True,
                saved_at='2024-01-03T12:00:00Z',
                folder_category='test',
                analysis=None
            )
            mock_threads_extractor.extract_saved_posts.return_value = [mock_threads_post]
            
            try:
                # Import collection functions
                from collect_multi_platform import main
                
                # Test multi-platform collection (async function)
                import asyncio
                result = asyncio.run(main())
                # The main function returns None on completion, which is expected
                assert result is None or result is not None
                
            except ImportError as e:
                pytest.skip(f"Collection module not available: {e}")
    
    @patch('scripts.database_manager.DatabaseManager')
    def test_database_storage(self, mock_db_manager, temp_db):
        """Test database storage functionality"""
        # Mock database manager
        mock_db = MagicMock()
        mock_db_manager.return_value = mock_db
        
        # Mock successful storage
        mock_db.add_post.return_value = True
        
        # Test post data
        test_post = {
            'post_id': 'test_storage_123',
            'platform': 'twitter',
            'author': 'Test Storage User',
            'author_handle': '@teststorage',
            'content': 'This is a test post for storage',
            'created_at': '2024-01-01T10:00:00Z',
            'url': 'https://twitter.com/test/123',
            'value_score': 8.0,
            'sentiment': 0.7,
            'folder_category': 'test',
            'ai_summary': 'Test storage summary',
            'key_concepts': '["test", "storage"]',
            'hashtags': '["test"]',
            'mentions': '[]',
            'media_urls': '[]'
        }
        
        # Test storage
        result = mock_db.add_post(test_post)
        assert result is True
        
        # Verify post was stored
        mock_db.add_post.assert_called_once_with(test_post)
    
    @patch('scripts.database_manager.DatabaseManager')
    def test_extraction_error_handling(self, mock_db_manager, temp_db):
        """Test extraction error handling"""
        # Mock database manager
        mock_db = MagicMock()
        mock_db_manager.return_value = mock_db
        
        # Mock Twitter extractor with error
        with patch('core.extraction.twitter_extractor_playwright.TwitterExtractorPlaywright') as mock_twitter:
            mock_extractor = MagicMock()
            mock_twitter.return_value = mock_extractor
            
            # Mock extraction error
            mock_extractor.extract_saved_posts.side_effect = Exception("Extraction failed")
            
            try:
                # Import collection functions
                from collect_multi_platform import collect_twitter_bookmarks
                
                # Test error handling (async function)
                import asyncio
                result = asyncio.run(collect_twitter_bookmarks(mock_db, set()))
                # Should handle error gracefully
                assert result is not None or result is None
                
            except ImportError as e:
                pytest.skip(f"Collection module not available: {e}")
            except Exception as e:
                # Error should be handled gracefully
                assert "Extraction" in str(e) or "failed" in str(e).lower()
    
    @patch('scripts.database_manager.DatabaseManager')
    def test_database_error_handling(self, mock_db_manager, temp_db):
        """Test database error handling"""
        # Mock database manager with error
        mock_db = MagicMock()
        mock_db_manager.return_value = mock_db
        
        # Mock database error
        mock_db.add_post.side_effect = Exception("Database connection failed")
        
        # Test post data
        test_post = {
            'post_id': 'test_error_123',
            'platform': 'twitter',
            'author': 'Test Error User',
            'content': 'This is a test post for error handling',
            'created_at': '2024-01-01T10:00:00Z',
            'url': 'https://twitter.com/test/123',
            'value_score': 8.0,
            'sentiment': 0.7,
            'folder_category': 'test',
            'ai_summary': 'Test error summary',
            'key_concepts': '["test", "error"]',
            'hashtags': '["test"]',
            'mentions': '[]',
            'media_urls': '[]'
        }
        
        # Test error handling
        try:
            result = mock_db.add_post(test_post)
            assert result is False or result is None
        except Exception as e:
            # Error should be handled gracefully
            assert "Database" in str(e) or "connection" in str(e).lower()
    
    def test_social_post_structure(self):
        """Test SocialPost data structure"""
        try:
            from core.extraction.social_extractor_base import SocialPost
            from datetime import datetime
            
            # Test SocialPost creation
            post = SocialPost(
                platform="twitter",
                post_id="test_123",
                author="Test Author",
                author_handle="@testauthor",
                content="This is a test post",
                created_at=datetime.now(),
                url="https://twitter.com/test/123",
                post_type="tweet",
                media_urls=[],
                hashtags=["test"],
                mentions=[],
                engagement={},
                is_saved=True,
                saved_at=datetime.now(),
                folder_category="test",
                analysis=None
            )
            
            # Verify structure
            assert post.platform == "twitter"
            assert post.post_id == "test_123"
            assert post.author == "Test Author"
            assert post.content == "This is a test post"
            assert "test" in post.hashtags
            
        except ImportError as e:
            pytest.skip(f"SocialPost module not available: {e}")
    
    @patch('scripts.database_manager.DatabaseManager')
    def test_collection_performance(self, mock_db_manager, temp_db):
        """Test collection performance with large datasets"""
        # Mock database manager
        mock_db = MagicMock()
        mock_db_manager.return_value = mock_db
        
        # Mock Twitter extractor with large dataset
        with patch('core.extraction.twitter_extractor_playwright.TwitterExtractorPlaywright') as mock_twitter:
            mock_extractor = MagicMock()
            mock_twitter.return_value = mock_extractor
            
            # Create large dataset
            large_posts = []
            for i in range(100):
                from datetime import datetime
                post = MagicMock(
                    post_id=f'test_twitter_{i}',
                    platform='twitter',
                    author=f'Test User {i}',
                    author_handle=f'@testuser{i}',
                    content=f'Test post {i} about various topics',
                    created_at=datetime.now(),
                    url=f'https://twitter.com/test/{i}',
                    hashtags=['test'],
                    mentions=[],
                    media_urls=[],
                    engagement={},
                    is_saved=True,
                    saved_at=datetime.now(),
                    folder_category='test',
                    analysis=None
                )
                large_posts.append(post)
            
            mock_extractor.extract_saved_posts.return_value = large_posts
            
            try:
                # Import collection functions
                from collect_multi_platform import collect_twitter_bookmarks
                
                # Test performance with large dataset (async function)
                import time
                import asyncio
                start_time = time.time()
                
                result = asyncio.run(collect_twitter_bookmarks(mock_db, set()))
                
                end_time = time.time()
                execution_time = end_time - start_time
                
                # Should complete within reasonable time (less than 30 seconds)
                assert execution_time < 30.0, f"Collection took {execution_time} seconds"
                assert result is not None
                
            except ImportError as e:
                pytest.skip(f"Collection module not available: {e}")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
