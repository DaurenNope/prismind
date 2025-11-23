"""
Integration test configuration and fixtures
"""

import pytest
import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

# Set test environment
os.environ.setdefault('TESTING', 'true')
os.environ.setdefault('LOG_LEVEL', 'INFO')


# ============================================================================
# Base Test Classes
# ============================================================================

class IntegrationTestBase:
    """Base class for integration tests with common setup/teardown"""
    
    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """Setup test environment before each test"""
        # Setup
        yield
        # Teardown (if needed)
        pass


class MockServiceMixin:
    """Mixin providing mock service utilities"""
    
    def create_mock_ai_service(self, service_name: str = "ollama"):
        """Create a mock AI service"""
        mock_service = Mock()
        mock_service.generate = AsyncMock(return_value="Mocked AI response")
        mock_service.analyze_content = AsyncMock(return_value={
            "ai_summary": "Mocked AI summary",
            "category": "Technology",
            "value_score": 7.5,
            "quality_score": 8.0,
            "key_concepts": ["test", "concept"],
            "topics": ["Technology"],
            "tags": ["test", "tech"]
        })
        mock_service.is_available = Mock(return_value=True)
        mock_service.name = service_name
        return mock_service
    
    def create_mock_database_manager(self):
        """Create a mock database manager"""
        mock_db = Mock()
        mock_db.get_posts = Mock(return_value=[])
        mock_db.get_unanalyzed_posts = Mock(return_value=[])
        mock_db.get_post_by_id = Mock(return_value=None)
        mock_db.add_post = Mock(return_value=True)
        mock_db.update_post = Mock(return_value=True)
        mock_db.save_post = Mock(return_value=True)
        return mock_db
    
    def create_mock_storage_facade(self):
        """Create a mock storage facade"""
        mock_storage = Mock()
        mock_storage.save_post = Mock(return_value=True)
        mock_storage.get_post = Mock(return_value=None)
        mock_storage.get_posts = Mock(return_value=[])
        mock_storage.get_unanalyzed_posts = Mock(return_value=[])
        mock_storage.save_github_trending_repo = Mock(return_value=True)
        return mock_storage
    
    def create_mock_github_api(self):
        """Create a mock GitHub API client"""
        mock_github = Mock()
        mock_github.get_repo = AsyncMock(return_value={
            "full_name": "test/repo",
            "description": "Test repository",
            "stars": 100,
            "language": "Python",
            "url": "https://github.com/test/repo"
        })
        mock_github.get_trending = Mock(return_value={
            "daily": [
                {
                    "full_name": "test/repo1",
                    "url": "https://github.com/test/repo1",
                    "description": "Test repo 1",
                    "language": "Python",
                    "stars": 100
                }
            ]
        })
        return mock_github


# ============================================================================
# Test Data Fixtures
# ============================================================================

@pytest.fixture
def sample_collected_post():
    """Sample post as collected from platform"""
    return {
        'post_id': 'test_post_123',
        'platform': 'twitter',
        'content': 'This is a test post about Python programming and data science.',
        'title': 'Test Post',
        'url': 'https://twitter.com/test/123',
        'author': 'test_author',
        'author_handle': '@test_author',
        'created_at': datetime.now(timezone.utc).isoformat(),
        'collected_at': datetime.now(timezone.utc).isoformat(),
        'hashtags': ['python', 'datascience'],
        'engagement': {'likes': 100, 'retweets': 50},
        'media_urls': []
    }


@pytest.fixture
def sample_analyzed_post():
    """Sample post with analysis results"""
    return {
        'post_id': 'test_post_123',
        'platform': 'twitter',
        'content': 'This is a test post about Python programming and data science.',
        'url': 'https://twitter.com/test/123',
        'author': 'test_author',
        'created_at': datetime.now(timezone.utc).isoformat(),
        'analyzed_at': datetime.now(timezone.utc).isoformat(),
        'ai_summary': 'Post about Python programming and data science',
        'category': 'Technology',
        'value_score': 7.5,
        'quality_score': 8.0,
        'key_concepts': ['Python', 'programming', 'data science'],
        'topics': ['Technology', 'Programming'],
        'tags': ['python', 'datascience', 'programming']
    }


@pytest.fixture
def sample_github_repo():
    """Sample GitHub repository data"""
    return {
        'full_name': 'test/repo',
        'url': 'https://github.com/test/repo',
        'description': 'A test repository for integration testing',
        'language': 'Python',
        'stars': 100,
        'period': 'daily',
        'collected_at': datetime.now(timezone.utc).isoformat()
    }


@pytest.fixture
def sample_research_query_result():
    """Sample research query result"""
    return {
        'query': 'Python data science best practices',
        'sources': [
            {
                'title': 'Python Data Science Guide',
                'url': 'https://example.com/guide',
                'relevance_score': 0.9,
                'summary': 'Comprehensive guide to Python data science'
            }
        ],
        'synthesis': 'Python data science involves pandas, numpy, and scikit-learn',
        'confidence': 0.85
    }


# ============================================================================
# Mock Service Fixtures
# ============================================================================

@pytest.fixture
def mock_ai_service():
    """Mock AI service for testing"""
    mixin = MockServiceMixin()
    return mixin.create_mock_ai_service()


@pytest.fixture
def mock_database_manager():
    """Mock database manager for testing"""
    mixin = MockServiceMixin()
    return mixin.create_mock_database_manager()


@pytest.fixture
def mock_storage_facade():
    """Mock storage facade for testing"""
    mixin = MockServiceMixin()
    return mixin.create_mock_storage_facade()


@pytest.fixture
def mock_github_api():
    """Mock GitHub API for testing"""
    mixin = MockServiceMixin()
    return mixin.create_mock_github_api()


# ============================================================================
# Platform Collector Fixtures
# ============================================================================

@pytest.fixture
def mock_twitter_collector():
    """Mock Twitter collector"""
    mock_collector = Mock()
    mock_collector.collect = AsyncMock(return_value=[
        {
            'post_id': 'twitter_123',
            'platform': 'twitter',
            'content': 'Test Twitter post',
            'url': 'https://twitter.com/test/123',
            'author': 'test_user',
            'created_at': datetime.now(timezone.utc).isoformat()
        }
    ])
    return mock_collector


@pytest.fixture
def mock_reddit_collector():
    """Mock Reddit collector"""
    mock_collector = Mock()
    mock_collector.collect = AsyncMock(return_value=[
        {
            'post_id': 'reddit_123',
            'platform': 'reddit',
            'content': 'Test Reddit post',
            'url': 'https://reddit.com/r/test/123',
            'author': 'test_user',
            'created_at': datetime.now(timezone.utc).isoformat()
        }
    ])
    return mock_collector


@pytest.fixture
def mock_threads_collector():
    """Mock Threads collector"""
    mock_collector = Mock()
    mock_collector.collect = AsyncMock(return_value=[
        {
            'post_id': 'threads_123',
            'platform': 'threads',
            'content': 'Test Threads post',
            'url': 'https://threads.net/test/123',
            'author': 'test_user',
            'created_at': datetime.now(timezone.utc).isoformat()
        }
    ])
    return mock_collector


# ============================================================================
# Performance Test Fixtures
# ============================================================================

@pytest.fixture
def performance_timer():
    """Timer fixture for performance tests"""
    import time
    
    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None
        
        def start(self):
            self.start_time = time.time()
        
        def stop(self):
            self.end_time = time.time()
        
        def elapsed(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return None
    
    return Timer()






