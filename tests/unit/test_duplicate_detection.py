"""
Test duplicate detection in the collector.
"""
import os
import sys
import unittest
from unittest.mock import MagicMock, patch
import sqlite3
from datetime import datetime, timezone

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, project_root)

# Import from the project root
from src.services.database_manager import SQLiteManager
from src.services.collector_runner import collect_twitter_bookmarks
from src.core.extraction.social_extractor_base import SocialPost
from src.core.extraction.twitter_extractor_playwright import TwitterExtractorPlaywright

class TestDuplicateDetection(unittest.IsolatedAsyncioTestCase):
    """Test duplicate detection functionality."""
    
    def setUp(self):
        """Set up test database and mocks."""
        # Use in-memory database for testing
        self.db_path = ":memory:"
        self.db_manager = SQLiteManager(self.db_path)
        
        # Initialize the database table
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create posts table with all required columns
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            metadata TEXT,
            processed BOOLEAN DEFAULT 0,
            deleted BOOLEAN DEFAULT 0,
            post_id TEXT,
            url TEXT,
            author TEXT,
            author_handle TEXT,
            post_type TEXT
        )
        """)
        conn.commit()
        conn.close()
        
        # Create test data
        self.test_post = {
            'post_id': '12345',
            'platform': 'twitter',
            'content': 'Test tweet content',
            'url': 'https://twitter.com/user/status/12345',
            'author': 'Test User',
            'author_handle': 'testuser',
            'created_at': datetime.now(timezone.utc).isoformat(),
            'metadata': {
                'tweet_id': '12345',
                'tweet_url': 'https://twitter.com/user/status/12345'
            }
        }
        
        # Mock the Twitter extractor
        self.mock_extractor = MagicMock()
        self.mock_extractor.authenticate.return_value = True
        
    async def test_duplicate_by_post_id(self):
        """Test that duplicate posts are skipped based on post_id."""
        # Add test post to database
        self.db_manager.add_post(self.test_post)
        
        # Create a mock post with the same ID
        mock_post = SocialPost(
            platform='twitter',
            author='Test User',
            author_handle='testuser',
            content='Different content but same ID',
            created_at=datetime.now(timezone.utc),
            url='https://twitter.com/user/status/12345',
            post_type='tweet',
            post_id='12345'
        )
        
        # Mock get_saved_posts to return our mock post
        self.mock_extractor.get_saved_posts.return_value = [mock_post]
        
        # Run collection
        with patch('src.services.collector_runner.TwitterExtractorPlaywright', return_value=self.mock_extractor):
            new_posts = await collect_twitter_bookmarks(self.db_manager, set())
            
        # Should skip the duplicate
        self.assertEqual(new_posts, 0)
        
    async def test_duplicate_by_url(self):
        """Test that duplicate posts are skipped based on URL."""
        # Add test post to database
        self.db_manager.add_post(self.test_post)
        
        # Create a mock post with different ID but same URL
        mock_post = SocialPost(
            platform='twitter',
            author='Test User',
            author_handle='testuser',
            content='Same content, different ID',
            created_at=datetime.now(timezone.utc),
            url='https://twitter.com/user/status/12345',  # Same URL
            post_type='tweet',
            post_id='54321'  # Different ID
        )
        
        # Mock get_saved_posts to return our mock post
        self.mock_extractor.get_saved_posts.return_value = [mock_post]
        
        # Run collection
        with patch('src.services.collector_runner.TwitterExtractorPlaywright', return_value=self.mock_extractor):
            new_posts = await collect_twitter_bookmarks(self.db_manager, set())
            
        # Should skip the duplicate
        self.assertEqual(new_posts, 0)
        
    async def test_new_post_added(self):
        """Test that new posts are added correctly."""
        # Create a new mock post
        mock_post = SocialPost(
            platform='twitter',
            author='New User',
            author_handle='newuser',
            content='Brand new content',
            created_at=datetime.now(timezone.utc),
            url='https://twitter.com/newuser/status/99999',
            post_type='tweet',
            post_id='99999'
        )
        
        # Mock get_saved_posts to return our mock post
        self.mock_extractor.get_saved_posts.return_value = [mock_post]
        
        # Run collection
        with patch('services.collector_runner.TwitterExtractorPlaywright', return_value=self.mock_extractor):
            new_posts = await collect_twitter_bookmarks(self.db_manager, set())
            
        # Should add the new post
        self.assertEqual(new_posts, 1)
        
        # Verify the post was added to the database
        all_posts = self.db_manager.get_all_posts()
        self.assertEqual(len(all_posts), 1)
        self.assertEqual(all_posts.iloc[0]['post_id'], '99999')

if __name__ == '__main__':
    unittest.main()
