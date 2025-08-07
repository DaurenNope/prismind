#!/usr/bin/env python3
"""
Test suite for SupabaseManager with comprehensive error handling
"""

import os
import sys
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from supabase_manager import SupabaseManager

# Load environment variables
load_dotenv()

class TestSupabaseManager:
    """Test suite for SupabaseManager class"""
    
    @pytest.fixture
    def manager(self):
        """Create a mocked SupabaseManager instance for testing"""
        with patch('supabase_manager.load_dotenv'), \
             patch('supabase_manager.os.getenv') as mock_getenv, \
             patch('supabase_manager.create_client'):
            
            mock_getenv.side_effect = lambda x: {
                'SUPABASE_URL': 'https://test.supabase.co',
                'SUPABASE_SERVICE_ROLE_KEY': 'test-key'
            }.get(x)
            
            manager = SupabaseManager()
            # Mock the client
            manager.client = Mock()
            return manager
    
    @pytest.fixture
    def sample_post(self):
        """Sample post data for testing"""
        return {
            'id': 999999,
            'title': 'Test Post',
            'content': 'This is a test post for unit testing',
            'platform': 'test',
            'author': 'Test Author',
            'author_handle': '@testauthor',
            'url': 'https://example.com/test',
            'summary': 'Test summary',
            'value_score': 5,
            'smart_tags': '["test", "unit"]',
            'ai_summary': 'This is a test AI summary.',
            'folder_category': 'test',
            'category': 'test'
        }
    
    def test_init_success(self):
        """Test successful initialization with valid credentials"""
        with patch('supabase_manager.load_dotenv'), \
             patch('supabase_manager.os.getenv') as mock_getenv, \
             patch('supabase_manager.create_client') as mock_client:
            
            mock_getenv.side_effect = lambda x: {
                'SUPABASE_URL': 'https://test.supabase.co',
                'SUPABASE_SERVICE_ROLE_KEY': 'test-key'
            }.get(x)
            
            manager = SupabaseManager()
            assert manager.supabase_url == 'https://test.supabase.co'
            assert manager.supabase_key == 'test-key'
            mock_client.assert_called_once_with('https://test.supabase.co', 'test-key')
    
    def test_init_missing_credentials(self):
        """Test initialization failure with missing credentials"""
        with patch('supabase_manager.load_dotenv'), \
             patch('supabase_manager.os.getenv') as mock_getenv:
            
            mock_getenv.side_effect = lambda x: None
            
            with pytest.raises(ValueError, match="Missing Supabase credentials in .env file"):
                SupabaseManager()
    
    def test_insert_post_success(self, manager, sample_post):
        """Test successful post insertion"""
        # Setup mock
        mock_table = Mock()
        mock_insert = Mock()
        mock_execute = Mock()
        mock_result = Mock()
        mock_result.data = [sample_post]
        
        manager.client.table.return_value = mock_table
        mock_table.insert.return_value = mock_insert
        mock_insert.execute.return_value = mock_result
        
        # Call method
        result = manager.insert_post(sample_post)
        
        # Assertions
        assert result == sample_post
        manager.client.table.assert_called_once_with('posts')
        mock_table.insert.assert_called_once_with(sample_post)
        mock_insert.execute.assert_called_once()
    
    def test_insert_post_empty_result(self, manager, sample_post):
        """Test post insertion with empty result"""
        # Setup mock
        mock_table = Mock()
        mock_insert = Mock()
        mock_execute = Mock()
        mock_result = Mock()
        mock_result.data = []
        
        manager.client.table.return_value = mock_table
        mock_table.insert.return_value = mock_insert
        mock_insert.execute.return_value = mock_result
        
        # Call method
        result = manager.insert_post(sample_post)
        
        # Assertions
        assert result == {}
        manager.client.table.assert_called_once_with('posts')
        mock_table.insert.assert_called_once_with(sample_post)
        mock_insert.execute.assert_called_once()
    
    def test_insert_post_exception(self, manager, sample_post):
        """Test post insertion with exception"""
        # Setup mock
        mock_table = Mock()
        mock_insert = Mock()
        
        manager.client.table.return_value = mock_table
        mock_table.insert.return_value = mock_insert
        mock_insert.execute.side_effect = Exception("Database error")
        
        # Call method
        result = manager.insert_post(sample_post)
        
        # Assertions
        assert result == {}
        manager.client.table.assert_called_once_with('posts')
        mock_table.insert.assert_called_once_with(sample_post)
        mock_insert.execute.assert_called_once()
    
    def test_get_posts_success(self, manager):
        """Test successful posts retrieval"""
        sample_posts = [
            {'id': 1, 'title': 'Post 1', 'platform': 'twitter'},
            {'id': 2, 'title': 'Post 2', 'platform': 'reddit'}
        ]
        
        with patch.object(manager.client.table('posts'), 'select') as mock_select:
            mock_query = Mock()
            mock_select.return_value = mock_query
            mock_query.limit.return_value.execute.return_value.data = sample_posts
            
            result = manager.get_posts(limit=10)
            assert result == sample_posts
            mock_select.assert_called_once_with('*')
            mock_query.limit.assert_called_once_with(10)
    
    def test_get_posts_with_platform_filter(self, manager):
        """Test posts retrieval with platform filter"""
        sample_posts = [
            {'id': 1, 'title': 'Post 1', 'platform': 'twitter'},
            {'id': 2, 'title': 'Post 2', 'platform': 'twitter'}
        ]
        
        with patch.object(manager.client.table('posts'), 'select') as mock_select:
            mock_query = Mock()
            mock_filtered_query = Mock()
            mock_select.return_value = mock_query
            mock_query.eq.return_value = mock_filtered_query
            mock_filtered_query.limit.return_value.execute.return_value.data = sample_posts
            
            result = manager.get_posts(limit=10, platform='twitter')
            assert result == sample_posts
            mock_select.assert_called_once_with('*')
            mock_query.eq.assert_called_once_with('platform', 'twitter')
            mock_filtered_query.limit.assert_called_once_with(10)
    
    def test_get_posts_exception(self, manager):
        """Test posts retrieval with exception"""
        with patch.object(manager.client.table('posts'), 'select') as mock_select:
            mock_select.side_effect = Exception("Database error")
            
            result = manager.get_posts(limit=10)
            assert result == []
    
    def test_update_post_success(self, manager):
        """Test successful post update"""
        update_data = {'title': 'Updated Title', 'value_score': 8}
        updated_post = {'id': 1, 'title': 'Updated Title', 'value_score': 8}
        
        with patch.object(manager.client.table('posts'), 'update') as mock_update:
            mock_result = Mock()
            mock_result.data = [updated_post]
            mock_update.return_value.eq.return_value.execute.return_value = mock_result
            
            result = manager.update_post(1, update_data)
            assert result == updated_post
            mock_update.assert_called_once_with(update_data)
    
    def test_update_post_empty_result(self, manager):
        """Test post update with empty result"""
        update_data = {'title': 'Updated Title'}
        
        with patch.object(manager.client.table('posts'), 'update') as mock_update:
            mock_result = Mock()
            mock_result.data = []
            mock_update.return_value.eq.return_value.execute.return_value = mock_result
            
            result = manager.update_post(1, update_data)
            assert result == {}
    
    def test_update_post_exception(self, manager):
        """Test post update with exception"""
        update_data = {'title': 'Updated Title'}
        
        with patch.object(manager.client.table('posts'), 'update') as mock_update:
            mock_update.return_value.eq.return_value.execute.side_effect = Exception("Database error")
            
            result = manager.update_post(1, update_data)
            assert result == {}
    
    def test_delete_post_success(self, manager):
        """Test successful post deletion"""
        with patch.object(manager.client.table('posts'), 'delete') as mock_delete:
            mock_result = Mock()
            mock_result.data = [{'id': 1}]
            mock_delete.return_value.eq.return_value.execute.return_value = mock_result
            
            result = manager.delete_post(1)
            assert result is True
    
    def test_delete_post_no_data(self, manager):
        """Test post deletion with no affected rows"""
        with patch.object(manager.client.table('posts'), 'delete') as mock_delete:
            mock_result = Mock()
            mock_result.data = []
            mock_delete.return_value.eq.return_value.execute.return_value = mock_result
            
            result = manager.delete_post(1)
            assert result is False
    
    def test_delete_post_exception(self, manager):
        """Test post deletion with exception"""
        with patch.object(manager.client.table('posts'), 'delete') as mock_delete:
            mock_delete.return_value.eq.return_value.execute.side_effect = Exception("Database error")
            
            result = manager.delete_post(1)
            assert result is False
    
    def test_search_posts_success(self, manager):
        """Test successful post search"""
        sample_posts = [
            {'id': 1, 'title': 'Python Tutorial', 'content': 'Learn Python programming'},
            {'id': 2, 'title': 'Advanced Python', 'content': 'Advanced Python techniques'}
        ]
        
        with patch.object(manager.client.table('posts'), 'select') as mock_select:
            mock_query = Mock()
            mock_filtered_query = Mock()
            mock_select.return_value = mock_query
            mock_query.or_.return_value = mock_filtered_query
            mock_filtered_query.limit.return_value.execute.return_value.data = sample_posts
            
            result = manager.search_posts('Python', limit=5)
            assert result == sample_posts
            mock_select.assert_called_once_with('*')
            mock_query.or_.assert_called_once()
    
    def test_search_posts_exception(self, manager):
        """Test post search with exception"""
        with patch.object(manager.client.table('posts'), 'select') as mock_select:
            mock_select.side_effect = Exception("Database error")
            
            result = manager.search_posts('Python')
            assert result == []
    
    def test_get_posts_by_category_success(self, manager):
        """Test successful posts retrieval by category"""
        sample_posts = [
            {'id': 1, 'title': 'Tech Post 1', 'category': 'technology'},
            {'id': 2, 'title': 'Tech Post 2', 'category': 'technology'}
        ]
        
        with patch.object(manager.client.table('posts'), 'select') as mock_select:
            mock_query = Mock()
            mock_filtered_query = Mock()
            mock_select.return_value = mock_query
            mock_query.eq.return_value = mock_filtered_query
            mock_filtered_query.limit.return_value.execute.return_value.data = sample_posts
            
            result = manager.get_posts_by_category('technology', limit=5)
            assert result == sample_posts
            mock_select.assert_called_once_with('*')
            mock_query.eq.assert_called_once_with('category', 'technology')
    
    def test_get_posts_by_category_exception(self, manager):
        """Test posts retrieval by category with exception"""
        with patch.object(manager.client.table('posts'), 'select') as mock_select:
            mock_select.side_effect = Exception("Database error")
            
            result = manager.get_posts_by_category('technology')
            assert result == []
    
    def test_get_top_posts_success(self, manager):
        """Test successful retrieval of top posts"""
        sample_posts = [
            {'id': 1, 'title': 'Top Post 1', 'value_score': 10},
            {'id': 2, 'title': 'Top Post 2', 'value_score': 9}
        ]
        
        with patch.object(manager.client.table('posts'), 'select') as mock_select:
            mock_query = Mock()
            mock_ordered_query = Mock()
            mock_select.return_value = mock_query
            mock_query.order.return_value = mock_ordered_query
            mock_ordered_query.limit.return_value.execute.return_value.data = sample_posts
            
            result = manager.get_top_posts(limit=5)
            assert result == sample_posts
            mock_select.assert_called_once_with('*')
            mock_query.order.assert_called_once_with('value_score', desc=True)
    
    def test_get_top_posts_exception(self, manager):
        """Test retrieval of top posts with exception"""
        with patch.object(manager.client.table('posts'), 'select') as mock_select:
            mock_select.side_effect = Exception("Database error")
            
            result = manager.get_top_posts()
            assert result == []

if __name__ == "__main__":
    pytest.main([__file__, "-v"])