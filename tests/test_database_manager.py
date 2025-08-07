#!/usr/bin/env python3
"""
Test suite for DatabaseManager
"""

import os
import sys
import pytest
import sqlite3
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pandas as pd

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.database_manager import DatabaseManager

class TestDatabaseManager:
    """Test suite for DatabaseManager class"""
    
    @pytest.fixture
    def db_manager(self, tmp_path):
        """Create a DatabaseManager instance with a temporary database"""
        db_path = tmp_path / "test.db"
        manager = DatabaseManager(str(db_path))
        return manager
    
    @pytest.fixture
    def sample_post(self):
        """Sample post data for testing"""
        return {
            'post_id': 'test_post_1',
            'platform': 'test',
            'author': 'Test Author',
            'content': 'This is a test post for unit testing',
            'created_at': '2023-01-01 12:00:00',
            'url': 'https://example.com/test',
            'value_score': 5.0,
            'engagement_score': 3.0,
            'sentiment': 'positive',
            'folder_category': 'test',
            'ai_summary': 'This is a test AI summary.',
            'key_concepts': 'test,unit',
            'is_deleted': 0
        }
    
    def test_init(self, tmp_path):
        """Test DatabaseManager initialization"""
        db_path = tmp_path / "test.db"
        manager = DatabaseManager(str(db_path))
        
        # Check that the database file was created
        assert db_path.exists()
        
        # Check that tables were created
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='posts'")
            assert cursor.fetchone() is not None
    
    def test_insert_post(self, db_manager, sample_post):
        """Test inserting a post"""
        post_id = db_manager.insert_post(sample_post)
        assert post_id is not None
        assert isinstance(post_id, int)
    
    def test_get_posts(self, db_manager, sample_post):
        """Test getting posts"""
        # Insert a post first
        db_manager.insert_post(sample_post)
        
        # Get posts
        posts = db_manager.get_posts()
        assert isinstance(posts, list)
        assert len(posts) == 1
        assert posts[0]['post_id'] == sample_post['post_id']
    
    def test_get_posts_with_limit(self, db_manager, sample_post):
        """Test getting posts with limit"""
        # Insert two posts
        sample_post2 = sample_post.copy()
        sample_post2['post_id'] = 'test_post_2'
        db_manager.insert_post(sample_post)
        db_manager.insert_post(sample_post2)
        
        # Get posts with limit
        posts = db_manager.get_posts(limit=1)
        assert isinstance(posts, list)
        assert len(posts) == 1
    
    def test_get_post_by_id(self, db_manager, sample_post):
        """Test getting a post by ID"""
        # Insert a post first
        post_id = db_manager.insert_post(sample_post)
        
        # Get post by ID
        post = db_manager.get_post_by_id(post_id)
        assert post is not None
        assert post['post_id'] == sample_post['post_id']
    
    def test_update_post(self, db_manager, sample_post):
        """Test updating a post"""
        # Insert a post first
        post_id = db_manager.insert_post(sample_post)
        
        # Update the post
        updates = {'value_score': 8.0, 'folder_category': 'updated'}
        db_manager.update_post(post_id, updates)
        
        # Check that the post was updated
        updated_post = db_manager.get_post_by_id(post_id)
        assert updated_post['value_score'] == 8.0
        assert updated_post['folder_category'] == 'updated'
    
    def test_delete_post(self, db_manager, sample_post):
        """Test deleting a post"""
        # Insert a post first
        post_id = db_manager.insert_post(sample_post)
        
        # Delete the post
        db_manager.delete_post(post_id)
        
        # Check that the post was marked as deleted
        post = db_manager.get_post_by_id(post_id)
        assert post['is_deleted'] == 1
    
    def test_search_posts(self, db_manager, sample_post):
        """Test searching posts"""
        # Insert a post first
        db_manager.insert_post(sample_post)
        
        # Search for posts
        results = db_manager.search_posts('test')
        assert isinstance(results, list)
        assert len(results) == 1
        assert results[0]['post_id'] == sample_post['post_id']
    
    def test_get_posts_by_category(self, db_manager, sample_post):
        """Test getting posts by category"""
        # Insert a post first
        db_manager.insert_post(sample_post)
        
        # Get posts by category
        results = db_manager.get_posts_by_category('test')
        assert isinstance(results, list)
        assert len(results) == 1
        assert results[0]['folder_category'] == 'test'
    
    def test_get_top_posts(self, db_manager, sample_post):
        """Test getting top posts"""
        # Insert posts with different scores
        post1 = sample_post.copy()
        post1['post_id'] = 'post_1'
        post1['value_score'] = 5.0
        
        post2 = sample_post.copy()
        post2['post_id'] = 'post_2'
        post2['value_score'] = 8.0
        
        db_manager.insert_post(post1)
        db_manager.insert_post(post2)
        
        # Get top posts
        results = db_manager.get_top_posts(limit=2)
        assert isinstance(results, list)
        assert len(results) == 2
        # Should be ordered by value_score descending
        assert results[0]['value_score'] >= results[1]['value_score']
    
    def test_get_database_stats(self, db_manager, sample_post):
        """Test getting database stats"""
        # Insert a post first
        db_manager.insert_post(sample_post)
        
        # Get stats
        stats = db_manager.get_database_stats()
        assert isinstance(stats, dict)
        assert 'total_posts' in stats
        assert stats['total_posts'] >= 1

if __name__ == "__main__":
    pytest.main([__file__, "-v"])