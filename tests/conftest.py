"""
Pytest configuration and shared fixtures.
"""

import pytest
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# Set test environment variables
os.environ.setdefault('TESTING', 'true')
os.environ.setdefault('LOG_LEVEL', 'DEBUG')


@pytest.fixture(scope="session")
def test_data_dir():
    """Return path to test data directory"""
    return Path(__file__).parent / "test_data"


@pytest.fixture(scope="session")
def sample_post():
    """Return a sample post for testing"""
    from datetime import datetime, timezone
    
    return {
        'post_id': 'test_post_123',
        'platform': 'twitter',
        'content': 'This is a sample post for testing purposes. It has enough content to pass quality checks.',
        'title': 'Test Post Title',
        'url': 'https://twitter.com/test/123',
        'author': 'test_author',
        'author_handle': '@test_author',
        'created_at': datetime.now(timezone.utc).isoformat(),
        'ai_summary': 'This is a sample AI summary for testing purposes. It has enough content to pass quality checks.',
        'category': 'TECH',
        'value_score': 7.0,
        'quality_score': 7.0,
        'rewrite_score': 7.0,
        'relevance_window': 'evergreen',
        'urgency_score': 0.2,
        'time_sensitive': False,
        'best_persona_key': 'qronoya',
        'best_persona_score': 7.0,
        'analyzed_at': datetime.now(timezone.utc).isoformat(),
        'analysis_model': 'ollama',
    }


@pytest.fixture(scope="session")
def sample_truncated_post():
    """Return a sample truncated post for testing"""
    from datetime import datetime, timezone
    
    return {
        'post_id': 'test_post_truncated',
        'platform': 'twitter',
        'content': 'This is truncated content that ends with...',
        'ai_summary': 'This is a summary',
        'created_at': datetime.now(timezone.utc).isoformat(),
        'analyzed_at': datetime.now(timezone.utc).isoformat(),
    }


@pytest.fixture(scope="session")
def sample_error_post():
    """Return a sample error post for testing"""
    from datetime import datetime, timezone
    
    return {
        'post_id': 'test_post_error',
        'platform': 'twitter',
        'content': 'JavaScript is not available. Please enable JavaScript to continue.',
        'ai_summary': 'This is a summary',
        'created_at': datetime.now(timezone.utc).isoformat(),
        'analyzed_at': datetime.now(timezone.utc).isoformat(),
    }


@pytest.fixture(autouse=True)
def reset_environment():
    """Reset environment before each test"""
    # Store original environment
    original_env = os.environ.copy()
    
    yield
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)
