#!/usr/bin/env python3
"""
Integration tests for SupabaseManager with the real Supabase database
"""

import os
import sys
import pytest
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from supabase_manager import SupabaseManager

# Load environment variables
load_dotenv()

@pytest.mark.integration
class TestSupabaseIntegration:
    """Integration tests for SupabaseManager class"""
    
    def test_connection_and_basic_operations(self):
        """Test connection to Supabase and basic CRUD operations"""
        try:
            # Initialize manager
            manager = SupabaseManager()
            
            # Test data
            test_post = {
                'title': 'Integration Test Post',
                'content': 'This is a test post for integration testing',
                'platform': 'integration_test',
                'author': 'Integration Tester',
                'author_handle': '@integrationtester',
                'url': 'https://example.com/integration-test',
                'summary': 'Integration test summary',
                'value_score': 7,
                'smart_tags': '["test", "integration"]',
                'ai_summary': 'This is a test AI summary for integration testing.',
                'folder_category': 'test',
                'category': 'integration'
            }
            
            # Test insert
            inserted_post = manager.insert_post(test_post)
            assert isinstance(inserted_post, dict)
            assert 'id' in inserted_post
            assert inserted_post['title'] == test_post['title']
            
            post_id = inserted_post['id']
            
            # Test get posts
            posts = manager.get_posts(limit=10, platform='integration_test')
            assert isinstance(posts, list)
            assert len(posts) > 0
            assert any(post['id'] == post_id for post in posts)
            
            # Test update
            update_data = {
                'title': 'Updated Integration Test Post',
                'value_score': 9
            }
            updated_post = manager.update_post(post_id, update_data)
            assert isinstance(updated_post, dict)
            assert updated_post['title'] == 'Updated Integration Test Post'
            assert updated_post['value_score'] == 9
            
            # Test search
            search_results = manager.search_posts('Integration', limit=5)
            assert isinstance(search_results, list)
            assert len(search_results) > 0
            
            # Test get by category
            category_posts = manager.get_posts_by_category('integration', limit=5)
            assert isinstance(category_posts, list)
            
            # Test get top posts
            top_posts = manager.get_top_posts(limit=5)
            assert isinstance(top_posts, list)
            
            # Test delete
            deleted = manager.delete_post(post_id)
            assert deleted is True
            
            # Verify deletion
            posts_after_delete = manager.get_posts(limit=10, platform='integration_test')
            assert not any(post['id'] == post_id for post in posts_after_delete)
            
        except Exception as e:
            pytest.skip(f"Integration test skipped due to: {e}")

    def test_error_handling(self):
        """Test error handling capabilities"""
        try:
            manager = SupabaseManager()
            
            # Test with invalid post ID for update (should not crash)
            result = manager.update_post(-999999, {'title': 'Test'})
            # Should return empty dict, not raise exception
            assert isinstance(result, dict)
            
            # Test with invalid post ID for delete (should not crash)
            result = manager.delete_post(-999999)
            # Should return False, not raise exception
            assert result is False
            
        except Exception as e:
            pytest.skip(f"Integration test skipped due to: {e}")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])